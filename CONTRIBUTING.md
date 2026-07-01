# Contributing to Accessibility Champion

## Adding a linter rule

1. Add class extending `A11yRule` in the appropriate `a11y_rules/*.py` module.
2. Implement `on_starttag`, `on_endtag`, `on_data`, and/or `finalize`.
3. Register in `a11y_rules/__init__.py` → `all_rules()`.
4. Add failing + passing tests in `test_a11y_lint.py`.
5. Update `README.md`, `SKILL.md` (`[linter]`), `demo/broken_page.html` if applicable.

## Rule template

```python
class ExampleRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        ...

    def finalize(self, ctx: ParseContext) -> None:
        ...
```

## Test template

```python
def test_example_rule_fails(self):
    source = """<html lang="en"><main>...</main></html>"""
    violations = check_html(source)
    self.assertIn("example-rule", [v["id"] for v in violations])

def test_example_rule_passes(self):
    source = """<html lang="en"><main>...</main></html>"""
    violations = check_html(source)
    self.assertNotIn("example-rule", [v["id"] for v in violations])
```

## Severity

| Severity | Use when |
|----------|----------|
| critical | Blocks access (missing label, alt, button name) |
| serious | WCAG failure likely (lang, iframe title, captions) |
| moderate | Best practice / operability (skip link, heading order) |
| minor | Advisory (landmarks, autocomplete hints) |

## fix_confidence (JSON violations)

- `auto` — deterministic, AST-safe fix only
- `assisted` — suggest patch; user confirms (default for heuristics)
- `manual` — human judgment (contrast in context, alt meaning)

## PR checklist

- [ ] Tests added (fail + pass)
- [ ] README rule table updated
- [ ] SKILL.md `[linter]` list updated
- [ ] Demo fixture updated if rule appears in `broken_page.html`
- [ ] Respects `ctx.fragment_mode` and full-page checks
- [ ] No file > 400 lines (`python3 scripts/check_max_file_size.py`)
