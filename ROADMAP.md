# Accessibility Champion — Roadmap

How Accessibility Champion evolves from a **fast static HTML linter** (32 rules today) toward a **layered WCAG 2.2 AA audit platform** — linter + axe + agent skill — with honest scope at each layer.

---

## Executive summary

| Layer | Role | Coverage | Status |
|-------|------|----------|--------|
| **Static linter** | `a11y_lint.py` + rule registry | ~35–50% of common HTML issues | **32 rules, 30 tests** |
| **Code quality / architecture** | Maintainability before growth | Prevents regression to monolith | Planned (Phase 1.5) |
| **Structure & frameworks** | More static rules + template extractors | ~50–60% on real projects | Planned (Phase 2) |
| **CSS engine** | Contrast, touch targets, shared parser | ~60–70% on static pages | Planned (Phase 3) |
| **Rendered audit** | axe-core wrapper | ~80%+ automated | Planned (Phase 4) |
| **Agent skill** | Manual review, auto-fix, test generation | Intent + non-HTML frameworks | Ongoing (Phase 5) |

**“Full” ≠ one HTML pass.** Target pipeline:

```
HTML/JSX/Vue → [extract] → a11y_lint.py → [optional --axe] → agent review → report
```

---

## Current state (as of Phase 1 complete)

### Linter capabilities

- 32 rule IDs across 21 rule classes in `a11y_rules.py` (775 lines)
- Thin dispatcher in `a11y_lint.py` (145 lines)
- CSS focus-outline parser in `a11y_focus.py`
- Shared `ParseContext` in `a11y_context.py`
- CLI: `--json`, `--fragment`, `--full-page`
- Demo fixtures + 30 unit tests
- `SKILL.md` tagged with `[linter]` / `[agent]` / `[axe]` / `[manual]`

### Remaining gaps (linter vs SKILL.md)

| Area | Status |
|------|--------|
| Placeholder-as-label, skip links, captions, document title | **Done** (Phase 1) |
| Color contrast | Not implemented |
| Keyboard navigation / focus traps | Agent / axe only |
| ARIA role validity & required children | Agent / axe only |
| JSX / Vue / Angular direct linting | Not implemented |
| Touch target size | Not implemented |
| Landmark nesting, list semantics | Not implemented |
| Link `href` quality, empty headings | Not implemented |
| Required field visible indicator | Not implemented |
| Multi-file / site-wide consistency | Not implemented |

---

