# Accessibility Champion

Accessibility Champion is a lightweight, static accessibility linter for HTML files. It helps identify common WCAG 2.2 AA violations in your markup and generates an accessibility score to help developers triage and fix issues quickly.

## Quick Start

Run the linter against any HTML file to get a human-readable text report:

```bash
python3 a11y_lint.py path/to/your/file.html
```

To output the results in JSON format (useful for CI/CD pipelines and automated tooling):

```bash
python3 a11y_lint.py path/to/your/file.html --json
```

## Output Format

The default text output provides a score out of 100, followed by a list of accessibility violations grouped by severity. Each violation includes the exact line number, a description of the issue, a suggested fix, and the corresponding WCAG criteria.

If violations are found, the script exits with status code `1`. If no violations are found (or only minor/passing items exist), it exits with `0`.

## Scoring Model

The Accessibility Score starts at 100 and deducts points based on the severity of the issues found:
- **Critical (-20 pts):** Completely blocks access for a disability group (e.g., missing `alt` on informational images, no form labels).
- **Serious (-10 pts):** Significantly degrades experience (e.g., missing `lang` attribute, missing `title` on `iframe`).
- **Moderate (-5 pts):** Creates friction but has workarounds (e.g., skipped heading levels, missing `<main>` landmark).
- **Minor (-2 pts):** Best-practice or AAA recommendations (e.g., missing autocomplete on personal data fields).

The score is clamped to a minimum of 0.

## Current Checks

The linter currently performs the following checks:
- `<html lang="en">` presence
- `<img>` missing `alt` attributes or using generic/low-quality `alt` text (e.g., "image", "photo")
- Form `<input>` elements missing associated labels or `id` attributes
- Form inputs requesting personal data missing `autocomplete` attributes
- `<button>` elements missing accessible names (via inner text or `aria-label`)
- Links (`<a>`) using generic text (e.g., "click here", "read more")
- Tables missing `<th>` header cells or `<caption>` elements
- Skipped heading hierarchy levels (e.g., jumping from `<h1>` to `<h3>`)
- `<iframe>` elements missing `title` attributes
- Media elements (`<video>`, `<audio>`) with `autoplay` enabled
- Presence of a `<main>` landmark
- Focus visibility suppression (`outline: none` without a `:focus-visible` fallback)

## Limitations

⚠️ **This is a static linter and does not replace manual accessibility review.**
While it catches 30-50% of common HTML accessibility issues, automated tooling cannot validate:
- **Interaction intent:** Does a custom widget actually behave like its native equivalent?
- **Meaningful text:** Is the `alt` text actually descriptive in context?
- **Keyboard navigation:** Are there keyboard traps or focus-management issues?
- **Visual contrast:** Real contrast ratios require rendering the DOM and CSS.

Always supplement this tool with screen reader testing, keyboard navigation audits, and dynamic tools like Axe-core.

## Demo Fixtures

The `demo/` directory contains two HTML files used to demonstrate and test the linter:
- **`demo/broken_page.html`**: An HTML file intentionally loaded with accessibility violations to demonstrate the linter's output.
- **`demo/passing_page.html`**: A perfectly accessible HTML file that scores 100/100 and passes all checks.

## Project Layout

- `a11y_lint.py` — The core HTML parser and accessibility linter script.
- `demo/broken_page.html` — Fixture demonstrating failing checks.
- `demo/passing_page.html` — Fixture demonstrating passing checks.
- `test_a11y_lint.py` — The automated test suite for the linter.
- `SKILL.md` — AI Agent integration guidelines detailing the overarching accessibility audit workflows.

## Contributing

When contributing to Accessibility Champion:
1. Try to keep changes small and surgical.
2. If you add a new accessibility rule, you **must** add tests to `test_a11y_lint.py` verifying that it correctly flags bad markup and correctly ignores good markup.
3. Keep the checks resilient and fast. When possible, use the robust HTML parser rather than regular expressions.
