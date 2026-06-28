#!/usr/bin/env python3
"""
accessibility-champion static linter
Checks a single HTML file for common WCAG 2.2 AA issues.
"""

import sys
import json
import re
import argparse
from pathlib import Path
from html.parser import HTMLParser
from collections import defaultdict

SEVERITY_WEIGHTS = {"critical": 20, "serious": 10, "moderate": 5, "minor": 2}

def check_focus_visible(source):
    """
    Scans raw HTML/CSS source for outline suppression (outline: none or outline: 0)
    without a corresponding :focus-visible or :focus fallback.
    Returns a list of violation dictionaries.
    """
    violations = []
    for m in re.finditer(r'outline\s*:\s*(?:none|0)\b', source):
        line = source[:m.start()].count("\n") + 1
        context_start = max(0, m.start() - 200)
        context_end = min(len(source), m.end() + 200)
        context = source[context_start:context_end]
        if ':focus-visible' not in context and ':focus' not in context:
            violations.append({
                "id": "focus-visible",
                "severity": "serious",
                "line": line,
                "message": "outline: none/0 detected without a :focus-visible replacement",
                "fix": "Replace with :focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }",
                "wcag": "2.4.7 Focus Visible"
            })
    return violations

class A11yHTMLParser(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.source = source
        self.violations = []
        self.tag_stack = []
        
        # State tracking for some checks
        self.has_main = False
        self.headings_seen = []
        
        self.table_depth = 0
        self.current_table_has_th = False
        self.current_table_has_caption = False
        self.current_table_is_presentation = False
        self.current_table_line = 0
        
        # Button accessible name tracking
        self.button_depth = 0
        self.current_button = None # To track button text
        self.in_svg_depth = 0
        self.in_title_depth = 0
        self.current_title_text = ""
        
        self.link_depth = 0
        self.current_link = None
        
        self.label_fors = set()
        self.inputs_needing_labels = []

        # New state variables for enhancements
        self.ids_seen = set()
        self.duplicate_ids = set() # set of tuples (id, line)
        self.fieldset_stack = [] # stack of dicts: {"has_legend": bool}
        self.radio_checkbox_inputs = [] # list of dicts: {"name": name, "line": line, "type": type, "valid": bool}
        self.described_by_checks = [] # list of dicts: {"described_by": str, "line": line}
        
        # Landmark completeness tracking
        self.is_full_page = False
        self.has_header = False
        self.has_nav = False
        self.has_footer = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        attrs_lower = {k.lower(): (v.lower() if v else v) for k, v in attrs_dict.items()}
        line, _ = self.getpos()
        
        self.tag_stack.append(tag)
        
        # Duplicate ID Detection
        id_val = attrs_dict.get("id")
        if id_val:
            if id_val in self.ids_seen:
                self.duplicate_ids.add((id_val, line))
            self.ids_seen.add(id_val)

        if tag in ("html", "body"):
            self.is_full_page = True

        if tag == "header" or attrs_lower.get("role") == "banner":
            self.has_header = True
        if tag == "nav" or attrs_lower.get("role") == "navigation":
            self.has_nav = True
        if tag == "footer" or attrs_lower.get("role") == "contentinfo":
            self.has_footer = True
        if tag == "main" or attrs_lower.get("role") == "main":
            self.has_main = True
            
        # Fieldset/Legend state tracking
        if tag == "fieldset":
            self.fieldset_stack.append({"has_legend": False})
        if tag == "legend" and self.fieldset_stack:
            self.fieldset_stack[-1]["has_legend"] = True

        # 1. Lang attribute on <html>
        if tag == "html":
            if "lang" not in attrs_lower:
                self.violations.append({
                    "id": "html-has-lang",
                    "severity": "serious",
                    "line": line,
                    "message": "<html> tag is missing a lang attribute",
                    "fix": 'Add lang="en" (or appropriate language code) to the <html> tag',
                    "wcag": "3.1.1 Language of Page"
                })

        # 2. Images without alt and alt quality
        if tag == "img":
            # Image within button accumulates its alt as accessible text
            if self.button_depth > 0 and self.current_button:
                alt = attrs_dict.get("alt", "")
                if alt:
                    self.current_button["text"] += " " + alt

            if "alt" not in attrs_lower:
                self.violations.append({
                    "id": "image-alt",
                    "severity": "critical",
                    "line": line,
                    "message": '<img> is missing an alt attribute',
                    "fix": 'Add alt="[description]" for informational images, or alt="" role="presentation" for decorative ones',
                    "wcag": "1.1.1 Non-text Content"
                })
            else:
                alt_text = attrs_lower["alt"].strip()
                if alt_text in ("image", "picture", "photo", "logo", "icon", "graphic"):
                    self.violations.append({
                        "id": "image-alt-quality",
                        "severity": "moderate",
                        "line": line,
                        "message": f'<img> alt text "{alt_text}" is not descriptive (human review required)',
                        "fix": 'Describe the purpose and meaning of the image, not what it is',
                        "wcag": "1.1.1 Non-text Content"
                    })

        # SVG/Title state tracking for accessible names
        if tag == "svg":
            self.in_svg_depth += 1
        if tag == "title":
            self.in_title_depth += 1
            self.current_title_text = ""

        # 3. Inputs without labels and Autocomplete
        if tag == "input":
            itype = attrs_lower.get("type", "text")
            if itype not in ('hidden', 'submit', 'button', 'image', 'reset'):
                has_aria_label = "aria-label" in attrs_lower or "aria-labelledby" in attrs_lower
                if not has_aria_label:
                    input_id = attrs_dict.get("id")
                    if not input_id:
                        # Check if it's wrapped in a label
                        if "label" not in self.tag_stack:
                            self.violations.append({
                                "id": "label-content-name-mismatch",
                                "severity": "critical",
                                "line": line,
                                "message": f'<input type="{itype}"> has no id and is not wrapped in a <label> — cannot be associated with a <label>',
                                "fix": 'Add a unique id attribute and a <label for="that-id"> element, wrap it in a <label>, or add aria-label="..."',
                                "wcag": "1.3.1 Info and Relationships"
                            })
                    else:
                        if "label" not in self.tag_stack:
                            self.inputs_needing_labels.append({"id": input_id, "line": line, "itype": itype})

            # Autocomplete check
            name_id = (attrs_lower.get("name", "") + attrs_lower.get("id", "")).lower()
            needs_autocomplete = False
            if itype in ("email", "password", "tel"):
                needs_autocomplete = True
            elif itype == "text" and any(x in name_id for x in ("name", "address", "city", "zip", "phone", "email")):
                needs_autocomplete = True

            if needs_autocomplete and "autocomplete" not in attrs_lower:
                self.violations.append({
                    "id": "input-autocomplete",
                    "severity": "minor",
                    "line": line,
                    "message": f"Input field (type='{itype}', id/name='{name_id}') requesting personal data is missing an autocomplete attribute",
                    "fix": 'Add an appropriate autocomplete attribute (e.g., autocomplete="email")',
                    "wcag": "1.3.5 Identify Input Purpose"
                })

            # Fieldset/Legend grouping check for radio/checkbox
            if itype in ("radio", "checkbox"):
                name = attrs_lower.get("name")
                if name:
                    in_fieldset = len(self.fieldset_stack) > 0
                    has_legend = self.fieldset_stack[-1]["has_legend"] if in_fieldset else False
                    self.radio_checkbox_inputs.append({
                        "name": name,
                        "line": line,
                        "type": itype,
                        "valid": in_fieldset and has_legend
                    })

        if tag in ("input", "select", "textarea"):
            described_by = attrs_dict.get("aria-describedby")
            if described_by:
                self.described_by_checks.append({"described_by": described_by, "line": line})

        if tag == "label":
            if "for" in attrs_dict:
                self.label_fors.add(attrs_dict["for"])

        # 4. Buttons with no accessible name
        if tag == "button":
            self.button_depth += 1
            has_aria = "aria-label" in attrs_lower or "aria-labelledby" in attrs_lower
            if self.button_depth == 1:
                self.current_button = {"line": line, "has_aria": has_aria, "text": ""}
                
        # 6. Links with generic text
        if tag == "a":
            self.link_depth += 1
            if self.link_depth == 1:
                self.current_link = {"line": line, "text": ""}

        # 7. Table checks
        if tag == "table":
            self.table_depth += 1
            if self.table_depth == 1:
                self.current_table_has_th = False
                self.current_table_has_caption = False
                self.current_table_is_presentation = (attrs_lower.get("role") == "presentation")
                self.current_table_line = line
        if tag == "th" and self.table_depth > 0:
            self.current_table_has_th = True
        if tag == "caption" and self.table_depth > 0:
            self.current_table_has_caption = True

        # 8. Heading hierarchy
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            if self.headings_seen:
                prev_level = self.headings_seen[-1]
                if level > prev_level + 1:
                    self.violations.append({
                        "id": "heading-order",
                        "severity": "moderate",
                        "line": line,
                        "message": f"Heading level skipped: H{prev_level} → H{level}",
                        "fix": f"Use H{prev_level + 1} here, or restructure heading hierarchy to avoid gaps",
                        "wcag": "1.3.1 Info and Relationships"
                    })
            self.headings_seen.append(level)

        # 9. iframes without title
        if tag == "iframe":
            if "title" not in attrs_lower:
                self.violations.append({
                    "id": "frame-title",
                    "severity": "serious",
                    "line": line,
                    "message": "<iframe> is missing a title attribute",
                    "fix": 'Add title="Description of iframe content" to the <iframe>',
                    "wcag": "2.4.1 Bypass Blocks"
                })

        # 10. autoplay media
        if tag in ("video", "audio"):
            if "autoplay" in attrs_lower:
                self.violations.append({
                    "id": "no-autoplay",
                    "severity": "serious",
                    "line": line,
                    "message": "Media with autoplay — can disorient screen reader users and violate WCAG 1.4.2",
                    "fix": "Remove autoplay, or add controls and a mechanism to pause/stop the media",
                    "wcag": "1.4.2 Audio Control"
                })

    def handle_endtag(self, tag):
        if self.tag_stack:
            for i in range(len(self.tag_stack)-1, -1, -1):
                if self.tag_stack[i] == tag:
                    self.tag_stack = self.tag_stack[:i]
                    break
        
        if tag == "fieldset" and self.fieldset_stack:
            self.fieldset_stack.pop()

        if tag == "title":
            self.in_title_depth = max(0, self.in_title_depth - 1)
            if self.in_title_depth == 0 and self.in_svg_depth > 0 and self.button_depth > 0 and self.current_button:
                self.current_button["text"] += " " + self.current_title_text
                
        if tag == "svg":
            self.in_svg_depth = max(0, self.in_svg_depth - 1)

        if tag == "button":
            if self.button_depth == 1 and self.current_button:
                if not self.current_button["has_aria"] and not self.current_button["text"].strip():
                    self.violations.append({
                        "id": "button-name",
                        "severity": "critical",
                        "line": self.current_button["line"],
                        "message": '<button> has no accessible name (empty inner text, no aria-label, and no descriptive child images/svgs)',
                        "fix": 'Add aria-label="[action description]" or visible text content inside the button',
                        "wcag": "4.1.2 Name, Role, Value"
                    })
                self.current_button = None
            self.button_depth = max(0, self.button_depth - 1)
            
        if tag == "a":
            if self.link_depth == 1 and self.current_link:
                text = self.current_link["text"].strip().lower()
                generic_prefixes = ("click here", "read more", "learn more")
                generic_exacts = ("here", "more")
                is_generic = False
                matched_phrase = ""
                
                for prefix in generic_prefixes:
                    if text == prefix or text.startswith(prefix + " "):
                        is_generic = True
                        matched_phrase = prefix
                        break
                
                if not is_generic:
                    for exact in generic_exacts:
                        if text == exact:
                            is_generic = True
                            matched_phrase = exact
                            break
                            
                if is_generic:
                    self.violations.append({
                        "id": "link-name",
                        "severity": "serious",
                        "line": self.current_link["line"],
                        "message": f'Link with generic text "{text}" (matches phrase "{matched_phrase}") — meaningless out of context',
                        "fix": 'Use descriptive link text like "Read the accessibility guide" or add aria-label="..."',
                        "wcag": "2.4.4 Link Purpose (In Context)"
                    })
                self.current_link = None
            self.link_depth = max(0, self.link_depth - 1)

        if tag == "table":
            if self.table_depth == 1:
                if not self.current_table_is_presentation:
                    if not self.current_table_has_th:
                        self.violations.append({
                            "id": "table-th",
                            "severity": "serious",
                            "line": self.current_table_line,
                            "message": "Data table has no <th> header cells",
                            "fix": "Add <th scope='col'> for column headers and <th scope='row'> for row headers",
                            "wcag": "1.3.1 Info and Relationships"
                        })
                    if not self.current_table_has_caption:
                        self.violations.append({
                            "id": "table-caption",
                            "severity": "moderate",
                            "line": self.current_table_line,
                            "message": "Table is missing a <caption> describing its purpose",
                            "fix": "Add <caption>Table description</caption> as first child of <table>",
                            "wcag": "1.3.1 Info and Relationships"
                        })
            self.table_depth = max(0, self.table_depth - 1)

    def handle_data(self, data):
        if self.button_depth > 0 and self.current_button:
            if self.in_title_depth > 0 and self.in_svg_depth > 0:
                self.current_title_text += data
            elif not self.in_svg_depth:
                self.current_button["text"] += data
        if self.link_depth > 0 and self.current_link:
            self.current_link["text"] += data
            
    def finalize(self):
        # Post-parse checks
        if not self.has_main:
            self.violations.append({
                "id": "missing-main",
                "severity": "moderate",
                "line": 1,
                "message": "Page is missing a <main> landmark",
                "fix": "Wrap the primary content of the page in a <main> tag",
                "wcag": "1.3.1 Info and Relationships"
            })
            
        # Optional Landmark checks for full pages
        if self.is_full_page:
            if not self.has_header:
                self.violations.append({
                    "id": "missing-header-landmark",
                    "severity": "minor",
                    "line": 1,
                    "message": "Page is missing a <header> or role='banner' landmark (manual review recommended)",
                    "fix": "Wrap page headers in a <header> element or add role='banner'",
                    "wcag": "1.3.1 Info and Relationships"
                })
            if not self.has_nav:
                self.violations.append({
                    "id": "missing-nav-landmark",
                    "severity": "minor",
                    "line": 1,
                    "message": "Page is missing a <nav> or role='navigation' landmark (manual review recommended)",
                    "fix": "Wrap page navigation in a <nav> element or add role='navigation'",
                    "wcag": "1.3.1 Info and Relationships"
                })
            if not self.has_footer:
                self.violations.append({
                    "id": "missing-footer-landmark",
                    "severity": "minor",
                    "line": 1,
                    "message": "Page is missing a <footer> or role='contentinfo' landmark (manual review recommended)",
                    "fix": "Wrap page footer in a <footer> element or add role='contentinfo'",
                    "wcag": "1.3.1 Info and Relationships"
                })

        # Duplicate ID check
        for id_val, line in sorted(self.duplicate_ids, key=lambda x: x[1]):
            self.violations.append({
                "id": "duplicate-id",
                "severity": "serious",
                "line": line,
                "message": f"Duplicate id attribute value '{id_val}' detected",
                "fix": "Ensure all id attributes on the page are unique",
                "wcag": "4.1.1 Parsing"
            })

        # Fieldset/Legend checks for grouped radio/checkboxes
        groups = defaultdict(list)
        for item in self.radio_checkbox_inputs:
            groups[(item["type"], item["name"])].append(item)
        for (itype, name), items in groups.items():
            if len(items) > 1:
                for item in items:
                    if not item["valid"]:
                        self.violations.append({
                            "id": "form-group-fieldset",
                            "severity": "moderate",
                            "line": item["line"],
                            "message": f"Grouped {itype} inputs (name='{name}') should be wrapped in a <fieldset> with a <legend>",
                            "fix": f"Wrap the group of {itype} inputs in a <fieldset> and add a descriptive <legend>",
                            "wcag": "1.3.1 Info and Relationships"
                        })

        # aria-describedby checks
        for check in self.described_by_checks:
            targets = check["described_by"].split()
            for target in targets:
                if target not in self.ids_seen:
                    self.violations.append({
                        "id": "aria-describedby-missing-target",
                        "severity": "serious",
                        "line": check["line"],
                        "message": f"aria-describedby target '{target}' does not exist in the document",
                        "fix": f"Ensure there is an element with id='{target}' to provide the description",
                        "wcag": "1.3.1 Info and Relationships"
                    })
        
        # 3. Inputs missing labels (deferred check)
        for inp in self.inputs_needing_labels:
            if inp["id"] not in self.label_fors:
                self.violations.append({
                    "id": "input-missing-label",
                    "severity": "critical",
                    "line": inp["line"],
                    "message": f'<input id="{inp["id"]}"> has no associated <label for="{inp["id"]}">',
                    "fix": f'Add <label for="{inp["id"]}">Descriptive label</label> before or wrapping the input',
                    "wcag": "3.3.2 Labels or Instructions"
                })
        
        return self.violations

def check_html(source):
    parser = A11yHTMLParser(source)
    parser.feed(source)
    violations = parser.finalize()
    violations.extend(check_focus_visible(source))
    return sorted(violations, key=lambda x: x["line"])

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
    parser = argparse.ArgumentParser(description="accessibility-champion static linter\nChecks HTML files for common WCAG 2.2 AA issues.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("files", nargs="+", help="HTML file(s) to lint")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    
    args = parser.parse_args()

    results = []
    has_errors = False
    
    for path in args.files:
        try:
            source = Path(path).read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"File not found: {path}", file=sys.stderr)
            has_errors = True
            continue

        violations = check_html(source)
        s = score(violations)
        results.append({"file": path, "score": s, "violations": violations})
        
        if len(violations) > 0:
            has_errors = True

        if not args.json:
            print(format_report(path, violations, s))

    if args.json:
        print(json.dumps(results, indent=2))
        
    sys.exit(1 if has_errors else 0)

if __name__ == "__main__":
    main()