## Target architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  CLI / API (a11y_lint.py)                                        │
│  flags: --json --fragment --full-page --axe --sarif --severity   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      ▼                      ▼                      ▼
┌─────────────┐    ┌─────────────────┐    ┌──────────────────┐
│ a11y_extract│    │ HTMLParser      │    │ a11y_axe.py      │
│ .py         │    │ rule registry   │    │ (axe-core)       │
│ Phase 2     │    │ a11y_rules/*    │    │ Phase 4          │
└──────┬──────┘    │ a11y_focus.py   │    └────────┬─────────┘
       │           │ a11y_css.py     │             │
       └───────────┤ Phase 1.5/3     ├─────────────┘
                   └────────┬────────┘
                            ▼
              Unified Violation { id, severity, line, message,
                                  fix, wcag, source, file }
                            ▼
                   Score + text / JSON / SARIF
                            ▼
              SKILL.md agent layer (manual + auto-fix + tests)
```

### Design principles

1. **One rule class per check** — register in `all_rules()`.
2. **One violation schema** — static, axe, and future sources share the same JSON shape.
3. **Honest scope** — README / SKILL / ROADMAP stay synchronized.
4. **Tests per rule** — failing + passing markup minimum.
5. **Split before 1k lines** — `a11y_rules.py` must not grow unbounded.

---

## Phase 1 — High-ROI static rules ✅ COMPLETE

**Delivered:** 10 new rules (22 → 32), 30 tests, demo + docs updated.

| Rule ID | Check |
|---------|-------|
| `placeholder-as-label` | Placeholder without real label |
| `document-title` | Missing `<title>` |
| `video-captions` | `<video>` without captions track |
| `audio-transcript` | `<audio>` without nearby transcript (heuristic) |
| `skip-link` | `<nav>` without skip-to-main link |
| `aria-labelledby-target` | Broken `aria-labelledby` reference |
| `aria-invalid-no-desc` | `aria-invalid` without error association |
| `tabindex-positive` | `tabindex > 0` |
| `button-type-missing` | `<button>` in `<form>` without `type` |
| `target-blank-no-warning` | `target="_blank"` without new-window hint |

---

## Phase 1.5 — Architecture & code quality (do before Phase 2)

**Effort:** ~1 week  
**Why now:** `a11y_rules.py` is 775 lines; `ParseContext` has 25+ fields; `LinkNameRule` owns skip-link and target-blank logic. Adding Phase 2 rules without this refactor will recreate the pre-refactor monolith.

### Code-judo refactors (from code review)

| Item | Problem | Remedy |
|------|---------|--------|
| **Split `a11y_rules.py`** | Single 775-line module, 21 classes | `a11y_rules/forms.py`, `media.py`, `structure.py`, `aria.py`; `all_rules()` re-exports |
| **Nest `ParseContext`** | God-object state bag | `PageState`, `FormState`, `MediaState`, `LinkState` sub-dataclasses on `ParseContext` |
| **Isolate link policies** | `LinkNameRule` handles generic text + skip link + `target="_blank"` | `SkipLinkRule` sets flag on starttag; `TargetBlankRule` on endtag; `LinkNameRule` = generic text only |
| **Audio transcript offsets** | `AudioTranscriptRule` re-scans full source with regex per `<audio>` | Store byte `offset` in `MediaRule`; finalize reads 500-char window from offset |
| **Page-level line numbers** | `document-title`, `skip-link`, landmarks report `line: 1` | Record line of triggering element (`<html>`, first `<nav>`, etc.) |
| **`AriaReferenceRule` whitelist** | Only checks `div`/`span` + form controls | Validate `aria-*` reference attrs on **any** element with those attributes |
| **Violation typed model** | Ad-hoc `dict` with string keys | `Violation` dataclass or `TypedDict`; single factory in `a11y_context.py` |

### Deliverables

- [ ] Split `a11y_rules/` package (no file > 400 lines)
- [ ] Nested context state objects
- [ ] Link policy rules extracted from `LinkNameRule`
- [ ] Audio offset-based transcript check
- [ ] `Violation` typed schema used everywhere
- [ ] All 30+ tests still pass

---

## Phase 2 — Structure, forms, frameworks

**Effort:** ~2–3 weeks  
**Dependencies:** Phase 1.5 complete

### New linter rules (proposed)

| Rule ID | Check | Severity |
|---------|-------|----------|
| `required-indicator` | `required` / `aria-required` without visible or sr-only indicator | moderate |
| `select-empty-label` | `<select>` first `<option>` is empty and acts as sole label | serious |
| `landmark-nesting` | `<main>` inside `<main>`, or duplicate `role="main"` | serious |
| `empty-heading` | `<h1>`–`<h6>` with no text content | moderate |
| `empty-link` | `<a>` with no `href` or `href="#"` as only destination | moderate |
| `filename-link-text` | Link text matches filename pattern (`report.pdf`) | minor |
| `aria-hidden-focusable` | `aria-hidden="true"` ancestor contains focusable descendant | serious |
| `redundant-role` | `role="button"` on `<button>`, etc. | minor |
| `list-structure` | Nav block with 3+ consecutive `<a>` in bare `<div>`s (heuristic) | moderate |
| `decorative-img-role` | `alt=""` without `role="presentation"` (advisory) | minor |
| `lang-subtag` | Inline `lang` on non-default-language spans missing on i18n content | minor |

### Framework / multi-format support

| Feature | Description |
|---------|-------------|
| **`a11y_extract.py`** | Extract HTML from `.tsx` (jsx template), `.vue` (`<template>`), `.svelte`, Angular `.component.html` |
| **`a11y_lint.py --extract`** | Auto-detect format, lint extracted markup, map line numbers back to source |
| **Batch mode** | `a11y_lint.py 'src/**/*.html'` or `--glob` for CI directories |

### Deliverables

- [ ] `a11y_extract.py` with tests per framework
- [ ] 8–10 new rules from table above
- [ ] README: “Linting React/Vue templates”
- [ ] SKILL.md: Step 1.5 calls extractor for non-`.html` files

