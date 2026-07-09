"""Link rules: LinkNameRule, SkipLinkRule, TargetBlankRule."""

from __future__ import annotations

import re

from a11y_context import ParseContext, TagAttrs
from a11y_rules.base import (
    A11yRule,
    GENERIC_LINK_PREFIXES,
    GENERIC_LINK_EXACTS,
    NEW_WINDOW_HINTS,
    SKIP_LINK_HREF_HINTS,
)


class SkipLinkRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag != "a":
            return
        href = (attrs.get("href") or "").strip().lower()
        if href.startswith("#") and any(hint in href for hint in SKIP_LINK_HREF_HINTS):
            ctx.page.has_skip_link = True

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag != "a":
            return
        if ctx.links.current_link:
            text = ctx.links.current_link["text"].strip().lower()
            href = ctx.links.current_link["href"]
            if "skip" in text and href.startswith("#"):
                ctx.page.has_skip_link = True

    def finalize(self, ctx: ParseContext) -> None:
        if ctx.fragment_mode or not ctx.page.is_full_page or not ctx.page.has_nav:
            return
        if not ctx.page.has_skip_link:
            ctx.add_violation(
                id="skip-link",
                severity="moderate",
                line=ctx.page.nav_line,
                message='Page with navigation is missing a "skip to main content" link',
                fix='Add <a href="#main-content">Skip to main content</a> as the first focusable element',
                wcag="2.4.1 Bypass Blocks",
            )


class TargetBlankRule(A11yRule):
    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag != "a":
            return
        if ctx.links.current_link and ctx.links.current_link["target_blank"]:
            text = ctx.links.current_link["text"].strip().lower()
            combined = " ".join(
                filter(None, (text, ctx.links.current_link["aria_label"], ctx.links.current_link["title"]))
            )
            if not any(hint in combined for hint in NEW_WINDOW_HINTS):
                ctx.add_violation(
                    id="target-blank-no-warning",
                    severity="minor",
                    line=ctx.links.current_link["line"],
                    message='Link with target="_blank" lacks an accessible new-window warning',
                    fix='Add visible text, aria-label, or title indicating the link opens in a new window/tab',
                    wcag="3.2.5 Change on Request",
                )


class LinkNameRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag != "a":
            return
        ctx.links.link_depth += 1
        if ctx.links.link_depth == 1:
            ctx.links.current_link = {
                "line": line,
                "text": "",
                "href": (attrs.get("href") or "").strip().lower(),
                "target_blank": attrs.get_lower("target") == "_blank",
                "aria_label": (attrs.get("aria-label") or "").lower(),
                "title": (attrs.get("title") or "").lower(),
            }

    def on_data(self, ctx: ParseContext, data: str) -> None:
        if ctx.links.link_depth > 0 and ctx.links.current_link:
            ctx.links.current_link["text"] += data

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag != "a":
            return
        if ctx.links.link_depth == 1 and ctx.links.current_link:
            text = ctx.links.current_link["text"].strip().lower()
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
                    line=ctx.links.current_link["line"],
                    message=f'Link with generic text "{text}" (matches phrase "{matched_phrase}") — meaningless out of context',
                    fix='Use descriptive link text like "Read the accessibility guide" or add aria-label="..."',
                    wcag="2.4.4 Link Purpose (In Context)",
                )

            ctx.links.current_link = None
        ctx.links.link_depth = max(0, ctx.links.link_depth - 1)


_FILENAME_RE = re.compile(r"\.(pdf|docx?|xlsx?|zip|png|jpe?g|gif)\b", re.I)


class EmptyLinkRule(A11yRule):
    """<a> with no meaningful href destination."""

    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag != "a":
            return
        href = (attrs.get("href") or "").strip()
        if not href or href == "#":
            ctx.add_violation(
                id="empty-link",
                severity="moderate",
                line=line,
                message="<a> has no meaningful href destination",
                fix='Use a real URL or href="#section-id" with descriptive text',
                wcag="2.4.4 Link Purpose (In Context)",
            )


class FilenameLinkTextRule(A11yRule):
    """Link text that is just a filename (heuristic). Runs before LinkNameRule clears state."""

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag != "a" or ctx.links.link_depth != 1 or not ctx.links.current_link:
            return
        text = ctx.links.current_link["text"].strip()
        if text and _FILENAME_RE.search(text):
            ctx.add_violation(
                id="filename-link-text",
                severity="minor",
                line=ctx.links.current_link["line"],
                message=f'Link text "{text}" looks like a filename (heuristic)',
                fix="Describe the link purpose, not the file name",
                wcag="2.4.4 Link Purpose (In Context)",
            )
