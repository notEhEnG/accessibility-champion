#!/usr/bin/env python3
"""Phase 2 — new structure/forms/framework rules and extract integration."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from a11y_lint import check_html, main
from a11y_rules import all_rules

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PAGE = "<html lang='en'><head><title>T</title></head><body><main>{body}</main></body></html>"


def _ids(source: str) -> list[str]:
    return [v["id"] for v in check_html(source)]


class TestPhase2Rules(unittest.TestCase):
    def test_total_rule_count(self):
        self.assertEqual(len(all_rules()), 32)

    def test_required_indicator(self):
        self.assertIn("required-indicator", _ids(PAGE.format(body='<input type="text" required />')))

    def test_required_indicator_passes_with_aria(self):
        self.assertNotIn(
            "required-indicator",
            _ids(PAGE.format(body='<input type="text" required aria-label="Name" />')),
        )

    def test_select_empty_label(self):
        src = PAGE.format(body='<select><option value=""></option><option>US</option></select>')
        self.assertIn("select-empty-label", _ids(src))

    def test_landmark_nesting(self):
        src = "<html lang='en'><body><main><main></main></main></body></html>"
        self.assertIn("landmark-nesting", _ids(src))

    def test_empty_heading(self):
        self.assertIn("empty-heading", _ids(PAGE.format(body="<h2></h2>")))

    def test_empty_heading_passes_with_text(self):
        self.assertNotIn("empty-heading", _ids(PAGE.format(body="<h2>Hello</h2>")))

    def test_empty_link(self):
        self.assertIn("empty-link", _ids(PAGE.format(body='<a href="#">click</a>')))

    def test_filename_link_text(self):
        self.assertIn("filename-link-text", _ids(PAGE.format(body='<a href="/f">report.pdf</a>')))

    def test_aria_hidden_focusable(self):
        src = PAGE.format(body='<div aria-hidden="true"><button>x</button></div>')
        self.assertIn("aria-hidden-focusable", _ids(src))

    def test_redundant_role(self):
        self.assertIn("redundant-role", _ids(PAGE.format(body='<button role="button">x</button>')))

    def test_list_structure(self):
        src = PAGE.format(body="<div><a>1</a><a>2</a><a>3</a></div>")
        self.assertIn("list-structure", _ids(src))

    def test_list_structure_passes_in_ul(self):
        src = PAGE.format(body="<ul><li><a>1</a></li><li><a>2</a></li><li><a>3</a></li></ul>")
        self.assertNotIn("list-structure", _ids(src))

    def test_decorative_img_role(self):
        self.assertIn("decorative-img-role", _ids(PAGE.format(body='<img src="x.png" alt="" />')))

    def test_lang_subtag(self):
        self.assertIn("lang-subtag", _ids(PAGE.format(body='<span lang="x">Hola</span>')))


class TestPhase2Extract(unittest.TestCase):
    def test_tsx_extract_remaps_landmark_nesting(self):
        source = (FIXTURES / "LoginForm.tsx").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "LoginForm.tsx"
            work.write_text(source, encoding="utf-8")
            rc = self._run_main([str(work), "--extract", "--json"])
            self.assertEqual(rc, 1)  # violations present → exit 1
            sidecar = Path(f"{work}.extract-map.json")
            self.assertTrue(sidecar.is_file())
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(data["version"], 1)

    def test_no_sidecar_flag(self):
        source = (FIXTURES / "LoginForm.vue").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "LoginForm.vue"
            work.write_text(source, encoding="utf-8")
            self._run_main([str(work), "--extract", "--no-sidecar", "--json"])
            self.assertFalse(Path(f"{work}.extract-map.json").exists())

    @staticmethod
    def _run_main(argv: list[str]) -> int:
        import sys
        from io import StringIO
        from unittest.mock import patch

        with patch.object(sys, "argv", ["a11y-lint", *argv]), patch("sys.stdout", StringIO()):
            try:
                main()
            except SystemExit as exc:
                return int(exc.code or 0)
        return 0


if __name__ == "__main__":
    unittest.main()