---

## Phase 3 — CSS engine (contrast, touch targets)

**Effort:** ~3–4 weeks  
**Dependencies:** `tinycss2` or `css-parser` in `requirements.txt`

### New module: `a11y_css.py`

| Feature | Rule ID (proposed) | Approach |
|---------|-------------------|----------|
| **Color contrast** | `color-contrast` | Resolve `color` / `background-color` pairs on text nodes |
| **Touch targets** | `touch-target-size` | `width`/`height`/`padding`/`min-height` on buttons/links; flag &lt; 44×44px |
| **Pointer events** | `pointer-events-none-interactive` | `pointer-events: none` on interactive elements |
| **Font size px** | `font-size-px-only` | Heuristic: all font sizes in `px` without `rem` fallback | 
| **Shared CSS parser** | — | Migrate `a11y_focus.py` to use `a11y_css.py` rule walker |
| **External stylesheets** | — | `--base-url` to fetch linked `.css` in CI |

### Limitations (document in README + SKILL)

- No inherited computed styles without a browser
- CSS variables, gradients, and background images are partial
- Results are **heuristic** — pair with axe for compliance claims

---

## Phase 4 — Rendered audit (axe-core integration)

**Effort:** ~2–3 weeks  
**Dependencies:** Node.js, `@axe-core/cli` or Playwright

### CLI

```bash
python3 a11y_lint.py page.html              # static only (default)
python3 a11y_lint.py page.html --axe        # static + rendered
python3 a11y_lint.py page.html --axe --json # merged JSON report
python3 a11y_lint.py page.html --axe-only   # skip static (debug)
```

### New module: `a11y_axe.py`

- Subprocess wrapper; map axe `impact` → severity
- Normalize to unified `Violation` schema with `source: "axe"`
- Deduplicate overlapping static + axe findings
- Optional: render HTML with `playwright` for SPAs before axe scan

### What axe adds

- Computed color contrast
- ARIA role validity and required children
- Focusable element visibility
- Duplicate accessible names
- ~57% of WCAG rules automatically

---

## Phase 5 — Skill & agent workflow enhancements

**Effort:** ongoing  
**Goal:** Make `SKILL.md` a first-class orchestration layer, not just a checklist.

### Agent workflow improvements

| Feature | Description | Priority |
|---------|-------------|----------|
| **Unified audit command** | Agent script: run linter → optional axe → format merged SKILL report | high |
| **AUTO_FIX v2** | Map each linter `id` to a deterministic fix template (AST-safe where possible) | high |
| **Severity config** | `.a11y.json` or `pyproject.toml` to disable rules / change severity per project | medium |
| **Baseline mode** | `--baseline violations.json` — only report new violations (CI regression) | medium |
| **Fix confidence tags** | Violations include `fix_confidence: auto \| assisted \| manual` in JSON | medium |
| **Component-scoped audit** | SKILL instructs agent to audit single component vs full page with correct fragment mode | medium |
| **Positive findings export** | Report which rules passed (not just violations) for stakeholder comms | low |
| **WCAG criterion index** | Group violations by WCAG SC number in output | low |

### GENERATE_TESTS enhancements

| Feature | Description |
|---------|-------------|
| **Linter test codegen** | Generate `unittest` snippets from `demo/broken_page.html` violations |
| **Playwright + linter CI** | Template GitHub Action: lint → axe → fail on critical |
| **Regression fixtures** | User-submitted HTML snippets become permanent test cases |

### Documentation

| Item | Status |
|------|--------|
| `CONTRIBUTING.md` | Not started — rule addition guide, test requirements |
| `references/rule-catalog.md` | Not started — one page per rule ID with examples |
| SKILL ↔ README auto-sync check | Not started — CI script verifying rule IDs match |

---

## Phase 6 — CI, packaging & distribution

**Effort:** ~1–2 weeks  
**Goal:** Drop into any pipeline without friction.

