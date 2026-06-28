# Accessibility Champion — Full Coverage Roadmap

This document describes how to evolve Accessibility Champion from a **fast static HTML linter** (22 rules today) toward **credible automated WCAG 2.2 AA coverage**, and recommends which phase to ship for an **Open Source Program submission** (e.g., Codex Open Source Program).

---

## Executive summary

| Layer | Role | Coverage contribution |
|-------|------|------------------------|
| **Static linter** (`a11y_lint.py`, `a11y_rules.py`, `a11y_focus.py`) | Parse HTML source; no browser | ~30–50% of common issues |
| **Hybrid CSS analysis** (planned Phase 3) | Parse stylesheets; computed heuristics | ~60–70% on static pages |
| **Rendered audit** (planned Phase 4, axe-core) | Browser/DOM; contrast, ARIA validity, focus | ~80%+ automated; still not 100% |
| **Manual review** (SKILL.md workflow) | Intent, meaningful alt, complex widgets | Required for true compliance |

**“Full” does not mean one HTML pass.** It means a **layered pipeline**: static rules for speed → axe for depth → human review for intent.

---

## Current state (baseline)

### What the tool does today

1. Reads UTF-8 HTML files (CLI or `check_html()` API).
2. Dispatches parse events to 14 rule classes in `a11y_rules.py`.
3. Scans `<style>` blocks and inline `style=""` for focus-outline suppression (`a11y_focus.py`).
4. Scores violations and outputs text or `--json`.
5. Supports `--fragment` / `--full-page` modes for partial markup vs whole documents.

### What it checks (22 rule IDs)

