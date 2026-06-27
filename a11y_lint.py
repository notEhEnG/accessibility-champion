#!/usr/bin/env python3
"""
accessibility-champion static linter
Checks a single HTML file for common WCAG 2.2 AA issues.
Usage: python3 scripts/a11y_lint.py path/to/file.html [--json]

Returns a JSON report (or human-readable) with:
  - score (0-100)
  - violations list with severity, line, and suggested fix
"""

import sys
import json
import re
from pathlib import Path

SEVERITY_WEIGHTS = {"critical": 20, "serious": 10, "moderate": 5, "minor": 2}

def parse_args():
    args = sys.argv[1:]
    json_mode = "--json" in args
    files = [a for a in args if not a.startswith("--")]
    return files, json_mode

def read_file(path):
    return Path(path).read_text(encoding="utf-8")

def find_all(pattern, text, flags=re.IGNORECASE):
    return list(re.finditer(pattern, text, flags))

def line_of(match, text):
    return text[:match.start()].count("\n") + 1

def check_html(source):
    violations = []

    # 1. Lang attribute on <html>
    html_tag = re.search(r'<html([^>]*)>', source, re.IGNORECASE)
    if html_tag:
        if 'lang=' not in html_tag.group(1).lower():
            violations.append({
                "id": "html-has-lang",
                "severity": "serious",
                "line": line_of(html_tag, source),
                "message": "<html> tag is missing a lang attribute",
                "fix": 'Add lang="en" (or appropriate language code) to the <html> tag',
                "wcag": "3.1.1 Language of Page"
            })

    # 2. Images without alt
    for m in find_all(r'<img([^>]*)>', source):
        attrs = m.group(1)
        if 'alt=' not in attrs.lower():
            violations.append({
                "id": "image-alt",
                "severity": "critical",
                "line": line_of(m, source),
                "message": '<img> is missing an alt attribute',
                "fix": 'Add alt="[description]" for informational images, or alt="" role="presentation" for decorative ones',
                "wcag": "1.1.1 Non-text Content"
            })

    # 3. Inputs without labels
    for m in find_all(r'<input([^>]*)>', source):
        attrs = m.group(1)
        input_type = re.search(r'type=["\']?(\w+)', attrs, re.IGNORECASE)
        itype = input_type.group(1).lower() if input_type else 'text'
        if itype in ('hidden', 'submit', 'button', 'image', 'reset'):
            continue
        input_id = re.search(r'id=["\']([^"\']+)', attrs, re.IGNORECASE)
        has_aria_label = 'aria-label=' in attrs.lower() or 'aria-labelledby=' in attrs.lower()
        if not has_aria_label:
            if not input_id:
                violations.append({
                    "id": "label-content-name-mismatch",
                    "severity": "critical",
                    "line": line_of(m, source),
                    "message": f'<input type="{itype}"> has no id — cannot be associated with a <label>',
                    "fix": 'Add a unique id attribute and a <label for="that-id"> element, or add aria-label="..."',
                    "wcag": "1.3.1 Info and Relationships"
                })
            else:
                iid = input_id.group(1)
                label_pattern = rf'<label[^>]*for=["\']?{re.escape(iid)}["\']?'
                if not re.search(label_pattern, source, re.IGNORECASE):
                    violations.append({
                        "id": "input-missing-label",
                        "severity": "critical",
                        "line": line_of(m, source),
                        "message": f'<input id="{iid}"> has no associated <label for="{iid}">',
                        "fix": f'Add <label for="{iid}">Descriptive label</label> before or wrapping the input',
                        "wcag": "3.3.2 Labels or Instructions"
                    })

    # 4. Buttons with no accessible name
    for m in find_all(r'<button([^>]*)>(.*?)</button>', source, re.DOTALL | re.IGNORECASE):
        attrs = m.group(1)
        inner = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        has_aria = 'aria-label=' in attrs.lower() or 'aria-labelledby=' in attrs.lower()
        if not inner and not has_aria:
            violations.append({
                "id": "button-name",
                "severity": "critical",
                "line": line_of(m, source),
                "message": '<button> has no accessible name (empty inner text, no aria-label)',
                "fix": 'Add aria-label="[action description]" or visible text content inside the button',
                "wcag": "4.1.2 Name, Role, Value"
            })

    # 5. outline:none / outline:0 without :focus-visible replacement
    for m in find_all(r'outline\s*:\s*(?:none|0)\b', source):
        # Check if it's inside a :focus-visible block (simple heuristic)
        context_start = max(0, m.start() - 200)
        context = source[context_start:m.start()]
        if ':focus-visible' not in context and ':focus' not in context:
            violations.append({
                "id": "focus-visible",
                "severity": "serious",
                "line": line_of(m, source),
                "message": "outline: none/0 detected without a :focus-visible replacement",
                "fix": "Replace with :focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }",
                "wcag": "2.4.7 Focus Visible"
            })

    # 6. Links with generic text
    for m in find_all(r'<a([^>]*)>(click here|read more|here|learn more|more)</a>', source):
        violations.append({
            "id": "link-name",
            "severity": "serious",
            "line": line_of(m, source),
            "message": f'Link with generic text "{m.group(2)}" — meaningless out of context',
            "fix": 'Use descriptive link text like "Read the accessibility guide" or add aria-label="..."',
            "wcag": "2.4.4 Link Purpose (In Context)"
        })

    # 7. Table without caption or th
    for m in find_all(r'<table([^>]*)>', source):
        end = source.find('</table>', m.start())
        if end == -1:
            continue
        table_html = source[m.start():end]
        has_caption = '<caption' in table_html.lower()
        has_th = re.search(r'<th(\s[^>]*)?>',  table_html, re.IGNORECASE)
        has_role_presentation = 'role="presentation"' in table_html.lower()
        if not has_role_presentation:
            if not has_th:
                violations.append({
                    "id": "table-th",
                    "severity": "serious",
                    "line": line_of(m, source),
                    "message": "Data table has no <th> header cells",
                    "fix": "Add <th scope='col'> for column headers and <th scope='row'> for row headers",
                    "wcag": "1.3.1 Info and Relationships"
                })
            if not has_caption:
                violations.append({
                    "id": "table-caption",
                    "severity": "moderate",
                    "line": line_of(m, source),
                    "message": "Table is missing a <caption> describing its purpose",
                    "fix": "Add <caption>Table description</caption> as first child of <table>",
                    "wcag": "1.3.1 Info and Relationships"
                })

    # 8. Heading hierarchy: detect skipped levels
    headings = find_all(r'<h([1-6])', source)
    prev_level = 1
    for m in headings:
        level = int(m.group(1))
        if level > prev_level + 1:
            violations.append({
                "id": "heading-order",
                "severity": "moderate",
                "line": line_of(m, source),
                "message": f"Heading level skipped: H{prev_level} → H{level}",
                "fix": f"Use H{prev_level + 1} here, or restructure heading hierarchy to avoid gaps",
                "wcag": "1.3.1 Info and Relationships"
            })
        prev_level = level

    # 9. iframes without title
    for m in find_all(r'<iframe([^>]*)>', source):
        attrs = m.group(1)
        if 'title=' not in attrs.lower():
            violations.append({
                "id": "frame-title",
                "severity": "serious",
                "line": line_of(m, source),
                "message": "<iframe> is missing a title attribute",
                "fix": 'Add title="Description of iframe content" to the <iframe>',
                "wcag": "2.4.1 Bypass Blocks"
            })

    # 10. autoplay media
    for m in find_all(r'<(?:video|audio)([^>]*)autoplay', source):
        violations.append({
            "id": "no-autoplay",
            "severity": "serious",
            "line": line_of(m, source),
            "message": "Media with autoplay — can disorient screen reader users and violate WCAG 1.4.2",
            "fix": "Remove autoplay, or add controls and a mechanism to pause/stop the media",
            "wcag": "1.4.2 Audio Control"
        })

    return violations

def score(violations):
    deduction = sum(SEVERITY_WEIGHTS.get(v["severity"], 0) for v in violations)
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
    files, json_mode = parse_args()
    if not files:
        print("Usage: python3 a11y_lint.py file.html [--json]")
        sys.exit(1)

    results = []
    for path in files:
        try:
            source = read_file(path)
        except FileNotFoundError:
            print(f"File not found: {path}", file=sys.stderr)
            continue

        violations = check_html(source)
        s = score(violations)
        results.append({"file": path, "score": s, "violations": violations})

        if json_mode:
            print(json.dumps(results, indent=2))
        else:
            print(format_report(path, violations, s))

if __name__ == "__main__":
    main()
