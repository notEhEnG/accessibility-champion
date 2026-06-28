"""Image and iframe content rules."""

from __future__ import annotations

from a11y_context import ParseContext, TagAttrs
from a11y_rules.base import A11yRule, GENERIC_ALT_TEXT


class ImageRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag != "img":
            return

        if ctx.buttons.button_depth > 0 and ctx.buttons.current_button:
            alt = attrs.get("alt")
            if alt:
                ctx.buttons.current_button["text"] += " " + alt

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