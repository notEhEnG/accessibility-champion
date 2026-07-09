"""Form labeling, autocomplete, and grouping rules."""

from __future__ import annotations

from a11y_context import ParseContext, TagAttrs
from a11y_rules.base import AUTOCOMPLETE_HINTS, LABELLED_INPUT_TYPES, A11yRule


def _input_type(tag: str, attrs: TagAttrs) -> str:
    if tag == "input":
        return attrs.get_lower("type") or "text"
    return tag


def _is_exempt_control(tag: str, attrs: TagAttrs) -> bool:
    if tag != "input":
        return False
    return _input_type(tag, attrs) in LABELLED_INPUT_TYPES


class FormLabelRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "label":
            label_for = attrs.get("for")
            if label_for:
                ctx.forms.label_fors.add(label_for)
            return

        if tag not in ("input", "select", "textarea"):
            return

        if attrs.has("aria-label") or attrs.has("aria-labelledby"):
            return

        if attrs.has("placeholder") and tag in ("input", "textarea"):
            if not _is_exempt_control(tag, attrs) and not ctx.in_tag("label"):
                ctx.forms.placeholder_controls.append({
                    "id": attrs.get("id"),
                    "line": line,
                    "tag": tag,
                    "itype": _input_type(tag, attrs),
                })
            return

        if _is_exempt_control(tag, attrs) or ctx.in_tag("label"):
            return

        itype = _input_type(tag, attrs)
        element_id = attrs.get("id")
        if not element_id:
            ctx.add_violation(
                id="input-unlabelled",
                severity="critical",
                line=line,
                message=f'<{tag} type="{itype}"> has no id and is not wrapped in a <label> — cannot be associated with a label',
                fix='Add a unique id attribute and a <label for="that-id"> element, wrap it in a <label>, or add aria-label="..."',
                wcag="1.3.1 Info and Relationships",
            )
            return

        ctx.forms.inputs_needing_labels.append({
            "id": element_id,
            "line": line,
            "tag": tag,
            "itype": itype,
        })

    def finalize(self, ctx: ParseContext) -> None:
        for inp in ctx.forms.inputs_needing_labels:
            if inp["id"] not in ctx.forms.label_fors:
                ctx.add_violation(
                    id="input-missing-label",
                    severity="critical",
                    line=inp["line"],
                    message=f'<{inp["tag"]} id="{inp["id"]}"> has no associated <label for="{inp["id"]}">',
                    fix=f'Add <label for="{inp["id"]}">Descriptive label</label> before or wrapping the control',
                    wcag="3.3.2 Labels or Instructions",
                )


class PlaceholderRule(A11yRule):
    def finalize(self, ctx: ParseContext) -> None:
        for control in ctx.forms.placeholder_controls:
            element_id = control["id"]
            if element_id and element_id in ctx.forms.label_fors:
                continue
            ctx.add_violation(
                id="placeholder-as-label",
                severity="critical",
                line=control["line"],
                message=f'<{control["tag"]}> uses placeholder text as the only label — placeholders are not accessible labels',
                fix="Add a visible <label> or aria-label; use placeholder only for format hints",
                wcag="3.3.2 Labels or Instructions",
            )


class AutocompleteRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag != "input":
            return

        itype = attrs.get_lower("type") or "text"
        name_id = ((attrs.get("name") or "") + (attrs.get("id") or "")).lower()
        needs_autocomplete = itype in ("email", "password", "tel") or (
            itype == "text" and any(hint in name_id for hint in AUTOCOMPLETE_HINTS)
        )

        if needs_autocomplete and not attrs.has("autocomplete"):
            ctx.add_violation(
                id="input-autocomplete",
                severity="minor",
                line=line,
                message=f"Input field (type='{itype}', id/name='{name_id}') requesting personal data is missing an autocomplete attribute",
                fix='Add an appropriate autocomplete attribute (e.g., autocomplete="email")',
                wcag="1.3.5 Identify Input Purpose",
            )


class FormGroupRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "fieldset":
            ctx.forms.fieldset_stack.append({"has_legend": False})
            return

        if tag == "legend" and ctx.forms.fieldset_stack:
            ctx.forms.fieldset_stack[-1]["has_legend"] = True
            return

        if tag != "input":
            return

        itype = attrs.get_lower("type")
        if itype not in ("radio", "checkbox"):
            return

        name = attrs.get("name")
        if not name:
            return

        in_fieldset = bool(ctx.forms.fieldset_stack)
        has_legend = ctx.forms.fieldset_stack[-1]["has_legend"] if in_fieldset else False
        key = (itype, name)
        group = ctx.forms.radio_checkbox_groups.setdefault(
            key,
            {"line": line, "count": 0, "valid": in_fieldset and has_legend},
        )
        group["count"] += 1
        if in_fieldset and has_legend:
            group["valid"] = True

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag == "fieldset" and ctx.forms.fieldset_stack:
            ctx.forms.fieldset_stack.pop()

    def finalize(self, ctx: ParseContext) -> None:
        for (itype, name), group in ctx.forms.radio_checkbox_groups.items():
            if group["count"] > 1 and not group["valid"]:
                ctx.add_violation(
                    id="form-group-fieldset",
                    severity="moderate",
                    line=group["line"],
                    message=f"{group['count']} grouped {itype} inputs (name='{name}') should be wrapped in a <fieldset> with a <legend>",
                    fix=f"Wrap the group of {itype} inputs in a <fieldset> and add a descriptive <legend>",
                    wcag="1.3.1 Info and Relationships",
                )


class ButtonTypeRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "form":
            ctx.forms.form_depth += 1
            return
        if tag == "button" and ctx.forms.form_depth > 0 and not attrs.has("type"):
            ctx.add_violation(
                id="button-type-missing",
                severity="moderate",
                line=line,
                message='<button> inside <form> is missing an explicit type attribute (defaults to submit)',
                fix='Add type="button" for actions or type="submit" for form submission',
                wcag="4.1.2 Name, Role, Value",
            )

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag == "form":
            ctx.forms.form_depth = max(0, ctx.forms.form_depth - 1)


class RequiredIndicatorRule(A11yRule):
    """Required control without a visible or programmatic required indicator (heuristic)."""

    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag not in ("input", "select", "textarea"):
            return
        required = attrs.has("required") or attrs.get_lower("aria-required") == "true"
        if not required:
            return
        ctx.forms.required_controls.append(
            {"line": line, "tag": tag, "has_aria": attrs.has("aria-label")}
        )

    def finalize(self, ctx: ParseContext) -> None:
        for ctrl in ctx.forms.required_controls:
            if ctrl["has_aria"]:
                continue
            ctx.add_violation(
                id="required-indicator",
                severity="moderate",
                line=ctrl["line"],
                message=f"Required <{ctrl['tag']}> lacks a visible required indicator (heuristic)",
                fix='Add visible "required" text, an asterisk with legend, or aria-describedby to a required hint',
                wcag="3.3.2 Labels or Instructions",
            )


class SelectEmptyLabelRule(A11yRule):
    """<select> whose empty first <option> is its only label."""

    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "select":
            ctx.forms.select_stack.append({
                "line": line,
                "first_option_text": None,
                "option_count": 0,
                "has_label": attrs.has("aria-label") or attrs.has("aria-labelledby"),
                "id": attrs.get("id"),
            })
        elif tag == "option" and ctx.forms.select_stack:
            sel = ctx.forms.select_stack[-1]
            if sel["option_count"] == 0:
                sel["first_option_text"] = ""
            sel["option_count"] += 1

    def on_data(self, ctx: ParseContext, data: str) -> None:
        if not ctx.forms.select_stack:
            return
        sel = ctx.forms.select_stack[-1]
        if sel["option_count"] == 1 and sel["first_option_text"] is not None:
            sel["first_option_text"] += data

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag != "select" or not ctx.forms.select_stack:
            return
        sel = ctx.forms.select_stack.pop()
        if sel["has_label"] or (sel["id"] and sel["id"] in ctx.forms.label_fors):
            return
        first = (sel.get("first_option_text") or "").strip()
        if first == "" and not ctx.in_tag("label"):
            ctx.add_violation(
                id="select-empty-label",
                severity="serious",
                line=sel["line"],
                message="<select> uses an empty first <option> as its sole label",
                fix='Add <label for="..."> or a non-empty first option with a real label',
                wcag="3.3.2 Labels or Instructions",
            )