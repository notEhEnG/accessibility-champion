import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from a11y_axe import dedupe_violations, map_axe_to_violations, merge_axe_results
from a11y_focus import check_focus_visible
from a11y_lint import check_html, rule_deduction, score

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

        # Phase 1 rules
        self.assertIn("document-title", violation_ids)
        self.assertIn("skip-link", violation_ids)
        self.assertIn("placeholder-as-label", violation_ids)
        self.assertIn("video-captions", violation_ids)
        self.assertIn("audio-transcript", violation_ids)
        self.assertIn("aria-invalid-no-desc", violation_ids)
        self.assertIn("button-type-missing", violation_ids)
        self.assertIn("target-blank-no-warning", violation_ids)
        self.assertIn("tabindex-positive", violation_ids)
        
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
        self.assertNotIn("input-unlabelled", violation_ids)
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
        <head><title>Test</title></head>
        <body>
            <a href="#main">Skip to main content</a>
            <header>Header</header>
            <nav>Nav</nav>
            <main id="main">Content</main>
            <footer>Footer</footer>
        </body>
        </html>"""
        violations_present = check_html(source_present)
        violation_ids_present = [v["id"] for v in violations_present]
        self.assertNotIn("missing-header-landmark", violation_ids_present)
        self.assertNotIn("missing-nav-landmark", violation_ids_present)
        self.assertNotIn("missing-footer-landmark", violation_ids_present)

    def test_check_focus_visible_css_blocks(self):
        source = """
        <style>
          .bad { outline: none; }
          .good { outline: 0; }
          .good:focus-visible { outline: 2px solid blue; }
        </style>
        """
        violations = check_focus_visible(source)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["id"], "focus-visible")

    def test_fragment_mode_skips_landmarks(self):
        source = '<div><input type="text" id="x"><label for="x">Name</label></div>'
        violations = check_html(source, fragment=True)
        violation_ids = [v["id"] for v in violations]
        self.assertNotIn("missing-main", violation_ids)
        self.assertNotIn("missing-header-landmark", violation_ids)

    def test_form_group_single_violation(self):
        source = """<html lang="en"><main>
            <input type="radio" name="c" value="1">
            <input type="radio" name="c" value="2">
            <input type="radio" name="c" value="3">
        </main></html>"""
        violations = [v for v in check_html(source) if v["id"] == "form-group-fieldset"]
        self.assertEqual(len(violations), 1)
        self.assertIn("3 grouped radio", violations[0]["message"])

    def test_single_h1_enforcement(self):
        source = """<html lang="en"><body>
            <header><h1>One</h1><h1>Two</h1></header>
            <nav></nav><main></main><footer></footer>
        </body></html>"""
        violations = check_html(source)
        self.assertIn("heading-single-h1", [v["id"] for v in violations])

    def test_select_missing_label(self):
        source = """<html lang="en"><main><select id="country"></select></main></html>"""
        violations = check_html(source)
        self.assertIn("input-missing-label", [v["id"] for v in violations])

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

    def test_placeholder_as_label(self):
        source = """<html lang="en"><main><input type="text" placeholder="Search"></main></html>"""
        violations = check_html(source)
        self.assertIn("placeholder-as-label", [v["id"] for v in violations])
        self.assertNotIn("input-unlabelled", [v["id"] for v in violations])

    def test_document_title(self):
        source = """<html lang="en"><head></head><body><main></main></body></html>"""
        self.assertIn("document-title", [v["id"] for v in check_html(source)])

    def test_skip_link_with_nav(self):
        source = """<html lang="en"><head><title>T</title></head><body>
            <nav><a href="/">Home</a></nav><main></main></body></html>"""
        self.assertIn("skip-link", [v["id"] for v in check_html(source)])

    def test_video_captions(self):
        source = """<html lang="en"><main><video src="a.mp4"></video></main></html>"""
        self.assertIn("video-captions", [v["id"] for v in check_html(source)])

    def test_audio_transcript(self):
        source = """<html lang="en"><main><audio src="a.mp3"></audio></main></html>"""
        self.assertIn("audio-transcript", [v["id"] for v in check_html(source)])

    def test_aria_labelledby_missing_target(self):
        source = """<html lang="en"><main><button aria-labelledby="missing-id">X</button></main></html>"""
        self.assertIn("aria-labelledby-target", [v["id"] for v in check_html(source)])

    def test_aria_invalid_no_desc(self):
        source = """<html lang="en"><main><input id="x" aria-invalid="true"></main></html>"""
        self.assertIn("aria-invalid-no-desc", [v["id"] for v in check_html(source)])

    def test_tabindex_positive(self):
        source = """<html lang="en"><main><div tabindex="2">Bad</div></main></html>"""
        self.assertIn("tabindex-positive", [v["id"] for v in check_html(source)])

    def test_button_type_missing(self):
        source = """<html lang="en"><main><form><button>Go</button></form></main></html>"""
        self.assertIn("button-type-missing", [v["id"] for v in check_html(source)])

    def test_target_blank_warning(self):
        source = """<html lang="en"><main><a href="https://x.com" target="_blank">Site</a></main></html>"""
        self.assertIn("target-blank-no-warning", [v["id"] for v in check_html(source)])

    def test_cli_missing_file(self):
        result = subprocess.run(
            ["python3", str(self.linter_script), "does_not_exist.html"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("File not found", result.stderr)

    def test_score_single_critical_violation(self):
        violations = [{
            "id": "image-alt",
            "severity": "critical",
            "line": 1,
            "message": "missing",
            "fix": "add alt",
            "wcag": "1.1.1",
        }]
        self.assertEqual(score(violations), 80)
        self.assertEqual(rule_deduction("critical", 1), 20)

    def test_score_caps_repeated_rule(self):
        violations = [
            {
                "id": "image-alt",
                "severity": "critical",
                "line": i,
                "message": "missing",
                "fix": "add alt",
                "wcag": "1.1.1",
            }
            for i in range(1, 6)
        ]
        self.assertEqual(rule_deduction("critical", 5), 30)
        self.assertEqual(score(violations), 70)

    def test_score_scales_medium_count(self):
        violations = [
            {
                "id": "link-name",
                "severity": "serious",
                "line": i,
                "message": "generic",
                "fix": "describe",
                "wcag": "2.4.4",
            }
            for i in range(1, 4)
        ]
        self.assertEqual(rule_deduction("serious", 3), 15)
        self.assertEqual(score(violations), 85)

    def test_empty_alt_passes_image_alt(self):
        source = """<html lang="en"><main><img src="dot.png" alt=""></main></html>"""
        violation_ids = [v["id"] for v in check_html(source)]
        self.assertNotIn("image-alt", violation_ids)

    def test_aria_label_passes_input_unlabelled(self):
        source = """<html lang="en"><main><input type="text" aria-label="Search"></main></html>"""
        violation_ids = [v["id"] for v in check_html(source)]
        self.assertNotIn("input-unlabelled", violation_ids)
        self.assertNotIn("input-missing-label", violation_ids)

    def test_single_radio_skips_form_group_fieldset(self):
        source = """<html lang="en"><main><input type="radio" name="color" value="red"></main></html>"""
        violation_ids = [v["id"] for v in check_html(source)]
        self.assertNotIn("form-group-fieldset", violation_ids)

    def test_image_alt_quality_fail_and_pass(self):
        bad = """<html lang="en"><main><img src="a.png" alt="image"></main></html>"""
        good = """<html lang="en"><main><img src="a.png" alt="Team celebrating launch"></main></html>"""
        self.assertIn("image-alt-quality", [v["id"] for v in check_html(bad)])
        self.assertNotIn("image-alt-quality", [v["id"] for v in check_html(good)])

    def test_no_autoplay_fail_and_pass(self):
        bad = """<html lang="en"><main><audio src="a.mp3" autoplay></audio></main></html>"""
        good = """<html lang="en"><main><audio src="a.mp3" controls></audio>
            <a href="transcript.html">Transcript</a></main></html>"""
        self.assertIn("no-autoplay", [v["id"] for v in check_html(bad)])
        self.assertNotIn("no-autoplay", [v["id"] for v in check_html(good)])

    def test_heading_order_fail_and_pass(self):
        bad = """<html lang="en"><body><header></header><nav></nav>
            <main><h1>Title</h1><h3>Skipped</h3></main><footer></footer></body></html>"""
        good = """<html lang="en"><body><header></header><nav></nav>
            <main><h1>Title</h1><h2>Section</h2></main><footer></footer></body></html>"""
        self.assertIn("heading-order", [v["id"] for v in check_html(bad)])
        self.assertNotIn("heading-order", [v["id"] for v in check_html(good)])

    def test_table_caption_fail_and_pass(self):
        bad = """<html lang="en"><main><table><tr><th>Name</th></tr><tr><td>A</td></tr></table></main></html>"""
        good = """<html lang="en"><main><table><caption>People</caption>
            <tr><th>Name</th></tr><tr><td>A</td></tr></table></main></html>"""
        self.assertIn("table-caption", [v["id"] for v in check_html(bad)])
        self.assertNotIn("table-caption", [v["id"] for v in check_html(good)])

    def test_html_has_lang_pass(self):
        source = """<html lang="en"><body><main></main></body></html>"""
        self.assertNotIn("html-has-lang", [v["id"] for v in check_html(source)])

    def test_aria_invalid_with_describedby_passes(self):
        source = """<html lang="en"><main>
            <input id="email" aria-invalid="true" aria-describedby="email-err">
            <span id="email-err">Invalid email</span>
        </main></html>"""
        self.assertNotIn("aria-invalid-no-desc", [v["id"] for v in check_html(source)])

    def test_focus_visible_inline_style(self):
        source = """<html lang="en"><main><button style="outline: none;">X</button></main></html>"""
        violations = check_focus_visible(source)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["id"], "focus-visible")

    def test_map_axe_to_violations(self):
        raw = {
            "violations": [{
                "id": "color-contrast",
                "impact": "serious",
                "help": "Elements must have sufficient color contrast",
                "helpUrl": "https://dequeuniversity.com/rules/axe/4.9/color-contrast",
                "tags": ["wcag2aa", "wcag143"],
                "nodes": [{"html": "<p>Low contrast</p>", "target": ["p"]}],
            }]
        }
        mapped = map_axe_to_violations(raw)
        self.assertEqual(len(mapped), 1)
        self.assertEqual(mapped[0]["id"], "axe-color-contrast")
        self.assertEqual(mapped[0]["severity"], "serious")

    def test_dedupe_axe_by_id_and_line(self):
        static = [{
            "id": "axe-color-contrast",
            "severity": "serious",
            "line": 3,
            "message": "static",
            "fix": "",
            "wcag": "",
        }]
        axe = [{
            "id": "axe-color-contrast",
            "severity": "serious",
            "line": 3,
            "message": "axe",
            "fix": "",
            "wcag": "",
        }, {
            "id": "axe-image-alt",
            "severity": "critical",
            "line": 5,
            "message": "axe alt",
            "fix": "",
            "wcag": "",
        }]
        merged = dedupe_violations(static, axe)
        self.assertEqual(len(merged), 2)

    @patch("a11y_axe.run_axe")
    @patch("a11y_axe.is_node_available", return_value=True)
    def test_merge_axe_results_graceful_when_run_fails(self, _node, mock_run):
        mock_run.return_value = None
        passing = self.demo_dir / "passing_page.html"
        violations = check_html(passing.read_text(encoding="utf-8"))
        merged = merge_axe_results(passing, violations)
        self.assertEqual(merged, violations)


if __name__ == "__main__":
    unittest.main()