| Feature | Description |
|---------|-------------|
| **`pip install accessibility-champion`** | `pyproject.toml`, entry point `a11y-lint` |
| **SARIF output** | `--sarif` for GitHub Code Scanning / GitLab SAST |
| **GitHub Action** | `uses: org/accessibility-champion@v1` with `files:` input |
| **pre-commit hook** | `.pre-commit-hooks.yaml` lint staged `.html` files |
| **GitLab / Jenkins examples** | Docs in README |
| **Docker image** | Optional image with Python + Node for `--axe` |
| **VS Code problem matcher** | Parse linter output into IDE diagnostics |

---

## Phase 7 — Advanced / research (defer until Phases 1–5 stable)

| Feature | Notes |
|---------|-------|
| **Multi-file site audit** | Cross-page nav consistency, shared header/footer templates |
| **SCSS/LESS extraction** | Compile to CSS before contrast analysis |
| **SVG a11y linter** | `<title>`, `aria-labelledby` inside inline SVG |
| **PDF/HTML export audit** | Accessibility of generated reports |
| **ML-assisted alt text review** | Flag likely-bad alts beyond keyword list (optional, privacy-sensitive) |
| **Live URL fetch** | `a11y_lint.py https://example.com` with SSRF guards |
| **Rule contribution registry** | Plugin system: third-party `A11yRule` subclasses via entry points |

---

## What NOT to implement as static rules

Document in SKILL.md as `[manual]` or `[axe]` — do not fake with regex:

| Check | Why |
|-------|-----|
| Keyboard traps | Needs focus events + JS |
| Modal focus management | Dynamic DOM |
| Custom widget behavior | Intent, not markup |
| Meaningful alt text in context | Human judgment |
| Reading order vs visual layout | Computed layout |
| Cross-page nav consistency | Multi-file analysis |
| Seizure / flash rate | Runtime animation |
| Screen reader announcement order | Live AT testing |

---

## Priority matrix (what to do next)

```
Now        Phase 1.5  Architecture refactor (split rules, nested context)
Next       Phase 2    Framework extractors + 8–10 structure/form rules
Then       Phase 4    axe-core `--axe` (higher impact than Phase 3 for "full" claims)
Parallel   Phase 5    AUTO_FIX v2 + unified agent audit script
Later      Phase 3    CSS contrast engine
Later      Phase 6    pip package + SARIF + GitHub Action
Research   Phase 7    Multi-file, plugins, URL fetch
```

### Recommended for next sprint

1. **Phase 1.5** — split `a11y_rules.py`, fix link-rule leakage, audio offsets (prevents debt)
2. **Phase 2 extractors** — unlocks SKILL value for React/Vue users
3. **Phase 4 spike** — `--axe` flag with merged JSON (biggest coverage jump)
4. **CONTRIBUTING.md** — lowers contributor barrier

---

## Success metrics by phase

| Phase | Rule count | Tests | Key metric |
|-------|------------|-------|------------|
| 1 ✅ | 32 | 30 | SKILL/linter alignment |
| 1.5 | 32 | 30 | No module > 400 lines; nested context |
| 2 | 40+ | 50+ | Lint extracted `.tsx` / `.vue` templates |
| 3 | 45+ | 55+ | Contrast heuristic on demo pages |
| 4 | 45+ + axe | 60+ | Single `--axe --json` merged report |
| 5 | — | — | Agent AUTO_FIX covers all `auto` confidence rules |
| 6 | — | — | Published on PyPI; SARIF in GitHub Action |

---

## How to add a rule (contributor reference)

1. Complete Phase 1.5 split — add rule to appropriate `a11y_rules/*.py` module.
2. Create class extending `A11yRule`.
3. Implement `on_starttag`, `on_endtag`, `on_data`, and/or `finalize`.
4. Register in `all_rules()`.
5. Add failing + passing tests in `test_a11y_lint.py`.
6. Update `README.md`, `SKILL.md` (`[linter]` tag), and `demo/broken_page.html` if applicable.
7. Respect `ctx.fragment_mode` and `ctx.is_full_page` for page-level checks.

---

## References

- [README.md](./README.md) — linter usage and rule tables
- [SKILL.md](./SKILL.md) — agent workflow (`[linter]` / `[agent]` / `[axe]` / `[manual]`)
- [framework-patterns.md](./framework-patterns.md) — React/Vue/Angular patterns
- [color-contrast.md](./color-contrast.md) — contrast algorithms (Phase 3)
- [WCAG 2.2 Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/)
- [axe-core rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)