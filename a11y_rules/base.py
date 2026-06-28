"""Base rule class and shared constants."""

from __future__ import annotations

from a11y_context import ParseContext, TagAttrs

GENERIC_ALT_TEXT = frozenset({"image", "picture", "photo", "logo", "icon", "graphic"})
GENERIC_LINK_PREFIXES = ("click here", "read more", "learn more")
GENERIC_LINK_EXACTS = ("here", "more")
AUTOCOMPLETE_HINTS = ("name", "address", "city", "zip", "phone", "email")
LABELLED_INPUT_TYPES = frozenset({"hidden", "submit", "button", "image", "reset"})
NEW_WINDOW_HINTS = ("new window", "new tab", "opens in")
SKIP_LINK_HREF_HINTS = ("main", "content", "skip")
ARIA_REFERENCE_ATTRS = frozenset({
    "aria-describedby",
    "aria-labelledby",
    "aria-invalid",
})


class A11yRule:
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        pass

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        pass

    def on_data(self, ctx: ParseContext, data: str) -> None:
        pass

    def finalize(self, ctx: ParseContext) -> None:
        pass