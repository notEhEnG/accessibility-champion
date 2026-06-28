"""Individual accessibility rules invoked by the HTML parser dispatcher."""

from __future__ import annotations

from a11y_context import ParseContext, TagAttrs

GENERIC_ALT_TEXT = frozenset({"image", "picture", "photo", "logo", "icon", "graphic"})
GENERIC_LINK_PREFIXES = ("click here", "read more", "learn more")
GENERIC_LINK_EXACTS = ("here", "more")
AUTOCOMPLETE_HINTS = ("name", "address", "city", "zip", "phone", "email")
LABELLED_INPUT_TYPES = frozenset({"hidden", "submit", "button", "image", "reset"})


class A11yRule:
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        pass

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        pass

    def on_data(self, ctx: ParseContext, data: str) -> None:
        pass

    def finalize(self, ctx: ParseContext) -> None:
        pass


class DocumentRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag in ("html", "body"):
            ctx.is_full_page = True

        if tag == "html" and not attrs.has("lang"):
            ctx.add_violation(
                id="html-has-lang",
                severity="serious",
                line=line,
                message="<html> tag is missing a lang attribute",
                fix='Add lang="en" (or appropriate language code) to the <html> tag',
                wcag="3.1.1 Language of Page",
            )

        id_val = attrs.get("id")
        if id_val:
            ctx.track_id(id_val, line)


class LandmarkRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        role = attrs.get_lower("role")
        if tag == "header" or role == "banner":
            ctx.has_header = True
        if tag == "nav" or role == "navigation":
            ctx.has_nav = True
        if tag == "footer" or role == "contentinfo":
            ctx.has_footer = True
        if tag == "main" or role == "main":
            ctx.has_main = True

    def finalize(self, ctx: ParseContext) -> None:
        if ctx.fragment_mode or not ctx.is_full_page:
            return

        if not ctx.has_main:
            ctx.add_violation(
                id="missing-main",
                severity="moderate",
                line=1,
                message="Page is missing a <main> landmark",
                fix="Wrap the primary content of the page in a <main> tag",
                wcag="1.3.1 Info and Relationships",
            )
        if not ctx.has_header:
            ctx.add_violation(
                id="missing-header-landmark",
                severity="minor",
                line=1,
                message="Page is missing a <header> or role='banner' landmark (manual review recommended)",
                fix="Wrap page headers in a <header> element or add role='banner'",
                wcag="1.3.1 Info and Relationships",
            )
        if not ctx.has_nav:
            ctx.add_violation(
                id="missing-nav-landmark",
                severity="minor",
                line=1,
                message="Page is missing a <nav> or role='navigation' landmark (manual review recommended)",
                fix="Wrap page navigation in a <nav> element or add role='navigation'",
                wcag="1.3.1 Info and Relationships",
            )
        if not ctx.has_footer:
            ctx.add_violation(
                id="missing-footer-landmark",
                severity="minor",
                line=1,
                message="Page is missing a <footer> or role='contentinfo' landmark (manual review recommended)",
                fix="Wrap page footer in a <footer> element or add role='contentinfo'",
                wcag="1.3.1 Info and Relationships",
            )


class HeadingRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag not in ("h1", "h2", "h3", "h4", "h5", "h6"):
            return

        level = int(tag[1])
        if tag == "h1":
            ctx.h1_count += 1

        if ctx.headings_seen:
            prev_level = ctx.headings_seen[-1]
            if level > prev_level + 1:
                ctx.add_violation(
                    id="heading-order",
                    severity="moderate",
                    line=line,
                    message=f"Heading level skipped: H{prev_level} → H{level}",
                    fix=f"Use H{prev_level + 1} here, or restructure heading hierarchy to avoid gaps",
                    wcag="1.3.1 Info and Relationships",
                )
        ctx.headings_seen.append(level)

    def finalize(self, ctx: ParseContext) -> None:
        if ctx.fragment_mode or not ctx.is_full_page or ctx.h1_count == 1:
            return
        ctx.add_violation(
            id="heading-single-h1",
            severity="moderate",
            line=1,
            message=f"Page has {ctx.h1_count} <h1> elements; expected exactly one per page",
            fix="Use a single <h1> for the page title and demote other top-level headings to <h2>",
            wcag="1.3.1 Info and Relationships",
        )


class ImageRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag != "img":
            return

        if ctx.button_depth > 0 and ctx.current_button:
            alt = attrs.get("alt")
            if alt:
                ctx.current_button["text"] += " " + alt

        if not attrs.has("alt"):
            ctx.add_violation(
                id="image-alt",
                severity="critical",
                line=line,
                message="<img> is missing an alt attribute",
                fix='Add alt="[description]" for informational images, or alt="" role="presentation" for decorative ones',
                wcag="1.1.1 Non-text Content",
            )
            return

        alt_text = (attrs.get("alt") or "").strip().lower()
        if alt_text in GENERIC_ALT_TEXT:
            ctx.add_violation(
                id="image-alt-quality",
                severity="moderate",
                line=line,
                message=f'<img> alt text "{alt_text}" is not descriptive (human review required)',
                fix="Describe the purpose and meaning of the image, not what it is",
                wcag="1.1.1 Non-text Content",
            )


class FormLabelRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "label":
            label_for = attrs.get("for")
            if label_for:
                ctx.label_fors.add(label_for)
            return

        if tag not in ("input", "select", "textarea"):
            return

        has_aria = attrs.has("aria-label") or attrs.has("aria-labelledby")
        if has_aria:
            return

        if tag == "input":
            itype = attrs.get_lower("type") or "text"
            if itype in LABELLED_INPUT_TYPES:
                return
        else:
            itype = tag

        if ctx.in_tag("label"):
            return

        element_id = attrs.get("id")
        if not element_id:
            ctx.add_violation(
                id="input-unlabelled",
                severity="critical",
                line=line,
                message=f"<{tag} type=\"{itype}\"> has no id and is not wrapped in a <label> — cannot be associated with a label",
                fix='Add a unique id attribute and a <label for="that-id"> element, wrap it in a <label>, or add aria-label="..."',
                wcag="1.3.1 Info and Relationships",
            )
            return

        ctx.inputs_needing_labels.append({"id": element_id, "line": line, "tag": tag, "itype": itype})

    def finalize(self, ctx: ParseContext) -> None:
        for inp in ctx.inputs_needing_labels:
            if inp["id"] not in ctx.label_fors:
                ctx.add_violation(
                    id="input-missing-label",
                    severity="critical",
                    line=inp["line"],
                    message=f'<{inp["tag"]} id="{inp["id"]}"> has no associated <label for="{inp["id"]}">',
                    fix=f'Add <label for="{inp["id"]}">Descriptive label</label> before or wrapping the control',
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
            ctx.fieldset_stack.append({"has_legend": False})
            return

        if tag == "legend" and ctx.fieldset_stack:
            ctx.fieldset_stack[-1]["has_legend"] = True
            return

        if tag != "input":
            return

        itype = attrs.get_lower("type")
        if itype not in ("radio", "checkbox"):
            return

        name = attrs.get("name")
        if not name:
            return

        in_fieldset = bool(ctx.fieldset_stack)
        has_legend = ctx.fieldset_stack[-1]["has_legend"] if in_fieldset else False
        key = (itype, name)
        group = ctx.radio_checkbox_groups.setdefault(
            key,
            {"line": line, "count": 0, "valid": in_fieldset and has_legend},
        )
        group["count"] += 1
        if in_fieldset and has_legend:
            group["valid"] = True

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag == "fieldset" and ctx.fieldset_stack:
            ctx.fieldset_stack.pop()

    def finalize(self, ctx: ParseContext) -> None:
        for (itype, name), group in ctx.radio_checkbox_groups.items():
            if group["count"] > 1 and not group["valid"]:
                ctx.add_violation(
                    id="form-group-fieldset",
                    severity="moderate",
                    line=group["line"],
                    message=f"{group['count']} grouped {itype} inputs (name='{name}') should be wrapped in a <fieldset> with a <legend>",
                    fix=f"Wrap the group of {itype} inputs in a <fieldset> and add a descriptive <legend>",
                    wcag="1.3.1 Info and Relationships",
                )


class AriaDescribedByRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag not in ("input", "select", "textarea"):
            return
        described_by = attrs.get("aria-describedby")
        if described_by:
            ctx.described_by_checks.append({"described_by": described_by, "line": line})

    def finalize(self, ctx: ParseContext) -> None:
        for check in ctx.described_by_checks:
            for target in check["described_by"].split():
                if target not in ctx.ids_seen:
                    ctx.add_violation(
                        id="aria-describedby-missing-target",
                        severity="serious",
                        line=check["line"],
                        message=f"aria-describedby target '{target}' does not exist in the document",
                        fix=f"Ensure there is an element with id='{target}' to provide the description",
                        wcag="1.3.1 Info and Relationships",
                    )


class ButtonNameRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "svg":
            ctx.in_svg_depth += 1
            return
        if tag == "title":
            ctx.in_title_depth += 1
            ctx.current_title_text = ""
            return
        if tag != "button":
            return

        ctx.button_depth += 1
        if ctx.button_depth == 1:
            has_aria = attrs.has("aria-label") or attrs.has("aria-labelledby")
            ctx.current_button = {"line": line, "has_aria": has_aria, "text": ""}

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag == "title":
            ctx.in_title_depth = max(0, ctx.in_title_depth - 1)
            if (
                ctx.in_title_depth == 0
                and ctx.in_svg_depth > 0
                and ctx.button_depth > 0
                and ctx.current_button
            ):
                ctx.current_button["text"] += " " + ctx.current_title_text
            return

        if tag == "svg":
            ctx.in_svg_depth = max(0, ctx.in_svg_depth - 1)
            return

        if tag != "button":
            return

        if ctx.button_depth == 1 and ctx.current_button:
            if not ctx.current_button["has_aria"] and not ctx.current_button["text"].strip():
                ctx.add_violation(
                    id="button-name",
                    severity="critical",
                    line=ctx.current_button["line"],
                    message="<button> has no accessible name (empty inner text, no aria-label, and no descriptive child images/svgs)",
                    fix='Add aria-label="[action description]" or visible text content inside the button',
                    wcag="4.1.2 Name, Role, Value",
                )
            ctx.current_button = None
        ctx.button_depth = max(0, ctx.button_depth - 1)

    def on_data(self, ctx: ParseContext, data: str) -> None:
        if ctx.button_depth <= 0 or not ctx.current_button:
            return
        if ctx.in_title_depth > 0 and ctx.in_svg_depth > 0:
            ctx.current_title_text += data
        elif not ctx.in_svg_depth:
            ctx.current_button["text"] += data


class LinkNameRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag != "a":
            return
        ctx.link_depth += 1
        if ctx.link_depth == 1:
            ctx.current_link = {"line": line, "text": ""}

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag != "a":
            return

        if ctx.link_depth == 1 and ctx.current_link:
            text = ctx.current_link["text"].strip().lower()
            matched_phrase = ""
            is_generic = any(
                text == prefix or text.startswith(prefix + " ")
                for prefix in GENERIC_LINK_PREFIXES
            )
            if not is_generic:
                for exact in GENERIC_LINK_EXACTS:
                    if text == exact:
                        is_generic = True
                        matched_phrase = exact
                        break
            else:
                for prefix in GENERIC_LINK_PREFIXES:
                    if text == prefix or text.startswith(prefix + " "):
                        matched_phrase = prefix
                        break

            if is_generic:
                ctx.add_violation(
                    id="link-name",
                    severity="serious",
                    line=ctx.current_link["line"],
                    message=f'Link with generic text "{text}" (matches phrase "{matched_phrase}") — meaningless out of context',
                    fix='Use descriptive link text like "Read the accessibility guide" or add aria-label="..."',
                    wcag="2.4.4 Link Purpose (In Context)",
                )
            ctx.current_link = None
        ctx.link_depth = max(0, ctx.link_depth - 1)

    def on_data(self, ctx: ParseContext, data: str) -> None:
        if ctx.link_depth > 0 and ctx.current_link:
            ctx.current_link["text"] += data


class TableRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "table":
            ctx.table_depth += 1
            if ctx.table_depth == 1:
                ctx.current_table_has_th = False
                ctx.current_table_has_caption = False
                ctx.current_table_is_presentation = attrs.get_lower("role") == "presentation"
                ctx.current_table_line = line
            return

        if ctx.table_depth <= 0:
            return
        if tag == "th":
            ctx.current_table_has_th = True
        if tag == "caption":
            ctx.current_table_has_caption = True

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag != "table":
            return

        if ctx.table_depth == 1 and not ctx.current_table_is_presentation:
            if not ctx.current_table_has_th:
                ctx.add_violation(
                    id="table-th",
                    severity="serious",
                    line=ctx.current_table_line,
                    message="Data table has no <th> header cells",
                    fix="Add <th scope='col'> for column headers and <th scope='row'> for row headers",
                    wcag="1.3.1 Info and Relationships",
                )
            if not ctx.current_table_has_caption:
                ctx.add_violation(
                    id="table-caption",
                    severity="moderate",
                    line=ctx.current_table_line,
                    message="Table is missing a <caption> describing its purpose",
                    fix="Add <caption>Table description</caption> as first child of <table>",
                    wcag="1.3.1 Info and Relationships",
                )
        ctx.table_depth = max(0, ctx.table_depth - 1)


class MediaRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag not in ("video", "audio"):
            return
        if attrs.has("autoplay"):
            ctx.add_violation(
                id="no-autoplay",
                severity="serious",
                line=line,
                message="Media with autoplay — can disorient screen reader users and violate WCAG 1.4.2",
                fix="Remove autoplay, or add controls and a mechanism to pause/stop the media",
                wcag="1.4.2 Audio Control",
            )


class FrameRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "iframe" and not attrs.has("title"):
            ctx.add_violation(
                id="frame-title",
                severity="serious",
                line=line,
                message="<iframe> is missing a title attribute",
                fix='Add title="Description of iframe content" to the <iframe>',
                wcag="2.4.1 Bypass Blocks",
            )


class DuplicateIdRule(A11yRule):
    def finalize(self, ctx: ParseContext) -> None:
        for id_val, line in sorted(ctx.duplicate_ids, key=lambda item: item[1]):
            ctx.add_violation(
                id="duplicate-id",
                severity="serious",
                line=line,
                message=f"Duplicate id attribute value '{id_val}' detected",
                fix="Ensure all id attributes on the page are unique",
                wcag="4.1.1 Parsing",
            )


def all_rules() -> list[A11yRule]:
    return [
        DocumentRule(),
        LandmarkRule(),
        HeadingRule(),
        ImageRule(),
        FormLabelRule(),
        AutocompleteRule(),
        FormGroupRule(),
        AriaDescribedByRule(),
        ButtonNameRule(),
        LinkNameRule(),
        TableRule(),
        MediaRule(),
        FrameRule(),
        DuplicateIdRule(),
    ]