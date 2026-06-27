# Color Contrast Reference

## WCAG 2.2 Contrast Thresholds

| Text size | AA (minimum) | AAA (enhanced) |
|---|---|---|
| Normal text (< 18pt / 14pt bold) | **4.5:1** | 7:1 |
| Large text (≥ 18pt or ≥ 14pt bold) | **3:1** | 4.5:1 |
| UI components & graphical objects | **3:1** | n/a |
| Disabled UI / decorative | n/a (exempt) | n/a |

18pt = 24px. 14pt bold = ~18.67px bold.

---

## Computing contrast ratio

```
Relative luminance L = 0.2126·R + 0.7152·G + 0.0722·B
  where each channel: c ≤ 0.04045 ? c/12.92 : ((c + 0.055)/1.055)^2.4
  and channel c = hex_value / 255

Contrast ratio = (L_lighter + 0.05) / (L_darker + 0.05)
```

JavaScript helper:
```javascript
function hexToLuminance(hex) {
  const [r, g, b] = hex.replace('#','').match(/.{2}/g)
    .map(h => parseInt(h, 16) / 255)
    .map(c => c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contrastRatio(hex1, hex2) {
  const [l1, l2] = [hexToLuminance(hex1), hexToLuminance(hex2)].sort((a,b) => b-a)
  return ((l1 + 0.05) / (l2 + 0.05)).toFixed(2)
}

// Usage
contrastRatio('#1a1a1a', '#ffffff') // → "17.35" ✓ passes all levels
contrastRatio('#9ca3af', '#ffffff') // → "2.85"  ✗ fails AA (Tailwind gray-400 on white)
```

---

## Common failures in popular design systems

### Tailwind CSS — pairs that FAIL WCAG AA

| Foreground | Background | Ratio | Issue |
|---|---|---|---|
| `gray-400` (#9ca3af) | `white` | 2.85 | Placeholder text, muted labels |
| `gray-500` (#6b7280) | `white` | 4.48 | Just under 4.5 threshold |
| `blue-400` (#60a5fa) | `white` | 3.13 | Often used for links |
| `green-400` (#4ade80) | `white` | 4.32 | Success badges on white |
| `red-400` (#f87171) | `white` | 3.53 | Error text on light bg |
| `yellow-400` (#facc15) | `white` | 1.63 | Warning states |
| `gray-300` (#d1d5db) | `white` | 1.28 | Disabled elements (but AA-exempt) |

### Tailwind CSS — pairs that PASS WCAG AA

| Foreground | Background | Ratio | Notes |
|---|---|---|---|
| `gray-900` (#111827) | `white` | 19.56 | Body text, always safe |
| `gray-700` (#374151) | `white` | 10.73 | Safe for all text |
| `gray-600` (#4b5563) | `white` | 7.45 | Safe normal text |
| `blue-700` (#1d4ed8) | `white` | 8.59 | Accessible link blue |
| `blue-600` (#2563eb) | `white` | 5.92 | Accessible |
| `green-700` (#15803d) | `white` | 7.18 | Accessible success |
| `red-700` (#b91c1c) | `white` | 9.18 | Accessible error |
| `gray-900` (#111827) | `yellow-200` (#fef08a) | 13.65 | Accessible warning |

---

## Dark mode contrast pitfalls

Common mistakes when implementing dark mode:

1. **Inverting a light palette doesn't work** — `gray-900` text on `white` passes; its inverse `gray-100` text on `black` might not.
2. **Overlays and frosted glass** — `rgba(0,0,0,0.4)` over a dark image is unpredictable.
3. **Focus rings** — `outline: 2px solid #3b82f6` (blue-500) on a dark navy page may fail.

Safe dark-mode text colors:
- Primary: `#f9fafb` (gray-50) — ratio ~18.4:1 on `#111827`
- Secondary: `#e5e7eb` (gray-200) — ratio ~13.1:1 on `#111827`  
- Muted/placeholder: `#9ca3af` (gray-400) — ratio ~5.2:1 on `#111827` ✓

---

## APCA (Accessible Perceptual Contrast Algorithm)

WCAG 3.0 will use APCA instead of the current ratio formula. APCA is more perceptually accurate, especially for light text on dark backgrounds. For now, WCAG 2.2 (ratio-based) remains the legal standard.

APCA quick reference (Lc values):
- Lc 90+ : Equivalent to high-contrast body text
- Lc 75+ : Body text, AA-like
- Lc 60+ : Large text / UI components
- Lc 45+ : Non-text graphical elements
- < Lc 30 : Decorative only

Online calculators: https://www.myndex.com/APCA/ or https://webaim.org/resources/contrastchecker/

---

## Browser DevTools shortcuts

| Action | Chrome | Firefox |
|---|---|---|
| Open accessibility tree | Elements > Accessibility tab | Inspector > Accessibility |
| Run axe scan | Install axe DevTools extension | Same |
| Check color contrast | Use color picker eyedropper in Styles | Same |
| Inspect focus order | Tab through with browser | Tab through |
| Simulate color blindness | Rendering panel > Emulate vision | Accessibility panel |
