"""CSS focus-outline checks independent of the HTML parser."""

from __future__ import annotations

import re

RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
OUTLINE_SUPPRESS_RE = re.compile(r"outline\s*:\s*(?:none|0)\b")
OUTLINE_SET_RE = re.compile(r"outline\s*:\s*(?!none\b|0\b)")
FOCUS_PSEUDO_RE = re.compile(r":focus-visible|:focus\b")
PSEUDO_STRIP_RE = re.compile(r":[\w-]+(\([^)]*\))?")


def _base_selector(selector: str) -> str:
    return PSEUDO_STRIP_RE.sub("", selector).strip()


def _line_number(source: str, index: int) -> int:
    return source[:index].count("\n") + 1


def _parse_css_rules(css: str, offset: int = 0) -> list[tuple[str, str, int]]:
    return [
        (match.group(1).strip(), match.group(2), offset + match.start())
        for match in RULE_RE.finditer(css)
    ]


def _check_css_rules(rules: list[tuple[str, str, int]], source: str) -> list[dict]:
    focus_fallbacks: set[str] = set()
    for selector, body, _ in rules:
        if FOCUS_PSEUDO_RE.search(selector) and OUTLINE_SET_RE.search(body):
            focus_fallbacks.add(_base_selector(selector))

    violations = []
    for selector, body, pos in rules:
        if not OUTLINE_SUPPRESS_RE.search(body):
            continue
        if FOCUS_PSEUDO_RE.search(selector):
            continue
        base = _base_selector(selector)
        if base in focus_fallbacks:
            continue
        violations.append({
            "id": "focus-visible",
            "severity": "serious",
            "line": _line_number(source, pos),
            "message": "outline: none/0 detected without a :focus-visible replacement",
            "fix": "Replace with :focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }",
            "wcag": "2.4.7 Focus Visible",
        })
    return violations


def check_focus_visible(source: str) -> list[dict]:
    """
    Scan style blocks and inline style attributes for outline suppression
    without a corresponding :focus-visible or :focus fallback rule.
    """
    violations: list[dict] = []
    seen_lines: set[int] = set()

    for match in re.finditer(
        r"<style[^>]*>(.*?)</style>",
        source,
        re.DOTALL | re.IGNORECASE,
    ):
        rules = _parse_css_rules(match.group(1), match.start(1))
        for item in _check_css_rules(rules, source):
            if item["line"] not in seen_lines:
                seen_lines.add(item["line"])
                violations.append(item)

    for match in re.finditer(r'\bstyle\s*=\s*["\']([^"\']*)["\']', source, re.IGNORECASE):
        rules = _parse_css_rules(match.group(1), match.start(1))
        for item in _check_css_rules(rules, source):
            if item["line"] not in seen_lines:
                seen_lines.add(item["line"])
                violations.append(item)

    return violations