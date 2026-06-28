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

    def test_button_accessible_names_advanced(self):
        # SVG title check
        source_svg = """<html lang="en"><main><button><svg><title>Close Menu</title></svg></button></main></html>"""
        violations = check_html(source_svg)
        violation_ids = [v["id"] for v in violations]
        self.assertNotIn("button-name", violation_ids)

        # Image alt check
        source_img = """<html lang="en"><main><button><img src="icon.png" alt="Submit Settings"></button></main></html>"""
        violations_img = check_html(source_img)
        violation_ids_img = [v["id"] for v in violations_img]
        self.assertNotIn("button-name", violation_ids_img)

    def test_broad_link_purpose(self):
        source = """<html lang="en"><main>
            <a href="#">Click here to read the report</a>
            <a href="#">Learn more about accessibility guidelines</a>
        </main></html>"""
        violations = check_html(source)
        violation_ids = [v["id"] for v in violations]
        self.assertIn("link-name", violation_ids)
        link_violations = [v for v in violations if v["id"] == "link-name"]
        self.assertEqual(len(link_violations), 2)

    def test_duplicate_id_detection(self):
        source = """<html lang="en"><main>
            <div id="duplicate-me">First</div>
            <div id="duplicate-me">Second</div>
        </main></html>"""
        violations = check_html(source)
        violation_ids = [v["id"] for v in violations]
        self.assertIn("duplicate-id", violation_ids)

    def test_form_group_fieldset_legend(self):
        # Invalid group
        source_invalid = """<html lang="en"><main>
            <input type="radio" name="color" value="red">
            <input type="radio" name="color" value="blue">
        </main></html>"""
        violations = check_html(source_invalid)
        self.assertIn("form-group-fieldset", [v["id"] for v in violations])

        # Valid group
        source_valid = """<html lang="en"><main>
            <fieldset>
                <legend>Choose a color</legend>
                <input type="radio" name="color" value="red">
                <input type="radio" name="color" value="blue">
            </fieldset>
        </main></html>"""
        violations_valid = check_html(source_valid)
        self.assertNotIn("form-group-fieldset", [v["id"] for v in violations_valid])

    def test_aria_describedby_missing_target(self):
        # Missing target
        source_missing = """<html lang="en"><main>
            <input type="text" id="username" aria-describedby="non-existent-desc">
        </main></html>"""
        violations = check_html(source_missing)
        self.assertIn("aria-describedby-missing-target", [v["id"] for v in violations])

        # Existing target
        source_exists = """<html lang="en"><main>
            <input type="text" id="username" aria-describedby="existent-desc">
            <div id="existent-desc">Help text</div>
        </main></html>"""
        violations_exists = check_html(source_exists)
        self.assertNotIn("aria-describedby-missing-target", [v["id"] for v in violations_exists])

    def test_landmark_completeness(self):
        # Full page missing landmarks
        source_missing = """<html lang="en"><body><main>Content</main></body></html>"""
        violations = check_html(source_missing)
        violation_ids = [v["id"] for v in violations]
        self.assertIn("missing-header-landmark", violation_ids)
        self.assertIn("missing-nav-landmark", violation_ids)
        self.assertIn("missing-footer-landmark", violation_ids)

        # Full page with landmarks
        source_present = """<html lang="en">
        <body>
            <header>Header</header>
            <nav>Nav</nav>
            <main>Content</main>
            <footer>Footer</footer>
        </body>
        </html>"""
        violations_present = check_html(source_present)
        violation_ids_present = [v["id"] for v in violations_present]
        self.assertNotIn("missing-header-landmark", violation_ids_present)
        self.assertNotIn("missing-nav-landmark", violation_ids_present)
        self.assertNotIn("missing-footer-landmark", violation_ids_present)

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
