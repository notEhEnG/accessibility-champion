"""Interactive controls validation rules: ButtonNameRule, TabIndexRule."""

from __future__ import annotations

from a11y_context import ParseContext, TagAttrs
from a11y_rules.base import A11yRule


class ButtonNameRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "svg":
            ctx.buttons.in_svg_depth += 1
            return
        if tag == "title":
            ctx.buttons.in_title_depth += 1
            ctx.buttons.current_title_text = ""
            return
        if tag != "button":
            return

        ctx.buttons.button_depth += 1
        if ctx.buttons.button_depth == 1:
            has_aria = attrs.has("aria-label") or attrs.has("aria-labelledby")
            ctx.buttons.current_button = {"line": line, "has_aria": has_aria, "text": ""}

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag == "title":
            ctx.buttons.in_title_depth = max(0, ctx.buttons.in_title_depth - 1)
            if (
                ctx.buttons.in_title_depth == 0
                and ctx.buttons.in_svg_depth > 0
                and ctx.buttons.button_depth > 0
                and ctx.buttons.current_button
            ):
                ctx.buttons.current_button["text"] += " " + ctx.buttons.current_title_text
            return

        if tag == "svg":
            ctx.buttons.in_svg_depth = max(0, ctx.buttons.in_svg_depth - 1)
            return

        if tag != "button":
            return

        if ctx.buttons.button_depth == 1 and ctx.buttons.current_button:
            if not ctx.buttons.current_button["has_aria"] and not ctx.buttons.current_button["text"].strip():
                ctx.add_violation(
                    id="button-name",
                    severity="critical",
                    line=ctx.buttons.current_button["line"],
                    message="<button> has no accessible name (empty inner text, no aria-label, and no descriptive child images/svgs)",
                    fix='Add aria-label="[action description]" or visible text content inside the button',
                    wcag="4.1.2 Name, Role, Value",
                )
            ctx.buttons.current_button = None
        ctx.buttons.button_depth = max(0, ctx.buttons.button_depth - 1)

    def on_data(self, ctx: ParseContext, data: str) -> None:
        if ctx.buttons.button_depth <= 0 or not ctx.buttons.current_button:
            return
        if ctx.buttons.in_title_depth > 0 and ctx.buttons.in_svg_depth > 0:
            ctx.buttons.current_title_text += data
        elif not ctx.buttons.in_svg_depth:
            ctx.buttons.current_button["text"] += data


class TabIndexRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        tabindex = attrs.get("tabindex")
        if tabindex is None:
            return
        try:
            value = int(tabindex.strip())
        except ValueError:
            return
        if value > 0:
            ctx.add_violation(
                id="tabindex-positive",
                severity="moderate",
                line=line,
                message=f'Positive tabindex="{value}" disrupts natural keyboard navigation order',
                fix='Remove tabindex or use tabindex="0"; reorder the DOM instead of overriding tab order',
                wcag="2.4.3 Focus Order",
            )
