#!/usr/bin/env python3
"""Phase 2 — per-framework extractor tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from a11y_extract import (
    detect_extractor,
    detect_format,
    extract_file,
    write_sidecar,
)
from a11y_mapping import LineMapping, remap_line

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestA11yExtract(unittest.TestCase):
    def test_detect_format_alias(self):
        path = FIXTURES / "LoginForm.vue"
        self.assertIs(detect_format(path), detect_extractor(path))

    def test_extract_tsx_offsets(self):
        result = extract_file(FIXTURES / "LoginForm.tsx")
        self.assertIn("<main", result.html)
        self.assertTrue(result.mappings)
        self.assertGreater(remap_line(1, result.mappings), 1)

    def test_extract_vue_offsets(self):
        result = extract_file(FIXTURES / "LoginForm.vue")
        self.assertIn("<input", result.html)
        input_lines = [m.source_line for m in result.mappings if m.extracted_line <= 3]
        self.assertTrue(input_lines)
        self.assertGreater(max(input_lines), 1)

    def test_extract_svelte_offsets(self):
        result = extract_file(FIXTURES / "LoginForm.svelte")
        self.assertIn("<input", result.html)
        self.assertNotIn("<script", result.html.lower())
        self.assertTrue(result.mappings)

    def test_extract_angular_offsets(self):
        result = extract_file(FIXTURES / "login.component.html")
        self.assertIn("<input", result.html)
        self.assertEqual(result.mappings[0].extracted_line, 1)

    def test_remap_line(self):
        m = [LineMapping(3, 47), LineMapping(5, 50)]
        self.assertEqual(remap_line(3, m), 47)
        self.assertEqual(remap_line(4, m), 48)

    def test_sidecar_schema(self):
        result = extract_file(FIXTURES / "LoginForm.tsx")
        path = write_sidecar(result)
        try:
            self.assertTrue(path.is_file())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["version"], 1)
            self.assertEqual(data["sourceFile"], str(FIXTURES / "LoginForm.tsx"))
            self.assertIn("mappings", data)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
