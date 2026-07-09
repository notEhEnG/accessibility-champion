#!/usr/bin/env python3
"""Phase 3 tests — CSS engine (contrast, touch, focus, pointer, font-size)."""

from __future__ import annotations

import unittest
from pathlib import Path

from a11y_css import (
    RuleBlock,
    check_color_contrast,
    check_css_accessibility,
    check_font_size_px,
    check_pointer_events,
    check_touch_targets,
    fetch_linked_css,
    find_focus_suppression_rules,
    parse_inline_style,
    parse_stylesheets,
    walk_rule_blocks,
)
from a11y_focus import check_focus_visible
from a11y_lint import check_html

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "css"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class TestPhase3CssApi(unittest.TestCase):
    def test_parse_inline_style(self):
        decls = parse_inline_style("color: red; background-color: #fff")
        self.assertEqual(decls["color"], "red")
        self.assertEqual(decls["background-color"], "#fff")

    def test_walk_rule_blocks(self):
        self.assertEqual(len(walk_rule_blocks("a { outline: none; }")), 1)

    def test_parse_stylesheets_from_style_tag(self):
        blocks = parse_stylesheets("<style>.x{color:red}</style>")
        self.assertTrue(blocks)
        self.assertIsInstance(blocks[0], RuleBlock)


class TestPhase3Contrast(unittest.TestCase):
    def test_contrast_fail_inline_styles(self):
        v = check_color_contrast(_load("contrast_fail_inline.html"))
        self.assertTrue(any(x["id"] == "color-contrast" for x in v))
        self.assertEqual(v[0]["fix_confidence"], "assisted")

    def test_contrast_skip_unresolved_var(self):
        v = check_color_contrast(_load("contrast_var_skip.html"))
        self.assertFalse(any(x["id"] == "color-contrast" for x in v))

    def test_contrast_linked_stylesheet(self):
        src = _load("stylesheet_contrast.html")
        css = fetch_linked_css(src, base_url=str(FIXTURES))
        self.assertIn(".low", css)
        v = check_color_contrast(src, base_url=str(FIXTURES))
        self.assertTrue(any(x["id"] == "color-contrast" for x in v))


class TestPhase3TouchAndFocus(unittest.TestCase):
    def test_touch_target_small_button(self):
        v = check_touch_targets(_load("touch_target_small.html"))
        self.assertTrue(any(x["id"] == "touch-target-size" for x in v))

    def test_focus_visible_uses_css_walker(self):
        src = _load("focus_suppressed.html")
        v = find_focus_suppression_rules(src)
        self.assertEqual(v[0]["id"], "focus-visible")
        self.assertEqual(check_focus_visible(src), v)

    def test_pointer_events(self):
        v = check_pointer_events('<button style="pointer-events: none">x</button>')
        self.assertTrue(any(x["id"] == "pointer-events-none-interactive" for x in v))

    def test_font_size_px(self):
        v = check_font_size_px('<p style="font-size: 12px">Hi</p>')
        self.assertTrue(any(x["id"] == "font-size-px-only" for x in v))
        self.assertEqual(v[0]["fix_confidence"], "manual")


class TestPhase3Integration(unittest.TestCase):
    def test_check_html_includes_css(self):
        v = check_html(_load("focus_suppressed.html"))
        self.assertIn("focus-visible", [x["id"] for x in v])

    def test_no_duplicate_focus(self):
        v = check_html(_load("focus_suppressed.html"))
        self.assertEqual([x["id"] for x in v].count("focus-visible"), 1)

    def test_no_css_flag_skips_contrast(self):
        v = check_html(_load("contrast_fail_inline.html"), css=False)
        self.assertNotIn("color-contrast", [x["id"] for x in v])

    def test_golden_fixtures_via_check_css_accessibility(self):
        for fixture in ("contrast_fail_inline.html", "touch_target_small.html"):
            v = check_css_accessibility(_load(fixture))
            self.assertTrue(v)
            for item in v:
                self.assertEqual(item["source"], "css")
                self.assertIn(item["fix_confidence"], ("assisted", "manual"))


if __name__ == "__main__":
    unittest.main()
