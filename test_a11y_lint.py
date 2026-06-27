import unittest
import json
import subprocess
from pathlib import Path
from a11y_lint import check_html, score, check_focus_visible

class TestA11yLint(unittest.TestCase):
    def setUp(self):
        self.demo_dir = Path(__file__).parent / "demo"
        self.linter_script = Path(__file__).parent / "a11y_lint.py"
        
    def test_broken_page(self):
        broken_path = self.demo_dir / "broken_page.html"
        source = broken_path.read_text(encoding="utf-8")
        violations = check_html(source)
        
        # Should have multiple violations
        self.assertGreater(len(violations), 0)
        violation_ids = [v["id"] for v in violations]
        
        # Check that specific violations are caught
        self.assertIn("html-has-lang", violation_ids)
        self.assertIn("image-alt", violation_ids)
        self.assertIn("input-missing-label", violation_ids)
        self.assertIn("button-name", violation_ids)
        self.assertIn("link-name", violation_ids)
        self.assertIn("table-th", violation_ids)
        self.assertIn("frame-title", violation_ids)
        
        # Check for new heuristics
        self.assertIn("missing-main", violation_ids)
        self.assertIn("input-autocomplete", violation_ids)
        
        # Score should be low
        s = score(violations)
        self.assertLess(s, 100)

    def test_passing_page(self):
        passing_path = self.demo_dir / "passing_page.html"
        source = passing_path.read_text(encoding="utf-8")
        violations = check_html(source)
        
        # A perfectly passing page should have 0 violations
        self.assertEqual(len(violations), 0, f"Expected 0 violations but got {len(violations)}: {[v['id'] for v in violations]}")
        s = score(violations)
        self.assertEqual(s, 100)

    def test_wrapped_labels(self):
        source = """<label>Username: <input type="text" autocomplete="username"></label>"""
        # We need <html> and <main> to avoid those errors
        full_source = f"<html lang='en'><main>{source}</main></html>"
        violations = check_html(full_source)
        violation_ids = [v["id"] for v in violations]
        self.assertNotIn("label-content-name-mismatch", violation_ids)
        self.assertNotIn("input-missing-label", violation_ids)

    def test_table_presentation(self):
        source = """<html lang='en'><main><table role="presentation"><tr><td>Data</td></tr></table></main></html>"""
        violations = check_html(source)
        violation_ids = [v["id"] for v in violations]
        self.assertNotIn("table-th", violation_ids)
        self.assertNotIn("table-caption", violation_ids)

    def test_nested_button_link_text(self):
        source = """<html lang='en'><main>
            <button><span>Save</span></button>
            <a href="#"><span>Read</span> more</a>
            <a href="#"><span>Explore</span> articles</a>
        </main></html>"""
        violations = check_html(source)
        violation_ids = [v["id"] for v in violations]
        self.assertNotIn("button-name", violation_ids)
        # "Read more" is generic and should be flagged
        self.assertIn("link-name", violation_ids)
        
        link_name_violations = [v for v in violations if v["id"] == "link-name"]
        self.assertEqual(len(link_name_violations), 1)
        self.assertIn("read more", link_name_violations[0]["message"])

    def test_check_focus_visible_regex(self):
        source = """
        <style>
          .bad { outline: none; }
          
          /* Padding to exceed the 200-character context window for the heuristic scan */
          /* ------------------------------------------------------------------------------------------------- */
          /* ------------------------------------------------------------------------------------------------- */
          /* ------------------------------------------------------------------------------------------------- */
          
          .good { outline: 0; }
          .good:focus-visible { outline: 2px solid blue; }
        </style>
        """
        violations = check_focus_visible(source)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["id"], "focus-visible")

    def test_cli_clean_file(self):
        passing_path = self.demo_dir / "passing_page.html"
        result = subprocess.run(
            ["python3", str(self.linter_script), str(passing_path)],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Score: 100/100", result.stdout)

    def test_cli_failing_file(self):
        broken_path = self.demo_dir / "broken_page.html"
        result = subprocess.run(
            ["python3", str(self.linter_script), str(broken_path)],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Score: 0/100", result.stdout)

    def test_cli_json_output(self):
        broken_path = self.demo_dir / "broken_page.html"
        result = subprocess.run(
            ["python3", str(self.linter_script), "--json", str(broken_path)],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        self.assertTrue(isinstance(data, list))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["score"], 0)
        self.assertGreater(len(data[0]["violations"]), 0)

    def test_cli_missing_file(self):
        result = subprocess.run(
            ["python3", str(self.linter_script), "does_not_exist.html"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("File not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
