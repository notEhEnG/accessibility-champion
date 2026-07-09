"""ARIA reference validation rules."""

from __future__ import annotations

from a11y_context import ParseContext, TagAttrs
from a11y_rules.base import A11yRule, ARIA_REFERENCE_ATTRS


class AriaReferenceRule(A11yRule):
    """Validates aria-describedby, aria-labelledby, and aria-invalid references."""

    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if not any(attrs.has(name) for name in ARIA_REFERENCE_ATTRS):
            return

        described_by = attrs.get("aria-describedby")
        if described_by:
            ctx.aria.described_by_checks.append({"ids": described_by, "line": line})

        labelled_by = attrs.get("aria-labelledby")
        if labelled_by:
            ctx.aria.labelled_by_checks.append({"ids": labelled_by, "line": line})

        if attrs.get_lower("aria-invalid") == "true":
            ctx.aria.aria_invalid_checks.append({
                "line": line,
                "described_by": attrs.get("aria-describedby"),
            })

    def finalize(self, ctx: ParseContext) -> None:
        for check in ctx.aria.described_by_checks:
            for target in check["ids"].split():
                if target not in ctx.aria.ids_seen:
                    ctx.add_violation(
                        id="aria-describedby-missing-target",
                        severity="serious",
                        line=check["line"],
                        message=f"aria-describedby target '{target}' does not exist in the document",
                        fix=f"Ensure there is an element with id='{target}' to provide the description",
                        wcag="1.3.1 Info and Relationships",
                    )

        for check in ctx.aria.labelled_by_checks:
            for target in check["ids"].split():
                if target not in ctx.aria.ids_seen:
                    ctx.add_violation(
                        id="aria-labelledby-target",
                        severity="serious",
                        line=check["line"],
                        message=f"aria-labelledby target '{target}' does not exist in the document",
                        fix=f"Ensure there is an element with id='{target}' to provide the accessible name",
                        wcag="4.1.2 Name, Role, Value",
                    )

        for check in ctx.aria.aria_invalid_checks:
            described_by = check["described_by"]
            if not described_by:
                ctx.add_violation(
                    id="aria-invalid-no-desc",
                    severity="serious",
                    line=check["line"],
                    message='aria-invalid="true" without aria-describedby pointing to an error message',
                    fix='Add aria-describedby="error-id" referencing a visible error element',
                    wcag="3.3.1 Error Identification",
                )
                continue
            targets = described_by.split()
            if not targets or any(target not in ctx.aria.ids_seen for target in targets):
                ctx.add_violation(
                    id="aria-invalid-no-desc",
                    severity="serious",
                    line=check["line"],
                    message='aria-invalid="true" with aria-describedby pointing to a missing element',
                    fix="Ensure aria-describedby references an existing id that contains the error message",
                    wcag="3.3.1 Error Identification",
                )


class DuplicateIdRule(A11yRule):
    def finalize(self, ctx: ParseContext) -> None:
        for id_val, line in sorted(ctx.aria.duplicate_ids, key=lambda item: item[1]):
            ctx.add_violation(
                id="duplicate-id",
                severity="serious",
                line=line,
                message=f"Duplicate id attribute value '{id_val}' detected",
                fix="Ensure all id attributes on the page are unique",
                wcag="4.1.1 Parsing",
            )


_FOCUSABLE_TAGS = frozenset({"a", "button", "input", "select", "textarea"})
_REDUNDANT_ROLES = frozenset({
    ("button", "button"),
    ("a", "link"),
    ("input", "textbox"),
    ("img", "img"),
})


class AriaHiddenFocusableRule(A11yRule):
    """Focusable element inside an aria-hidden='true' subtree."""

    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        is_hidden = attrs.get_lower("aria-hidden") == "true"
        ctx.aria.hidden_stack.append(is_hidden)
        if any(ctx.aria.hidden_stack) and tag in _FOCUSABLE_TAGS:
            if tag == "input" and attrs.get_lower("type") == "hidden":
                return
            ctx.add_violation(
                id="aria-hidden-focusable",
                severity="serious",
                line=line,
                message='Focusable element inside an aria-hidden="true" subtree',
                fix="Remove aria-hidden from the ancestor or remove focusable content from the hidden subtree",
                wcag="4.1.2 Name, Role, Value",
            )

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if ctx.aria.hidden_stack:
            ctx.aria.hidden_stack.pop()


class RedundantRoleRule(A11yRule):
    """role='button' on <button>, etc. — implicit role restated."""

    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        role = attrs.get_lower("role")
        if not role:
            return
        if (tag, role) in _REDUNDANT_ROLES:
            ctx.add_violation(
                id="redundant-role",
                severity="minor",
                line=line,
                message=f'Redundant role="{role}" on <{tag}> (implicit role)',
                fix=f'Remove role="{role}" from the native <{tag}>',
                wcag="4.1.2 Name, Role, Value",
            )