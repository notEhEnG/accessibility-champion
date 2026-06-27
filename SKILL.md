---
name: accessibility-champion
description: >
  Comprehensive WCAG 2.2 accessibility audit, scoring, and auto-fix skill for HTML,
  JSX, Vue, Angular, and plain HTML templates. Use this skill whenever the user mentions
  accessibility, a11y, ARIA, WCAG, screen readers, keyboard navigation, color contrast,
  ADA compliance, tab order, focus management, or wants to make their UI more inclusive.
  Also trigger when the user asks to "review my component", "audit my page", "check my
  forms", or shares front-end code and wants quality feedback — accessibility is part of
  quality. Produces a severity-ranked report with copy-paste fixes and a numeric
  accessibility score. Can also generate a full accessibility test suite.
---

# Accessibility Champion

Audit, score, and fix WCAG 2.2 accessibility issues across any front-end codebase.
Works with HTML, JSX/TSX, Vue SFCs, Angular templates, Svelte, and plain Markdown.

---

## Quick decision tree

```
User shares code / page URL?
  ├── Yes → run FULL_AUDIT workflow below
  └── No → ask: "Share a component, URL, or describe what you're building?"

User wants fixes applied?
  ├── Yes → run AUTO_FIX workflow
  └── No → report only (default)

User wants tests?
  └── Yes → run GENERATE_TESTS workflow
```

---

## FULL_AUDIT workflow

### Step 1 — Detect framework

Identify from file extension and syntax:
- `.jsx` / `.tsx` → React/Next.js mode (JSX attribute names: `className`, `htmlFor`, `aria-*`)
- `.vue` → Vue SFC mode (template block)
- `.component.html` + `.ts` → Angular mode
- `.svelte` → Svelte mode
- `.html` / `.md` / raw markup → plain HTML mode

### Step 2 — Run checks across 6 WCAG pillars

For each pillar, collect all violations with file location (line number if possible):

#### Pillar 1 — Perceivable
- [ ] **Images**: Every `<img>` has non-empty `alt`. Decorative images have `alt=""` + `role="presentation"`. Automated check flags generic alt text like "image" or "photo" for manual review.
- [ ] **Video/audio**: `<video>` has `<track kind="captions">`, `<audio>` has transcript link nearby.
- [ ] **Color contrast**: Text on background must meet 4.5:1 (normal) or 3:1 (large ≥18pt/14pt bold). UI components 3:1 minimum.
- [ ] **Non-color cues**: Errors, required fields, links — never convey meaning by color alone. Must have icon, underline, or text label too.
- [ ] **Text resize**: No fixed `px` font sizes that prevent browser zoom to 200%. Prefer `rem`/`em`.

#### Pillar 2 — Operable
- [ ] **Keyboard access**: All interactive elements (`<a>`, `<button>`, custom widgets) reachable by `Tab` and operable by `Enter`/`Space`.
- [ ] **Focus visible**: No `outline: none` / `outline: 0` without a custom `:focus-visible` replacement.
- [ ] **No keyboard traps**: Modal dialogs must trap focus *within* and release on `Esc`. Menus must not trap indefinitely.
- [ ] **Skip links**: Pages with navigation must have a "Skip to main content" link as first focusable element.
- [ ] **No seizure content**: No content flashing faster than 3 Hz.
- [ ] **Touch targets**: Interactive elements ≥ 44×44px (WCAG 2.5.5 AA).

#### Pillar 3 — Understandable
- [ ] **Language**: `<html lang="xx">` is set and correct.
- [ ] **Labels**: All `<input>`, `<select>`, `<textarea>` have an associated `<label>` (via `for`/`id` or wrapping). Placeholder alone is not a label.
- [ ] **Error identification**: Errors name the field and describe the issue. Not just "Invalid".
- [ ] **Consistent navigation**: Repeated nav patterns appear in the same order site-wide.
- [ ] **Autocomplete**: `<input>` collecting personal data sets `autocomplete` attribute (name, email, tel, etc.).

