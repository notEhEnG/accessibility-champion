"""Phase 3 — CSS accessibility heuristics (contrast, touch targets, focus)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from a11y_css_fetch import fetch_linked_css

PHASE = "3"
FIX_CONFIDENCE = "assisted"
TEXT_TAGS = frozenset({"p", "span", "a", "button", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "label"})
INTERACTIVE_TAGS = frozenset({"button", "a", "input", "select", "textarea"})

RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
OUTLINE_SUPPRESS_RE = re.compile(r"outline\s*:\s*(?:none|0)\b")
OUTLINE_SET_RE = re.compile(r"outline\s*:\s*(?!none\b|0\b)")
FOCUS_PSEUDO_RE = re.compile(r":focus-visible|:focus\b")
PSEUDO_STRIP_RE = re.compile(r":[\w-]+(\([^)]*\))?")
PX_RE = re.compile(r"^([\d.]+)px$")
REM_EM_RE = re.compile(r"^([\d.]+)(rem|em)$")
VAR_RE = re.compile(r"var\s*\(")
CALC_RE = re.compile(r"calc\s*\(|clamp\s*\(")
TAG_ATTRS_RE = re.compile(
    r"<(p|span|a|button|h[1-6]|li|td|label|input)([^>]*)>",
    re.I,
)
CLASS_ID_RE = re.compile(r'\bclass\s*=\s*["\']([^"\']*)["\']', re.I)
ID_RE = re.compile(r'\bid\s*=\s*["\']([^"\']+)["\']', re.I)
STYLE_RE = re.compile(r'\bstyle\s*=\s*["\']([^"\']*)["\']', re.I)


@dataclass
class CssValue:
    kind: Literal["literal", "unknown", "var"]
    raw: str
    pixels: float | None = None


@dataclass
class RuleBlock:
    selectors: list[str]
    declarations: dict[str, str]
    line: int


def _line_number(source: str, index: int) -> int:
    return source[:index].count("\n") + 1


def parse_inline_style(attr_value: str) -> dict[str, str]:
    """Parse CSS declaration block into property → value map."""
    decls: dict[str, str] = {}
    for part in attr_value.split(";"):
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        decls[key.strip().lower()] = val.strip()
    return decls


def _parse_px(value: str) -> CssValue:
    value = value.strip().lower()
    if VAR_RE.search(value) or CALC_RE.search(value):
        return CssValue("var" if VAR_RE.search(value) else "unknown", value)
    m = PX_RE.match(value)
    if m:
        return CssValue("literal", value, float(m.group(1)))
    m = REM_EM_RE.match(value)
    if m:
        return CssValue("literal", value, float(m.group(1)) * 16.0)
    return CssValue("unknown", value)


def _parse_hex_color(value: str) -> CssValue:
    value = value.strip().lower()
    if VAR_RE.search(value) or value in ("inherit", "initial", "transparent"):
        return CssValue("var" if VAR_RE.search(value) else "unknown", value)
    rgb = _parse_hex_color_rgb(value)
    if rgb:
        return CssValue("literal", value)
    return CssValue("unknown", value)


def _parse_hex_color_rgb(value: str) -> tuple[int, int, int] | None:
    value = value.strip().lower()
    if value.startswith("#") and len(value) in (4, 7):
        if len(value) == 4:
            r, g, b = [int(c * 2, 16) for c in value[1:]]
            return r, g, b
        return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)
    named = {"black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0)}
    return named.get(value)


def _relative_luminance(r: float, g: float, b: float) -> float:
    def chan(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _contrast_ratio(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    l1 = _relative_luminance(*fg)
    l2 = _relative_luminance(*bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def parse_rule_blocks(css: str, offset: int = 0) -> list[tuple[str, str, int]]:
    return [
        (m.group(1).strip(), m.group(2), offset + m.start())
        for m in RULE_RE.finditer(css)
    ]


def walk_rule_blocks(css: str, offset: int = 0) -> list[tuple[str, str, int]]:
    """ARCHITECTURE alias for shared CSS walker."""
    return parse_rule_blocks(css, offset)


def parse_stylesheet(css_text: str, *, line_offset: int = 0) -> list[RuleBlock]:
    """Parse CSS text into RuleBlock list (tinycss2 when available)."""
    raw_rules: list[tuple[str, str, int]] = []
    try:
        import tinycss2
        parsed = tinycss2.parse_stylesheet(css_text, skip_comments=True, skip_whitespace=True)
        for node in parsed:
            if node.type != "qualified-rule":
                continue
            selectors = tinycss2.serialize(node.prelude).strip()
            body = tinycss2.serialize(node.content)
            raw_rules.append((selectors, body, line_offset))
    except ImportError:
        raw_rules = parse_rule_blocks(css_text, line_offset)
    blocks: list[RuleBlock] = []
    for selectors, body, line in raw_rules:
        blocks.append(RuleBlock(
            selectors=[s.strip() for s in selectors.split(",") if s.strip()],
            declarations=parse_inline_style(body.replace("\n", ";")),
            line=_line_number(css_text, line) if line < len(css_text) else 1,
        ))
    return blocks


def parse_stylesheets(source: str, base_url: str | None = None) -> list[RuleBlock]:
    """Collect RuleBlocks from <style>, linked sheets, and inline style rule bodies."""
    blocks: list[RuleBlock] = []
    for match in re.finditer(r"<style[^>]*>(.*?)</style>", source, re.DOTALL | re.IGNORECASE):
        blocks.extend(parse_stylesheet(match.group(1), line_offset=match.start(1)))
    linked = fetch_linked_css(source, base_url)
    if linked:
        blocks.extend(parse_stylesheet(linked))
    return blocks


def _selector_matches(selector: str, tag: str, classes: set[str], elem_id: str | None) -> bool:
    sel = PSEUDO_STRIP_RE.sub("", selector).strip().lower()
    if not sel:
        return False
    parts = sel.split()
    target = parts[-1] if parts else sel
    if target.startswith("."):
        return target[1:] in classes
    if target.startswith("#"):
        return elem_id == target[1:]
    if target == tag:
        return True
    if "." in target:
        ttag, _, rest = target.partition(".")
        if ttag and ttag != tag:
            return False
        return rest.split(".")[0] in classes if rest else False
    return False


def _merged_declarations(
    blocks: list[RuleBlock],
    tag: str,
    classes: set[str],
    elem_id: str | None,
    inline: dict[str, str],
) -> dict[str, str]:
    merged: dict[str, str] = {}
    for block in blocks:
        for sel in block.selectors:
            if _selector_matches(sel, tag, classes, elem_id):
                merged.update(block.declarations)
    merged.update(inline)
    return merged


def _violation(
    rule_id: str,
    *,
    line: int,
    message: str,
    fix: str,
    wcag: str,
    severity: str = "serious",
    fix_confidence: str = FIX_CONFIDENCE,
) -> dict:
    return {
        "id": rule_id,
        "severity": severity,
        "line": line,
        "message": message,
        "fix": fix,
        "wcag": wcag,
        "source": "css",
        "phase": PHASE,
        "fix_confidence": fix_confidence,
    }


def check_color_contrast(source: str, base_url: str | None = None) -> list[dict]:
    """Inline + matched stylesheet rules; skip unresolved var()/calc()."""
    violations: list[dict] = []
    blocks = parse_stylesheets(source, base_url)
    seen: set[int] = set()

    def _check_declarations(line: int, decls: dict[str, str]) -> None:
        if line in seen:
            return
        fg_raw = decls.get("color", "")
        bg_raw = decls.get("background-color", decls.get("background", ""))
        if not fg_raw or not bg_raw:
            return
        fg_cv, bg_cv = _parse_hex_color(fg_raw), _parse_hex_color(bg_raw)
        if fg_cv.kind in ("var", "unknown") or bg_cv.kind in ("var", "unknown"):
            return
        fg, bg = _parse_hex_color_rgb(fg_raw), _parse_hex_color_rgb(bg_raw.split()[0] if " " in bg_raw else bg_raw)
        if not fg or not bg:
            return
        ratio = _contrast_ratio(fg, bg)
        if ratio < 4.5:
            seen.add(line)
            violations.append(_violation(
                "color-contrast",
                line=line,
                message=f"Color contrast ratio {ratio:.1f}:1 below 4.5:1 (heuristic)",
                fix="Increase contrast between text and background colors",
                wcag="1.4.3 Contrast (Minimum)",
            ))

    for match in TAG_ATTRS_RE.finditer(source):
        tag = match.group(1).lower()
        if tag not in TEXT_TAGS:
            continue
        attrs = match.group(2)
        classes = set(CLASS_ID_RE.search(attrs).group(1).split()) if CLASS_ID_RE.search(attrs) else set()
        elem_id = ID_RE.search(attrs).group(1) if ID_RE.search(attrs) else None
        inline = parse_inline_style(STYLE_RE.search(attrs).group(1)) if STYLE_RE.search(attrs) else {}
        decls = _merged_declarations(blocks, tag, classes, elem_id, inline)
        _check_declarations(_line_number(source, match.start()), decls)

    return violations


def check_touch_targets(source: str, base_url: str | None = None) -> list[dict]:
    """Inline + matched rules on interactive elements."""
    violations: list[dict] = []
    blocks = parse_stylesheets(source, base_url)
    tag_re = re.compile(r"<(button|a\b|input)([^>]*)>", re.I)
    for match in tag_re.finditer(source):
        tag = match.group(1).lower()
        attrs = match.group(2)
        if tag == "input" and 'type="hidden"' in attrs.lower():
            continue
        classes = set(CLASS_ID_RE.search(attrs).group(1).split()) if CLASS_ID_RE.search(attrs) else set()
        elem_id = ID_RE.search(attrs).group(1) if ID_RE.search(attrs) else None
        inline = parse_inline_style(STYLE_RE.search(attrs).group(1)) if STYLE_RE.search(attrs) else {}
        decls = _merged_declarations(blocks, tag, classes, elem_id, inline)
        sizes = []
        for key in ("width", "height", "min-width", "min-height"):
            if key in decls:
                cv = _parse_px(decls[key])
                if cv.kind == "literal" and cv.pixels is not None:
                    sizes.append(cv.pixels)
        if sizes and min(sizes) < 44:
            violations.append(_violation(
                "touch-target-size",
                line=_line_number(source, match.start()),
                severity="moderate",
                message="Interactive element may be smaller than 44×44px (heuristic)",
                fix="Ensure touch targets are at least 44×44 CSS pixels",
                wcag="2.5.5 Target Size",
            ))
    return violations


def find_focus_suppression_rules(source: str) -> list[dict]:
    """Phase 3 focus check — shared CSS walker."""
    violations: list[dict] = []
    seen: set[int] = set()

    def _base(sel: str) -> str:
        return PSEUDO_STRIP_RE.sub("", sel).strip()

    def _check(rules: list[tuple[str, str, int]]) -> None:
        fallbacks = {
            _base(s) for s, b, _ in rules
            if FOCUS_PSEUDO_RE.search(s) and OUTLINE_SET_RE.search(b)
        }
        for selector, body, pos in rules:
            if not OUTLINE_SUPPRESS_RE.search(body) or FOCUS_PSEUDO_RE.search(selector):
                continue
            if _base(selector) in fallbacks:
                continue
            line = _line_number(source, pos)
            if line in seen:
                continue
            seen.add(line)
            violations.append(_violation(
                "focus-visible",
                line=line,
                message="outline: none/0 detected without a :focus-visible replacement",
                fix="Replace with :focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }",
                wcag="2.4.7 Focus Visible",
            ))

    for match in re.finditer(r"<style[^>]*>(.*?)</style>", source, re.DOTALL | re.IGNORECASE):
        inner = match.group(1)
        rules = [(s, b, match.start(1) + off) for s, b, off in walk_rule_blocks(inner)]
        _check(rules)
    for match in re.finditer(r'\bstyle\s*=\s*["\']([^"\']*)["\']', source, re.IGNORECASE):
        # Inline style attributes have no selector/braces; treat the body as a "*" rule.
        _check([("*", match.group(1), match.start(1))])
    return violations


def check_pointer_events(source: str) -> list[dict]:
    violations = []
    tag_re = re.compile(
        r"<(button|a\b|input|select|textarea)([^>]*)\bstyle\s*=\s*[\"']([^\"']*)[\"']",
        re.IGNORECASE,
    )
    for match in tag_re.finditer(source):
        decls = parse_inline_style(match.group(3))
        if decls.get("pointer-events", "").lower() == "none":
            violations.append(_violation(
                "pointer-events-none-interactive",
                line=_line_number(source, match.start()),
                message="Interactive element uses pointer-events: none",
                fix="Remove pointer-events: none or provide an accessible alternative control",
                wcag="2.1.1 Keyboard",
            ))
    return violations


def check_font_size_px(source: str) -> list[dict]:
    violations = []
    for match in re.finditer(r'\bstyle\s*=\s*["\']([^"\']*)["\']', source, re.IGNORECASE):
        decls = parse_inline_style(match.group(1))
        fs = decls.get("font-size", "")
        font_shorthand = decls.get("font", "")
        if PX_RE.match(fs) and "rem" not in font_shorthand and "em" not in font_shorthand:
            violations.append(_violation(
                "font-size-px-only",
                line=_line_number(source, match.start()),
                severity="minor",
                message="font-size uses px without rem/em fallback (heuristic)",
                fix="Prefer rem/em or provide a rem fallback for user zoom",
                wcag="1.4.4 Resize Text",
                fix_confidence="manual",
            ))
    return violations


def check_external_css_links(source: str, base_url: str | None = None) -> list[dict]:
    violations = []
    for match in re.finditer(r'<link[^>]+rel=["\']stylesheet["\'][^>]*>', source, re.I):
        if 'href=""' in match.group(0) or "href=''" in match.group(0):
            violations.append(_violation(
                "css-link-empty",
                line=_line_number(source, match.start()),
                severity="minor",
                message="Stylesheet <link> has empty href",
                fix="Provide a valid stylesheet href",
                wcag="1.3.1 Info and Relationships",
            ))
    return violations


def check_css_accessibility(source: str, *, base_url: str | None = None) -> list[dict]:
    """Phase 3 entry — call from check_html()."""
    out: list[dict] = []
    out.extend(find_focus_suppression_rules(source))
    out.extend(check_color_contrast(source, base_url))
    out.extend(check_touch_targets(source, base_url))
    out.extend(check_pointer_events(source))
    out.extend(check_font_size_px(source))
    out.extend(check_external_css_links(source, base_url))
    return out