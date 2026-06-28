![PyPI](https://img.shields.io/pypi/v/accessibility-champion)
![GitHub release](https://img.shields.io/github/v/release/notEhEnG/accessibility-champion)
![GitHub stars](https://img.shields.io/github/stars/notEhEnG/accessibility-champion)

# Accessibility Champion

Accessibility Champion is a lightweight, static accessibility linter for HTML files. It helps identify common WCAG 2.2 AA violations in your markup and generates an accessibility score to help developers triage and fix issues quickly.

The linter uses Python's `HTMLParser` with a **rule-registry architecture**: a thin dispatcher forwards parse events to focused rule classes, keeping each check isolated and easy to extend.

## Installation

Install from PyPI (Python 3.8+):

```bash
pip install accessibility-champion
```

Optional extras:

```bash
pip install accessibility-champion[css]   # tinycss2 for CSS heuristics (roadmap)
pip install accessibility-champion[dev]     # build, twine, and coverage
```

After install, use the `a11y-lint` console script:

```bash
a11y-lint path/to/your/file.html
```

Install from a cloned repo (development):

```bash
git clone https://github.com/notEhEnG/accessibility-champion.git
cd accessibility-champion
pip install -e .
```

## Quick Start

Run the linter against any HTML file to get a human-readable text report:

```bash
a11y-lint path/to/your/file.html
# or, from a source checkout:
python3 a11y_lint.py path/to/your/file.html
```

Try the included demo fixtures:

```bash
a11y-lint demo/broken_page.html   # exits 1 — many violations
a11y-lint demo/passing_page.html  # exits 0 — score 100/100
```

### CLI Options

| Flag | Description |
|------|-------------|
| `--json` | Output results as a JSON array (one entry per file) |
| `--fragment` | Treat input as an HTML fragment; skip full-page landmark and single-`<h1>` checks |
| `--full-page` | Force full-page mode even when `<html>` / `<body>` tags are absent |
| `--axe` | Merge axe-core results when Node.js and `axe-core` + `jsdom` are installed (see below) |

**Auto-detection:** When neither `--fragment` nor `--full-page` is passed, the linter treats markup as a **fragment** unless it contains an `<html>` or `<body>` tag. Full-page landmark checks (`<main>`, `<header>`, `<nav>`, `<footer>`, single `<h1>`) only run in full-page mode.

```bash
# JSON output for CI
a11y-lint path/to/your/file.html --json

# Lint a partial HTML snippet (e.g., a component template)
a11y-lint path/to/fragment.html --fragment

# Static + rendered audit (requires Node.js)
npm install axe-core jsdom
a11y-lint path/to/your/file.html --axe
```

### Exit Codes

- `0` — no violations found across all linted files
- `1` — one or more violations found, or a file could not be read

Any violation severity (including minor) causes a non-zero exit when `--json` is not used for machine parsing.

## Output Format

### Text Report

The default text output provides a score out of 100, followed by violations grouped by severity. Each violation includes:

- **id** — stable rule identifier (e.g., `image-alt`, `form-group-fieldset`)
- **line** — source line number
- **message** — human-readable description
- **fix** — suggested remediation
- **wcag** — relevant WCAG success criterion

### JSON Report

```json
[
  {
    "file": "demo/broken_page.html",
    "score": 0,
    "violations": [
      {
        "id": "html-has-lang",
        "severity": "serious",
        "line": 2,
        "message": "<html> tag is missing a lang attribute",
        "fix": "Add lang=\"en\" (or appropriate language code) to the <html> tag",
        "wcag": "3.1.1 Language of Page"
      },
      {
        "id": "image-alt",
        "severity": "critical",
        "line": 14,
        "message": "<img> is missing an alt attribute",
        "fix": "Add alt=\"[description]\" for informational images, or alt=\"\" role=\"presentation\" for decorative ones",
        "wcag": "1.1.1 Non-text Content"
      }
    ]
  }
]
```

### Programmatic API

```python
from a11y_lint import check_html, score

violations = check_html(source)                  # auto-detect fragment vs full page
violations = check_html(source, fragment=True) # force fragment mode
total = score(violations)
```

## Scoring Model

The Accessibility Score starts at 100. Deductions are grouped **by rule ID** so repeated instances of the same issue do not zero out the score before other problems are reflected.

| Severity | Base cap (1 hit) | Examples |
|----------|------------------|----------|
| **Critical** | −20 | Missing `alt`, unlabelled form controls, buttons without accessible names |
| **Serious** | −10 | Missing `lang`, duplicate IDs, generic link text, missing `iframe` title |
| **Moderate** | −5 | Skipped heading levels, missing `<main>`, ungrouped radio/checkbox sets |
| **Minor** | −2 | Missing `autocomplete` on personal-data fields, optional landmark regions |

**Per-rule scaling** (applied once per rule ID, not per violation):

| Violations of same rule | Multiplier | Example (`image-alt`, critical) |
|-------------------------|------------|----------------------------------|
| 1 | 1× base cap | −20 |
| 2–4 | 1.5× base cap | −30 (capped) |
| 5+ | 2× base cap | −30 (absolute max per rule) |

No single rule can deduct more than **−30** points. The total score is still clamped to a minimum of 0.

**Worked example:** Six `image-alt` violations (critical, base −20) use the 5+ multiplier: `min(20 × 2.0, 30) = −30` total for that rule — not `6 × 20 = −120`.

## Current Checks

### Pillar 1 — Perceivable

| Rule ID | What it checks |
|---------|----------------|
| `html-has-lang` | `<html>` missing `lang` attribute |
| `image-alt` | `<img>` missing `alt` attribute |
| `image-alt-quality` | Generic `alt` text (`image`, `photo`, `logo`, etc.) |
| `no-autoplay` | `<video>` / `<audio>` with `autoplay` |
| `video-captions` | `<video>` missing `<track kind="captions">` |
| `audio-transcript` | `<audio>` without nearby transcript link/text (heuristic) |
| `document-title` | Full page missing non-empty `<title>` in `<head>` |

### Pillar 2 — Operable

| Rule ID | What it checks |
|---------|----------------|
| `button-name` | `<button>` with no accessible name (text, `aria-label`, child `<img alt>`, or `<svg><title>`) |
| `link-name` | `<a>` with generic text (`click here`, `read more`, `here`, `more`, etc.) |
| `focus-visible` | `outline: none` / `outline: 0` in CSS without a matching `:focus` / `:focus-visible` fallback rule |
| `skip-link` | Full page with `<nav>` missing a skip-to-main-content link |
| `tabindex-positive` | Any `tabindex` value greater than 0 |
| `button-type-missing` | `<button>` inside `<form>` without explicit `type` attribute |
| `target-blank-no-warning` | `target="_blank"` without accessible new-window warning |

Focus-outline analysis parses CSS rule blocks inside `<style>` elements and inline `style=""` attributes. It matches base selectors (e.g., `.btn`) to companion `:focus-visible` rules that restore a visible outline.

### Pillar 3 — Understandable

| Rule ID | What it checks |
|---------|----------------|
| `input-unlabelled` | Form control has no `id`, is not wrapped in `<label>`, and has no `aria-label` |
| `input-missing-label` | Control has an `id` but no matching `<label for="...">` |
| `placeholder-as-label` | `placeholder` used without a real label or `aria-label` |
| `input-autocomplete` | Personal-data inputs (`email`, `password`, `tel`, or `name`/`address`-like fields) missing `autocomplete` |
| `aria-invalid-no-desc` | `aria-invalid="true"` without `aria-describedby` pointing to an error element |

Applies to `<input>`, `<select>`, and `<textarea>`.

### Pillar 4 — Robust & Semantic Structure

| Rule ID | What it checks |
|---------|----------------|
| `duplicate-id` | Duplicate `id` attribute values |
| `form-group-fieldset` | Multiple radio/checkbox inputs sharing a `name` not wrapped in `<fieldset>` + `<legend>` (one violation per group) |
| `aria-describedby-missing-target` | `aria-describedby` references an `id` that does not exist |
| `aria-labelledby-target` | `aria-labelledby` references an `id` that does not exist |
| `heading-order` | Skipped heading levels (e.g., `<h1>` → `<h3>`) |
| `heading-single-h1` | More than one `<h1>` on a full page |
| `frame-title` | `<iframe>` missing `title` |
| `table-th` | Data table missing `<th>` header cells |
| `table-caption` | Data table missing `<caption>` |
| `missing-main` | Full page missing `<main>` landmark |
| `missing-header-landmark` | Full page missing `<header>` / `role="banner"` |
| `missing-nav-landmark` | Full page missing `<nav>` / `role="navigation"` |
| `missing-footer-landmark` | Full page missing `<footer>` / `role="contentinfo"` |

Presentation tables (`role="presentation"`) are exempt from table header/caption checks.

## Architecture

```
a11y_lint.py      CLI entry point; thin HTMLParser dispatcher
a11y_context.py   ParseContext (shared state) and TagAttrs helpers
a11y_rules/       Individual A11yRule classes registered via all_rules()
a11y_focus.py     CSS rule-block parser for focus-outline checks
a11y_axe.py       Optional axe-core merge via inline Node.js script (--axe)
```

To add a new check, create a class extending `A11yRule` under `a11y_rules/` with `on_starttag`, `on_endtag`, `on_data`, and/or `finalize` hooks, then register it in `a11y_rules/__init__.py`.

## AI Agent Integration

[`SKILL.md`](./SKILL.md) is an **agent skill file** for Claude, Cursor, Copilot, and similar LLM coding agents. It tells agents how to run accessibility audits, interpret linter output, and know which checks still need human review.

**Who uses it:** AI agents invoked to audit HTML/JSX/Vue/Svelte codebases, produce severity-ranked reports, or apply safe fixes.

**Two workflows it defines:**

| Workflow | When to use |
|----------|-------------|
| **FULL_AUDIT** | User shares code or a page — run `a11y-lint` on `.html` first, then agent manual checks for contrast, keyboard, ARIA behavior, and intent |
| **AUTO_FIX** | User wants fixes applied — apply copy-paste-safe patches from violation `fix` fields; escalate `[manual]` items |

**Update `SKILL.md` when you:**

- Add or rename rule IDs
- Add or change CLI flags (e.g. `--fragment`, `--axe`)
- Change the violation JSON schema or scoring model
- Change FULL_AUDIT or AUTO_FIX steps

Agents load `SKILL.md` as context; keeping it in sync with the linter avoids stale audit instructions.

## Running Tests

```bash
python3 -m unittest test_a11y_lint -v
```

The suite covers fixture pages, individual rules, CLI behavior, fragment mode, scoring caps, axe mapping, and edge cases (54 tests). **Every new rule must include tests** that verify both failing and passing markup.

With dev dependencies installed:

```bash
coverage run -m unittest test_a11y_lint -v && coverage report -m
```

## Limitations

⚠️ **This is a static linter and does not replace manual accessibility review.**

While it catches a meaningful share of common HTML accessibility issues, automated tooling cannot validate:

- **Interaction intent** — Does a custom widget actually behave like its native equivalent?
- **Meaningful text** — Is the `alt` text actually descriptive in context?
- **Keyboard navigation** — Are there keyboard traps or focus-management issues?
- **Visual contrast** — Real contrast ratios require rendering the DOM and CSS.

Always supplement this tool with screen reader testing, keyboard navigation audits, and dynamic tools like axe-core.

## Demo Fixtures

| File | Purpose |
|------|---------|
| `demo/broken_page.html` | Intentionally broken markup; demonstrates linter output |
| `demo/passing_page.html` | Accessible page that scores 100/100 |
| `demo/expected_output.txt` | Reference text output for `broken_page.html` |

## Project Layout

| Path | Purpose |
|------|---------|
| `a11y_lint.py` | CLI entry point and thin HTML parser dispatcher |
| `a11y_context.py` | Shared parse context and attribute helpers |
| `a11y_rules/` | Individual accessibility rule implementations |
| `a11y_focus.py` | CSS focus-outline checks for `<style>` blocks and inline styles |
| `a11y_axe.py` | Optional axe-core merge (`--axe`) |
| `demo/broken_page.html` | Fixture demonstrating failing checks |
| `demo/passing_page.html` | Fixture demonstrating passing checks |
| `test_a11y_lint.py` | Automated test suite |
| `SKILL.md` | AI agent integration guidelines — update when rule IDs or CLI flags change |

## Roadmap

See [ROADMAP.md](./ROADMAP.md) for the phased plan to expand coverage toward full WCAG-aligned auditing (static rules → CSS analysis → axe-core integration).

## Contributing

1. Keep changes small and surgical.
2. Add new rules as `A11yRule` subclasses under `a11y_rules/`; register them in `all_rules()`.
3. Add tests to `test_a11y_lint.py` for both failing and passing markup.
4. Prefer the HTML parser over regular expressions for structural checks.
5. Update this README when adding new rule IDs, CLI flags, or architectural changes.

## License

MIT License — see [LICENSE](./LICENSE).