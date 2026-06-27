# Sample Linter Output

Here is an example of what `a11y_lint.py` produces when run against a poorly accessible HTML file.

## Input (demo/broken_page.html)
```html
<!DOCTYPE html>
<html>
<head>
  <title>Broken Page</title>
</head>
<body>
  <img src="logo.png">
  <input type="text" id="username">
  <button></button>
  <table role="presentation">
     <tr><td>Data</td></tr>
  </table>
  <a href="#">Click here</a>
</body>
</html>
```

## Output
```text
=== Accessibility Audit: demo/broken_page.html ===

Score: 30/100  |  WCAG 2.2 AA

🔴 Critical (3 issues)

  [image-alt] line 7: <img> is missing an alt attribute
  → WCAG: 1.1.1 Non-text Content
  → Fix: Add alt="[description]" for informational images, or alt="" role="presentation" for decorative ones

  [input-missing-label] line 8: <input id="username"> has no associated <label for="username">
  → WCAG: 3.3.2 Labels or Instructions
  → Fix: Add <label for="username">Descriptive label</label> before or wrapping the input

  [button-name] line 9: <button> has no accessible name (empty inner text, no aria-label)
  → WCAG: 4.1.2 Name, Role, Value
  → Fix: Add aria-label="[action description]" or visible text content inside the button

🟠 Serious (2 issues)

  [html-has-lang] line 2: <html> tag is missing a lang attribute
  → WCAG: 3.1.1 Language of Page
  → Fix: Add lang="en" (or appropriate language code) to the <html> tag

  [link-name] line 13: Link with generic text "Click here" — meaningless out of context
  → WCAG: 2.4.4 Link Purpose (In Context)
  → Fix: Use descriptive link text like "Read the accessibility guide" or add aria-label="..."
```