#### Pillar 4 — Robust
- [ ] **Valid ARIA**: `role`, `aria-label`, `aria-labelledby`, `aria-describedby` follow the ARIA spec. No invalid role combinations.
- [ ] **Required ARIA children**: `role="list"` has `role="listitem"` children; `role="tablist"` has `role="tab"` children, etc.
- [ ] **Name/Role/Value**: All custom interactive widgets expose name, role, and value/state to assistive technology.
- [ ] **Live regions**: Dynamic content updates use `aria-live="polite"` (or `assertive` for urgent alerts). Toast/notification components check here.
- [ ] **Status messages**: Success/error messages programmatically determinable (use `role="status"` or `role="alert"`).

#### Pillar 5 — Forms (high-impact, own pillar for clarity)
- [ ] **Required fields**: Marked with `aria-required="true"` or `required` attribute *and* a visible indicator.
- [ ] **Error association**: Error messages linked via `aria-describedby` to the input in error.
- [ ] **Group labels**: Related controls (`<fieldset>` + `<legend>`) for radio/checkbox groups.
- [ ] **Disabled vs read-only**: Don't use `disabled` on fields users need to understand. Use `readonly` + `aria-disabled="true"` for contextual unavailability.

#### Pillar 6 — Headings & Structure
- [ ] **Single H1**: One `<h1>` per page/view.
- [ ] **Heading hierarchy**: No skipped levels (H1 → H3 without H2). Headings convey structure, not style.
- [ ] **Landmark regions**: Page has `<main>`, `<nav>`, `<header>`, `<footer>` (or ARIA equivalents). The linter checks for the presence of a `<main>` landmark. No landmark nesting violations.
- [ ] **Lists**: Navigation links, icon rows, tag groups use `<ul>/<li>` or `<ol>/<li>`. Don't use `<div>` soup for lists.
- [ ] **Tables**: Data tables have `<th scope="col/row">` and `<caption>`. Never use tables for layout.

### Step 3 — Score and report

Calculate a numeric **A11y Score** (0–100):

```
score = 100 − (critical × 20 + serious × 10 + moderate × 5 + minor × 2)
        clamped to [0, 100]
```

Severity definitions:
- **Critical** — completely blocks access for a disability group (missing alt on informational image, broken keyboard trap, no form labels)
- **Serious** — significantly degrades experience (poor contrast, no focus visible, no error association)
- **Moderate** — creates friction but has workarounds (missing skip link, inconsistent heading, no landmark regions)
- **Minor** — best-practice or AAA recommendation (autocomplete attributes, touch target just under 44px)

### ⚠️ Automation Limits & Score Disclaimer
While this skill and its static linting can catch common HTML issues (catching about 30-50% of WCAG issues), **automated tooling cannot fully replace manual review**. 
You must apply human judgment for:
- **Interaction intent**: Does the custom widget actually behave like the native equivalent?
- **Meaningful alt text**: Is the alt text actually descriptive, or just `alt="image"`?
- **Reading order**: Does the DOM order make sense when styled visually via CSS Flex/Grid?
- **Nuanced keyboard behavior**: Do complex ARIA widgets manage focus properly (e.g., roving tabindex)?

*Note on the Accessibility Score (0-100):* This score is useful for quick triage and measuring relative improvement, but it **does not guarantee compliance**. It can oversimplify serious accessibility risk. A score of 95/100 still means the site could be completely unusable for a screen reader user if the remaining 5% is a critical keyboard trap.

### Step 4 — Output format

Present findings in this order:

```
## Accessibility Audit — [Component/Page Name]
**Score: XX/100**  |  WCAG 2.2 AA  |  [Framework]

### 🔴 Critical (N issues)
1. **[Issue title]** — `line X` or selector
   > Why it matters: [one sentence, real-world impact on a specific disability group]
   > Fix: [code snippet, ready to paste]

### 🟠 Serious (N issues)
...

### 🟡 Moderate (N issues)
...

### 🔵 Minor / Best Practice (N issues)
...

### ✅ Passing checks
[Brief list of what's already good — always include positives]

---
*Run `/accessibility-champion fix` to apply all auto-fixable issues.*
*Run `/accessibility-champion tests` to generate a Playwright/Vitest a11y test suite.*
```