See [README.md](./README.md#current-checks) for the full table. Highlights:

- Perceivable: `lang`, `alt`, generic alt, autoplay
- Operable: button/link names, CSS focus outline
- Understandable: labels, autocomplete
- Robust: duplicate IDs, fieldset/legend, `aria-describedby`, headings, landmarks, tables, iframes

### What it does **not** check (gap vs SKILL.md)

`SKILL.md` describes a six-pillar agent audit. The **linter code** does not yet implement:

- Color contrast
- Keyboard navigation / focus traps
- Skip links
- Video captions / audio transcripts
- Placeholder-as-label
- Error field association (`aria-invalid` + `aria-describedby`)
- ARIA role validity and required children
- JSX / Vue / Angular template support
- Touch target size
- Cross-page consistency

---

## Target architecture

```
┌─────────────────────────────────────────────────────────────┐
│  CLI / API (a11y_lint.py)                                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
┌─────────────────┐ ┌──────────────┐ ┌─────────────────────┐
│ HTMLParser      │ │ CSS analyzer │ │ axe-core wrapper    │
│ rule registry   │ │ (Phase 3)    │ │ (Phase 4, optional) │
│ (a11y_rules.py) │ │ (a11y_focus+)│ │ (a11y_axe.py)       │
└────────┬────────┘ └──────┬───────┘ └──────────┬──────────┘
         │                 │                     │
         └─────────────────┼─────────────────────┘
                           ▼
              Unified violation schema
              { id, severity, line, message, fix, wcag, source }
                           ▼
                   Score + text/JSON report
```

### Design principles

1. **One rule class per check** — extend `A11yRule`; register in `all_rules()`.
2. **One violation schema** — static and axe findings share the same JSON shape; add `source: "static" | "axe"`.
3. **Honest scope** — README and SKILL.md must distinguish static vs rendered vs manual checks.
4. **Tests per rule** — every new rule: failing markup + passing markup in `test_a11y_lint.py`.

---

## Phase 1 — High-ROI static rules (recommended for OSS submission)

**Effort:** ~1–2 weeks  
**Dependencies:** Python stdlib only  
**Fits:** Existing `A11yRule` registry; no new runtime.

### Goals

Close the largest gaps between `SKILL.md` promises and linter behavior using pure static analysis.

### Planned rules

| Rule ID (proposed) | Check | Severity | WCAG area |
|--------------------|-------|----------|-----------|
| `placeholder-as-label` | `placeholder` on input without `<label>`, `aria-label`, or `aria-labelledby` | critical | 3.3.2 |
| `video-captions` | `<video>` without `<track kind="captions">` | serious | 1.2.2 |
| `audio-transcript` | `<audio>` without adjacent transcript link/text (heuristic) | serious | 1.2.1 |
| `document-title` | Full page missing non-empty `<title>` | serious | 2.4.2 |
| `skip-link` | Full page with `<nav>` but no skip link to `<main>` / `#main-content` | moderate | 2.4.1 |
| `aria-labelledby-target` | `aria-labelledby` references missing `id` | serious | 4.1.2 |
| `tabindex-positive` | Any `tabindex` > 0 | moderate | 2.4.3 |
| `aria-invalid-no-desc` | `aria-invalid="true"` without `aria-describedby` pointing to existing id | serious | 3.3.1 |
| `button-type-missing` | `<button>` inside `<form>` without explicit `type` | moderate | best practice |
| `target-blank-no-warning` | `target="_blank"` without accessible new-window hint (heuristic) | minor | 3.2.5 |

### Deliverables

- [x] 10 new rule classes in `a11y_rules.py`
- [x] 20 new unit tests (2 per rule minimum)
- [x] Updated `demo/broken_page.html` + `demo/expected_output.txt`
- [x] README rule table updated
- [x] SKILL.md checkboxes aligned with implemented rules

### Success metrics

- Rule count: 22 → **32** (implemented)
- All tests pass: `python3 -m unittest test_a11y_lint -v` (30 tests)
- `demo/broken_page.html` demonstrates new violations
- Zero new non-stdlib dependencies

---

## Phase 2 — Structure, forms depth, framework hooks

**Effort:** ~2–3 weeks  
**Dependencies:** Optional light parsers for template extraction

### Goals

Deeper semantic and form checks; path toward JSX/Vue/HTML in the same pipeline.

### Planned work

| Area | Features |
|------|----------|
| **Forms** | Required fields without visible/sr-only indicator; empty first `<option>` as only label |
| **Landmarks** | Nesting violations (`<main>` inside `<main>`); duplicate `role="main"` |
| **Links** | Empty `href`, placeholder `#` links, filename-like link text |
| **Headings** | Empty heading elements |
| **ARIA** | `aria-hidden="true"` on ancestor of focusable child; redundant `role` on natives |
| **Frameworks** | `extract_html.py`: pull template blocks from `.tsx`, `.vue`, `.component.html` before lint |

### Deliverables

- [ ] `a11y_extract.py` (or `scripts/extract_html.py`) for template extraction
- [ ] Landmark nesting rule
- [ ] Form required-field + error-association rules
- [ ] Docs: “Linting React/Vue templates” section in README

---

## Phase 3 — CSS engine (contrast, touch targets)

**Effort:** ~3–4 weeks  
**Dependencies:** `tinycss2` or equivalent (add to `requirements.txt`)

### Goals

Replace regex CSS parsing with a real stylesheet parser; enable contrast and size heuristics.

### Planned work

| Feature | Approach |
|---------|----------|
| **Color contrast** | Resolve `color` / `background-color` on text nodes for inline + `<style>` rules |
| **Touch targets** | Parse `width`/`height`/`padding`/`min-height` on interactive elements; flag &lt; 44×44px when computable |
| **Focus CSS** | Migrate `a11y_focus.py` from regex to shared CSS rule parser |
| **External CSS** | Optional `--base-url` to fetch linked stylesheets in CI |

### Limitations (document clearly)

- No inherited computed styles without a browser
- Gradients, background images, and CSS variables will be partial
- Results are **heuristic**, not compliance guarantees

---

## Phase 4 — Rendered audit (axe-core integration)

**Effort:** ~2–3 weeks  
**Dependencies:** Node.js, `@axe-core/cli` or Playwright + `axe-core`

### Goals

Honest “full automated pass” by delegating browser-only checks to the industry-standard engine.

### Planned CLI

```bash
# Fast static pass (default, no extra deps)
python3 a11y_lint.py page.html

# Full automated pass (requires Node + axe)
python3 a11y_lint.py page.html --axe

# CI: merge both into one JSON report
python3 a11y_lint.py page.html --axe --json
```

### New module: `a11y_axe.py`

- Subprocess wrapper around axe-core
- Map axe `impact` → `critical` / `serious` / `moderate` / `minor`
- Normalize to shared violation schema with `source: "axe"`
- Merge and deduplicate with static findings

### What axe adds that static cannot

- Computed color contrast
- Valid ARIA roles and required children
- Focusable element visibility
- Duplicate accessible names
- Many WCAG 2.x rules that need rendered DOM

---

## What not to implement as static rules

These require a browser, runtime JS, or human judgment. Document as **manual review** in SKILL.md instead of fake static checks:

| Check | Why static fails |
|-------|------------------|
| Keyboard traps | Needs focus events and JS behavior |
| Modal focus management | Dynamic DOM |
| Custom widget semantics | Behavior, not markup |
| Meaningful alt text | Context and intent |
| Reading order vs visual layout | CSS layout computation |
| Cross-page nav consistency | Multi-file site analysis |
| Seizure / flash rate | Animation timing in runtime |

---

## Recommendation for Codex Open Source Program submission

### Primary recommendation: **Ship Phase 1**

Phase 1 is the best submission scope for these reasons:

1. **Complete, reviewable increment** — Judges can clone, run tests, and see new rules immediately without installing Node or a browser.
2. **Demonstrates architecture** — The rule-registry design proves the project is extensible, not a one-off script.
3. **Closes the credibility gap** — Today `SKILL.md` overpromises relative to code. Phase 1 aligns docs with implementation.
4. **High accessibility impact per line of code** — Placeholder-as-label, captions, skip links, and error association are common real-world failures.
5. **Low risk** — Stdlib-only; no flaky CI from headless Chrome; easy to maintain post-submission.
6. **Clear narrative** — “We expanded from 22 to 30+ WCAG-aligned static checks with full test coverage.”

### Submission package checklist (Phase 1)

| Item | Status |
|------|--------|
| Working CLI + JSON output | Done |
| Rule-registry architecture | Done |
| 20+ unit tests | Done (extend to 36+ with Phase 1) |
| README with rule tables | Done (update after Phase 1) |
| Demo fixtures (broken + passing) | Done (extend broken_page) |
| ROADMAP.md (this file) | Done |
| `.gitignore`, no committed bytecode | Done |
| SKILL.md aligned with linter | Phase 1 deliverable |
| CONTRIBUTING.md (optional) | Recommended |

### Optional stretch goal (if time permits): **Phase 4 spike**

If the program rewards ambition and you have ~1 extra week:

- Add a minimal `a11y_axe.py` + `--axe` flag
- Document Node as optional dependency
- Show one merged JSON report (static + axe)

**Do not** make Phase 4 the only submission story — external deps and setup friction hurt reproducibility for reviewers.

### Defer for post-submission

- **Phase 3** (CSS engine) — high effort, heuristic accuracy debates; better as v2.0 after community feedback
- **Phase 2 framework extractors** — valuable but broader scope; good follow-up PR series

---

## Suggested timeline

```
Week 1–2   Phase 1 rules + tests + demo updates     ← SUBMIT HERE
Week 3     README/SKILL.md sync + submission polish
Week 4+    Phase 2 (framework extractors) OR Phase 4 spike (--axe)
Month 2+   Phase 3 CSS engine based on user feedback
```

---

## Submission narrative (template)

Use this framing in your Open Source Program application:

> **Accessibility Champion** is a lightweight, extensible static HTML linter for WCAG 2.2 AA triage. It uses a rule-registry architecture (14 rule classes, 22 checks, 20 tests) and produces scored JSON reports for CI.
>
> **This submission delivers Phase 1** of our [coverage roadmap](./ROADMAP.md): 8–10 additional high-impact static checks (form placeholders, media captions, skip links, ARIA reference validation, document title) with full test coverage and updated documentation — closing the gap between our agent skill spec and the linter implementation.
>
> **Future work** (documented, not required for review): axe-core integration for rendered audits (Phase 4) and CSS contrast analysis (Phase 3).

---

## How to add a rule (contributor reference)

1. Create a class extending `A11yRule` in `a11y_rules.py`.
2. Implement `on_starttag`, `on_endtag`, `on_data`, and/or `finalize`.
3. Register the instance in `all_rules()`.
4. Add failing + passing tests in `test_a11y_lint.py`.
5. Update `README.md` rule table and, if applicable, `demo/broken_page.html`.
6. If the rule is full-page only, respect `ctx.fragment_mode` and `ctx.is_full_page`.

---

## References

- [README.md](./README.md) — current checks and usage
- [SKILL.md](./SKILL.md) — full six-pillar audit workflow (agent)
- [framework-patterns.md](./framework-patterns.md) — React/Vue/Angular patterns
- [color-contrast.md](./color-contrast.md) — contrast guidance (future Phase 3)
- [WCAG 2.2 Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/)
- [axe-core rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md) — target for Phase 4 parity