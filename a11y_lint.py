#!/usr/bin/env python3
"""
accessibility-champion static linter
Checks a single HTML file for common WCAG 2.2 AA issues.
"""

from __future__ import annotations

import sys
import json
import re
import argparse
import glob as globmod
from pathlib import Path
from html.parser import HTMLParser

from collections import defaultdict

from a11y_context import ParseContext, TagAttrs, Violation
from a11y_focus import check_focus_visible
from a11y_rules import all_rules
from a11y_extract import detect_extractor, extract_file, write_sidecar
from a11y_mapping import remap_violations

SEVERITY_WEIGHTS = {"critical": 20, "serious": 10, "moderate": 5, "minor": 2}
RULE_SCORE_ABSOLUTE_MAX = 30


class A11yHTMLParser(HTMLParser):
    """Thin dispatcher that forwards parse events to registered accessibility rules."""

    def __init__(self, ctx: ParseContext, rules):
        super().__init__()
        self.ctx = ctx
        self.rules = rules

    def handle_starttag(self, tag, attrs):
        self.ctx.push_tag(tag)
        tag_attrs = TagAttrs.from_parser(attrs)
        line, _ = self.getpos()
        for rule in self.rules:
            rule.on_starttag(self.ctx, tag, tag_attrs, line)

    def handle_endtag(self, tag):
        for rule in self.rules:
            rule.on_endtag(self.ctx, tag)
        self.ctx.pop_tag(tag)

    def handle_data(self, data):
        for rule in self.rules:
            rule.on_data(self.ctx, data)


def _detect_fragment_mode(source: str, fragment: bool | None) -> bool:
    if fragment is not None:
        return fragment
    return not re.search(r"<(?:html|body)\b", source, re.IGNORECASE)


def check_html(source: str, fragment: bool | None = None) -> list[Violation]:
    ctx = ParseContext(
        source=source,
        fragment_mode=_detect_fragment_mode(source, fragment),
    )
    rules = all_rules()
    parser = A11yHTMLParser(ctx, rules)
    parser.feed(source)
    for rule in rules:
        rule.finalize(ctx)
    violations = list(ctx.violations)
    violations.extend(check_focus_visible(source))
    return sorted(violations, key=lambda item: item["line"])


def _count_multiplier(count: int) -> float:
    if count <= 1:
        return 1.0
    if count <= 4:
        return 1.5
    return 2.0


def rule_deduction(severity: str, count: int) -> int:
    """Per-rule score cap scaled by violation count (max −30 per rule id)."""
    base = SEVERITY_WEIGHTS.get(severity, 0)
    if count <= 0:
        return 0
    return min(int(base * _count_multiplier(count)), RULE_SCORE_ABSOLUTE_MAX)


def score(violations: list[Violation]) -> int:
    groups: dict[str, list[Violation]] = defaultdict(list)
    for violation in violations:
        groups[violation["id"]].append(violation)
    deduction = sum(
        rule_deduction(items[0]["severity"], len(items))
        for items in groups.values()
    )
    return max(0, 100 - deduction)


def format_report(path, violations, s):
    lines = [f"\n=== Accessibility Audit: {path} ===\n"]
    lines.append(f"Score: {s}/100  |  WCAG 2.2 AA\n")

    for sev in ("critical", "serious", "moderate", "minor"):
        group = [v for v in violations if v["severity"] == sev]
        if not group:
            continue
        icons = {"critical": "🔴", "serious": "🟠", "moderate": "🟡", "minor": "🔵"}
        lines.append(f"\n{icons[sev]} {sev.capitalize()} ({len(group)} issue{'s' if len(group) > 1 else ''})")
        for v in group:
            lines.append(f"\n  [{v['id']}] line {v['line']}: {v['message']}")
            if "wcag" in v:
                lines.append(f"  → WCAG: {v['wcag']}")
            lines.append(f"  → Fix: {v['fix']}")

    if not violations:
        lines.append("\n✅ No static issues found! Consider running axe-core for dynamic and contrast checks.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="accessibility-champion static linter\nChecks HTML files for common WCAG 2.2 AA issues.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("files", nargs="+", help="HTML file(s) to lint")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument(
        "--fragment",
        action="store_true",
        help="Treat input as an HTML fragment (skip full-page landmark and single-H1 checks)",
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Treat input as a full page even without <html>/<body> tags",
    )
    parser.add_argument(
        "--axe",
        action="store_true",
        help="Merge axe-core rendered audit results when Node.js and axe-core are available",
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Extract HTML from framework templates (.tsx/.jsx/.vue/.svelte/.component.html) before linting",
    )
    parser.add_argument(
        "--glob",
        dest="glob_pattern",
        action="store_true",
        help="Treat each argument as a glob pattern (expanded recursively) before linting",
    )
    parser.add_argument(
        "--no-sidecar",
        action="store_true",
        help="Skip writing the *.extract-map.json sidecar during extraction",
    )

    args = parser.parse_args()
    if args.fragment and args.full_page:
        parser.error("--fragment and --full-page are mutually exclusive")

    fragment = True if args.fragment else False if args.full_page else None

    paths: list[str] = []
    for item in args.files:
        if args.glob_pattern:
            paths.extend(sorted(globmod.glob(item, recursive=True)))
        else:
            paths.append(item)

    results = []
    has_errors = False

    for path in paths:
        path_obj = Path(path)
        extractor = detect_extractor(path_obj)
        use_extract = args.extract or (
            extractor is not None and path_obj.suffix.lower() not in (".html", ".htm")
        )
        try:
            if use_extract and extractor is not None:
                result = extract_file(path_obj)
                violations = check_html(
                    result.html,
                    fragment=result.fragment if result.fragment else fragment,
                )
                violations = remap_violations(violations, result.mappings, result.source_file)
                if not args.no_sidecar:
                    write_sidecar(result)
                file_key = result.source_file
            else:
                source = path_obj.read_text(encoding="utf-8")
                violations = check_html(source, fragment=fragment)
                if args.axe:
                    from a11y_axe import merge_axe_results

                    violations = merge_axe_results(path_obj, violations)
                file_key = path
        except FileNotFoundError:
            print(f"File not found: {path}", file=sys.stderr)
            has_errors = True
            continue
        except ValueError as exc:
            print(exc, file=sys.stderr)
            has_errors = True
            continue

        s = score(violations)
        results.append({"file": file_key, "score": s, "violations": violations})

        if violations:
            has_errors = True

        if not args.json:
            print(format_report(file_key, violations, s))

    if args.json:
        print(json.dumps(results, indent=2))

    sys.exit(1 if has_errors else 0)


def cli():
    import sys

    if len(sys.argv) < 2:
        print("Usage: a11y-lint <html-file>")
        print("Example: a11y-lint demo/broken_page.html")
        sys.exit(1)

    main()


if __name__ == "__main__":
    main()
