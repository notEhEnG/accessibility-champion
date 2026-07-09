"""Document-level rules: lang, title, duplicate ids."""

from __future__ import annotations

from a11y_context import ParseContext, TagAttrs
from a11y_rules.base import A11yRule


class DocumentRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag in ("html", "body"):
            ctx.page.is_full_page = True

        if tag == "html":
            ctx.page.html_line = line
            if not attrs.has("lang"):
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


class DocumentTitleRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "head":
            ctx.page.head_line = line
            ctx.page.head_depth += 1
        if tag == "title" and ctx.page.head_depth > 0:
            ctx.page.document_title_depth += 1
            ctx.page.document_title = ""

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag == "title":
            ctx.page.document_title_depth = max(0, ctx.page.document_title_depth - 1)
        if tag == "head":
            ctx.page.head_depth = max(0, ctx.page.head_depth - 1)

    def on_data(self, ctx: ParseContext, data: str) -> None:
        if ctx.page.document_title_depth > 0:
            ctx.page.document_title += data

    def finalize(self, ctx: ParseContext) -> None:
        if ctx.fragment_mode or not ctx.page.is_full_page:
            return
        if not ctx.page.document_title.strip():
            ctx.add_violation(
                id="document-title",
                severity="serious",
                line=ctx.page.head_line,
                message="Full page is missing a non-empty <title> element in <head>",
                fix="Add <title>Page name — Site name</title> inside <head>",
                wcag="2.4.2 Page Titled",
            )


class LangSubtagRule(A11yRule):
    """Inline lang attribute that is too short to be a valid BCP 47 tag (heuristic)."""

    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag not in ("span", "p", "div", "i", "em"):
            return
        lang = attrs.get("lang")
        if not lang:
            return
        if len(lang) < 2:
            ctx.add_violation(
                id="lang-subtag",
                severity="minor",
                line=line,
                message=f'Inline lang="{lang}" may be invalid (heuristic)',
                fix='Use a valid BCP 47 language tag, e.g. lang="es" or lang="zh-Hans"',
                wcag="3.1.2 Language of Parts",
            )