Always lead with the score and a one-line summary ("This component has 3 critical issues that block screen reader users entirely.").

---

## AUTO_FIX workflow

When the user says "fix it", "apply fixes", or "auto-fix":

1. Re-read the original code.
2. Apply only changes that are unambiguous and safe:
   - Adding `alt=""` on decorative images ✓
   - Adding `aria-label` to icon-only buttons ✓
   - Wrapping inputs in `<label>` or adding `htmlFor` ✓
   - Adding `lang="en"` to `<html>` ✓
   - Adding `aria-required="true"` ✓
   - Replacing `outline: none` with `outline: 2px solid currentColor` ✓
3. Mark issues that need human decision with a `// TODO [a11y]:` comment:
   - Alt text for informational images (you don't know what the image conveys)
   - Color contrast (need design decision on palette)
   - Heading hierarchy changes (may affect SEO/layout)
4. Output the full patched file (not a diff) so the user can copy-paste directly.
5. After the file, list what was auto-fixed and what requires human attention.

---

## GENERATE_TESTS workflow

When the user asks for "tests", "test suite", or "a11y tests":

Generate tests using **axe-core** (the industry standard) for the detected framework:

### React / JSX — use `@axe-core/react` + `vitest`
```typescript
// [ComponentName].a11y.test.tsx
import { render } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { ComponentName } from './ComponentName'

expect.extend(toHaveNoViolations)

describe('ComponentName accessibility', () => {
  it('has no axe violations', async () => {
    const { container } = render(<ComponentName />)
    expect(await axe(container)).toHaveNoViolations()
  })

  it('all interactive elements are keyboard reachable', async () => {
    const { getAllByRole } = render(<ComponentName />)
    // Check buttons, links, inputs are in the tab order
    const interactives = getAllByRole(/button|link|textbox|combobox|checkbox|radio/)
    interactives.forEach(el => {
      expect(el).not.toHaveAttribute('tabindex', '-1')
    })
  })

  it('form inputs have associated labels', async () => {
    const { getAllByRole } = render(<ComponentName />)
    getAllByRole('textbox').forEach(input => {
      expect(input).toHaveAccessibleName()
    })
  })
})
```

### Playwright — end-to-end a11y scan
```typescript
// [page].a11y.spec.ts
import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('[PageName] accessibility', () => {
  test('passes axe scan on load', async ({ page }) => {
    await page.goto('/your-route')
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze()
    expect(results.violations).toEqual([])
  })

  test('keyboard: skip link reaches main content', async ({ page }) => {
    await page.goto('/your-route')
    await page.keyboard.press('Tab')
    const focused = await page.locator(':focus').textContent()
    expect(focused).toMatch(/skip/i)
  })

  test('keyboard: focus never gets trapped outside modal', async ({ page }) => {
    await page.goto('/your-route')
    // Open modal, press Escape, check focus returns to trigger
    // Adapt to your trigger selector
  })
})
```

Always include:
1. axe full-page scan (catches ~57% of WCAG issues automatically)
2. Keyboard navigation test
3. Specific tests for the exact critical/serious issues found in the audit

---

## Framework-specific quick-reference

Read `references/framework-patterns.md` when the user's code uses a specific
framework — it contains copy-paste patterns for React, Vue, Angular, and Svelte
for common a11y patterns (dialogs, dropdowns, tabs, tooltips, date pickers, etc).

Read `references/color-contrast.md` when checking or computing contrast ratios.
It includes the APCA and WCAG contrast algorithms and a table of common Tailwind
color pairs that fail/pass.

---

## Tone and communication

- Be specific: "Line 23: `<button>` has no accessible name" not "buttons need labels"
- Lead with impact: name the disability group affected ("Screen reader users hear nothing when this icon button is activated")
- Be encouraging: always list what's already good before fixes
- Be practical: always provide a ready-to-paste fix, never just a description of the problem
- For design-system teams: group findings by component type so they can fix at the source
