---
name: accessibility-champion
description: >
  WCAG 2.2 AA accessibility audits combining the static HTML linter (a11y_lint.py),
  agent-guided manual review, and optional axe-core tests. Use for HTML files directly;
  use agent review for JSX/TSX, Vue, Angular, and Svelte. Trigger on mentions of
  accessibility, a11y, ARIA, WCAG, screen readers, keyboard navigation, color contrast,
  ADA compliance, tab order, or focus management. Produces a severity-ranked report
  with copy-paste fixes and a numeric score (0–100).
---

# Accessibility Champion

Audit, score, and fix WCAG 2.2 accessibility issues.

This project has **two layers**:

| Layer | Tool | Scope |
|-------|------|-------|
| **Static linter** | `a11y_lint.py` | `.html` files + framework templates via `--extract` — 43 automated rule IDs, fast CI triage |
| **Agent + axe** | This skill | JSX/Vue/Angular/Svelte contrast, keyboard, ARIA behavior, intent (beyond the linter's static reach) |

For plain HTML, **always run the linter first**, then apply manual pillar checks for anything the linter cannot detect. See [README.md](./README.md) for the full rule reference.

---

## Check coverage legend

When reviewing, each item is tagged by who performs it:

| Tag | Who checks it |
|-----|----------------|
| **`[linter]`** | `python3 a11y_lint.py` — automated, line numbers, JSON output |
| **`[agent]`** | You (the agent) — manual code review |
| **`[axe]`** | axe-core / Playwright — rendered DOM (GENERATE_TESTS workflow) |
| **`[manual]`** | Human judgment required — intent, meaning, design decisions |

---

## Static linter (run first for HTML)

```bash
# Human-readable report
python3 a11y_lint.py path/to/file.html

# JSON for merging into your audit report
python3 a11y_lint.py path/to/file.html --json

# HTML fragment (skips full-page landmark / single-H1 checks)
python3 a11y_lint.py path/to/fragment.html --fragment

# Framework template — extract HTML, lint, remap lines to the source file
python3 a11y_lint.py path/to/LoginForm.tsx --extract --json
```

Extraction is automatic for `.tsx`, `.jsx`, `.vue`, `.svelte`, and `.component.html`. Violation
`line` values refer to the **source file** after remapping; a `*.extract-map.json` sidecar records
the mapping (`--no-sidecar` to skip). Use `--fragment` for partial component templates.

Programmatic use:

```python
from a11y_lint import check_html, score
violations = check_html(source)
total = score(violations)
```

**43 linter rule IDs** (by pillar — details in README):

- **Perceivable:** `html-has-lang`, `image-alt`, `image-alt-quality`, `no-autoplay`, `video-captions`, `audio-transcript`, `document-title`, `decorative-img-role`
- **Operable:** `button-name`, `link-name`, `focus-visible`, `skip-link`, `tabindex-positive`, `button-type-missing`, `target-blank-no-warning`, `empty-link`, `filename-link-text`
- **Understandable:** `input-unlabelled`, `input-missing-label`, `placeholder-as-label`, `input-autocomplete`, `aria-invalid-no-desc`, `required-indicator`, `select-empty-label`, `lang-subtag`
- **Robust & structure:** `duplicate-id`, `form-group-fieldset`, `aria-describedby-missing-target`, `aria-labelledby-target`, `heading-order`, `heading-single-h1`, `frame-title`, `table-th`, `table-caption`, `missing-main`, `missing-header-landmark`, `missing-nav-landmark`, `missing-footer-landmark`, `landmark-nesting`, `empty-heading`, `list-structure`, `aria-hidden-focusable`, `redundant-role`

Merge linter JSON violations into your audit report. Do not re-derive checks the linter already covers.

---

## Quick decision tree

```
User shares code / page URL?
  ├── .html file → run a11y_lint.py FIRST, then FULL_AUDIT manual items
  ├── .tsx/.jsx/.vue/.svelte/.component.html → run a11y_lint.py --extract FIRST, then FULL_AUDIT manual items
  └── No code → ask: "Share a component, URL, or describe what you're building?"

User wants fixes applied?
  ├── Yes → run AUTO_FIX workflow
  └── No → report only (default)

User wants tests?
  └── Yes → run GENERATE_TESTS workflow (axe-core)
```

---

## FULL_AUDIT workflow

### Step 1 — Detect framework

| Extension | Mode | Linter? |
|-----------|------|---------|
| `.html` | Plain HTML | **Yes** — run `a11y_lint.py` |
| `.jsx` / `.tsx` | React/Next.js (`className`, `htmlFor`) | **Yes** — `a11y_lint.py --extract`, then agent review |
| `.vue` | Vue SFC (template block) | **Yes** — `a11y_lint.py --extract`, then agent review |
| `.component.html` | Angular | **Yes** — `a11y_lint.py --extract`, then agent review |
| `.svelte` | Svelte | **Yes** — `a11y_lint.py --extract`, then agent review |
| `.md` / raw markup | Plain HTML | Yes if valid HTML |

### Step 1.5 — Run static linter (HTML or framework templates)

1. Execute `python3 a11y_lint.py <file> --json` (add `--extract` for `.tsx`/`.jsx`/`.vue`/`.svelte`/`.component.html`).
2. Include all linter violations in the final report with their `id`, `line`, `message`, and `fix`.
3. Use the linter score as the baseline (same formula as Step 3).
4. Proceed to Step 2 **only for items tagged `[agent]`, `[axe]`, or `[manual]`** — do not duplicate linter findings.

### Step 2 — Run checks across 6 WCAG pillars

For each pillar, collect violations with file location. Skip `[linter]` items if Step 1.5 already ran.

#### Pillar 1 — Perceivable

- [linter] **Images** — `image-alt`, `image-alt-quality`. Decorative `alt=""` + `role="presentation"` is best practice; linter does not require `role="presentation"`.
- [linter] **Video captions** — `video-captions` requires `<track kind="captions">` on `<video>`.
- [linter] **Audio transcript** — `audio-transcript` heuristic flags `<audio>` without nearby transcript text/link.
- [linter] **Document title** — `document-title` requires non-empty `<title>` in `<head>` on full pages.
- [linter] **Autoplay** — `no-autoplay` flags `<video>` / `<audio>` with `autoplay`.
- [manual] **Alt text quality** — Is alt text meaningful in context? (linter only flags generic words.)
- [agent] **Color contrast** — Text 4.5:1 (normal) or 3:1 (large). UI components 3:1. See `references/color-contrast.md`.
- [agent] **Non-color cues** — Errors, required fields, links must not rely on color alone.
- [agent] **Text resize** — Avoid `px`-only font sizes that block 200% zoom; prefer `rem`/`em`.

#### Pillar 2 — Operable

- [linter] **Focus visible** — `focus-visible` scans `<style>` and inline CSS for `outline: none/0` without `:focus` / `:focus-visible` fallback.
- [linter] **Skip links** — `skip-link` requires skip-to-main link when `<nav>` is present on full pages.
- [linter] **Tab order** — `tabindex-positive` bans `tabindex > 0`.
- [linter] **Button type** — `button-type-missing` requires explicit `type` on `<button>` inside `<form>`.
- [linter] **New window links** — `target-blank-no-warning` flags `target="_blank"` without accessible warning text.
- [linter] **Button / link names** — `button-name`, `link-name`.
- [agent] **Keyboard access** — All interactive elements reachable by Tab; operable by Enter/Space.
- [agent] **Keyboard traps** — Modals trap focus and release on Esc; menus don't trap indefinitely.
- [agent] **Seizure content** — No flashing faster than 3 Hz.
- [axe] **Touch targets** — Interactive elements ≥ 44×44px (WCAG 2.5.5).

#### Pillar 3 — Understandable

- [linter] **Language** — `html-has-lang`.
- [linter] **Labels** — `input-unlabelled`, `input-missing-label` on `<input>`, `<select>`, `<textarea>`.
- [linter] **Placeholder** — `placeholder-as-label` flags placeholder-only labeling.
- [linter] **Autocomplete** — `input-autocomplete` on personal-data fields.
- [linter] **Error association (partial)** — `aria-invalid-no-desc` requires `aria-describedby` when `aria-invalid="true"`.
- [agent] **Error identification** — Error messages name the field and describe the issue; not just "Invalid".
- [manual] **Consistent navigation** — Repeated nav patterns in same order site-wide (multi-page).

#### Pillar 4 — Robust

- [linter] **ARIA references** — `aria-describedby-missing-target`, `aria-labelledby-target` validate target ids exist.
- [linter] **Duplicate IDs** — `duplicate-id`.
- [agent] **Valid ARIA** — Role combinations, prohibited attributes, spec compliance.
- [agent] **Required ARIA children** — e.g. `role="list"` → `role="listitem"` children.
- [agent] **Name/Role/Value** — Custom widgets expose correct name, role, state to AT.
- [agent] **Live regions** — Dynamic updates use `aria-live`; toasts use `role="status"` or `role="alert"`.

#### Pillar 5 — Forms

- [linter] **Group labels** — `form-group-fieldset` for radio/checkbox groups (`<fieldset>` + `<legend>`).
- [linter] **Error association (partial)** — see `aria-invalid-no-desc` above.
- [agent] **Required fields** — `required` / `aria-required` plus visible indicator.
- [agent] **Disabled vs read-only** — Prefer `readonly` + `aria-disabled` over `disabled` when users must read values.

#### Pillar 6 — Headings & Structure

- [linter] **Single H1** — `heading-single-h1` on full pages.
- [linter] **Heading hierarchy** — `heading-order` (no skipped levels).
- [linter] **Landmarks** — `missing-main`, `missing-header-landmark`, `missing-nav-landmark`, `missing-footer-landmark` on full pages (presence only).
- [linter] **Tables** — `table-th`, `table-caption` (skips `role="presentation"` tables).
- [linter] **Iframes** — `frame-title`.
- [agent] **Landmark nesting** — No nested `<main>`; correct landmark hierarchy.
- [agent] **Lists** — Nav groups use `<ul>/<li>` or `<ol>/<li>`, not div soup.

### Step 3 — Score and report

Use the linter score when Step 1.5 ran. For non-HTML audits, calculate manually:

```
score = 100 − (critical × 20 + serious × 10 + moderate × 5 + minor × 2)
        clamped to [0, 100]
```

Severity definitions:
- **Critical** — blocks access for a disability group (missing alt, no labels, empty button name)
- **Serious** — significantly degrades experience (missing lang, no captions, generic links, missing iframe title)
- **Moderate** — friction with workarounds (skip link, heading gaps, missing landmarks, positive tabindex)
- **Minor** — best-practice (autocomplete, optional landmarks, new-window warnings)

### ⚠️ Automation limits & score disclaimer

The static linter catches roughly **30–50%** of common HTML issues. axe-core adds rendered-DOM checks (~57% of WCAG rules). **Neither replaces manual review.**

Apply human judgment for:
- **Interaction intent** — Does the custom widget behave correctly?
- **Meaningful alt text** — Descriptive in context, not just non-generic?
- **Reading order** — DOM order vs visual layout (flex/grid)?
- **Keyboard behavior** — Focus management in complex ARIA widgets?

A score of 95/100 does not guarantee compliance — the remaining 5% could be a critical keyboard trap.

### Step 4 — Output format

```
## Accessibility Audit — [Component/Page Name]
**Score: XX/100**  |  WCAG 2.2 AA  |  [Framework]
**Linter:** [ran a11y_lint.py / not applicable]

### 🔴 Critical (N issues)
1. **[rule-id or issue title]** — line X
   > Why it matters: [impact on disability group]
   > Fix: [code snippet]

### 🟠 Serious (N issues)
...

### 🟡 Moderate (N issues)
...

### 🔵 Minor (N issues)
...

### ✅ Passing checks
[Include linter passes and manual positives]

---
*Run AUTO_FIX to apply safe fixes.*
*Run GENERATE_TESTS for axe-core / Playwright suite.*
```

Always lead with score and a one-line summary.

---

## AUTO_FIX workflow

When the user says "fix it", "apply fixes", or "auto-fix":

1. Re-read the original code. If HTML, re-run `a11y_lint.py` to confirm current violations.
2. Apply only unambiguous, safe fixes:
   - `alt=""` on decorative images
   - `aria-label` on icon-only buttons
   - `<label>` / `htmlFor` on inputs
   - `lang="en"` on `<html>`
   - `<title>` in `<head>`
   - `type="button"` on non-submit buttons in forms
   - `<track kind="captions">` on video
   - `outline` / `:focus-visible` CSS fixes
   - Skip link: `<a href="#main-content">Skip to main content</a>`
3. Mark issues needing human decision with `// TODO [a11y]:`:
   - Informative image alt text (unknown content)
   - Color contrast (design palette)
   - Heading restructure (SEO/layout impact)
4. Output the full patched file (not a diff).
5. List what was auto-fixed vs what needs human attention.

---

## GENERATE_TESTS workflow

When the user asks for "tests", "test suite", or "a11y tests":

Use **axe-core** for rendered-DOM checks the linter cannot perform (contrast, ARIA validity, visibility).

### React / JSX — `@axe-core/react` + vitest

```typescript
import { render } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { ComponentName } from './ComponentName'

expect.extend(toHaveNoViolations)

describe('ComponentName accessibility', () => {
  it('has no axe violations', async () => {
    const { container } = render(<ComponentName />)
    expect(await axe(container)).toHaveNoViolations()
  })
})
```

### Playwright — end-to-end axe scan

```typescript
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('passes axe scan on load', async ({ page }) => {
  await page.goto('/your-route')
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  expect(results.violations).toEqual([])
})
```

Always include:
1. axe full-page scan
2. Keyboard navigation test (skip link, tab order)
3. Tests targeting critical/serious issues from the audit

For HTML projects, also keep `python3 -m unittest test_a11y_lint test_a11y_extract test_phase2 -v` passing when changing linter rules.

---

## Framework-specific quick-reference

Read `references/framework-patterns.md` for React, Vue, Angular, and Svelte patterns (dialogs, dropdowns, tabs, tooltips).

Read `references/color-contrast.md` for contrast algorithms and common Tailwind pass/fail pairs.

Read `ROADMAP.md` for planned linter expansion (CSS contrast, axe integration, framework extractors).

---

## Tone and communication

- Be specific: `[image-alt] line 23` not "images need labels"
- Lead with impact: name the disability group affected
- Be encouraging: list what's already good
- Be practical: provide ready-to-paste fixes
- For design-system teams: group findings by component type
- Clearly label finding source: **linter**, **agent review**, or **axe**