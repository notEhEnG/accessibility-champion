"""Landmarks, headings, skip links, and tables."""

from __future__ import annotations

from a11y_context import ParseContext, TagAttrs
from a11y_rules.base import A11yRule


class LandmarkRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        role = attrs.get_lower("role")
        if tag == "header" or role == "banner":
            ctx.page.has_header = True
        if tag == "nav" or role == "navigation":
            ctx.page.has_nav = True
            ctx.page.nav_line = line
        if tag == "footer" or role == "contentinfo":
            ctx.page.has_footer = True
        if tag == "main" or role == "main":
            ctx.page.has_main = True

    def finalize(self, ctx: ParseContext) -> None:
        if ctx.fragment_mode or not ctx.page.is_full_page:
            return
        page_line = ctx.page_line()

        if not ctx.page.has_main:
            ctx.add_violation(
                id="missing-main",
                severity="moderate",
                line=page_line,
                message="Page is missing a <main> landmark",
                fix="Wrap the primary content of the page in a <main> tag",
                wcag="1.3.1 Info and Relationships",
            )
        if not ctx.page.has_header:
            ctx.add_violation(
                id="missing-header-landmark",
                severity="minor",
                line=page_line,
                message="Page is missing a <header> or role='banner' landmark (manual review recommended)",
                fix="Wrap page headers in a <header> element or add role='banner'",
                wcag="1.3.1 Info and Relationships",
            )
        if not ctx.page.has_nav:
            ctx.add_violation(
                id="missing-nav-landmark",
                severity="minor",
                line=page_line,
                message="Page is missing a <nav> or role='navigation' landmark (manual review recommended)",
                fix="Wrap page navigation in a <nav> element or add role='navigation'",
                wcag="1.3.1 Info and Relationships",
            )
        if not ctx.page.has_footer:
            ctx.add_violation(
                id="missing-footer-landmark",
                severity="minor",
                line=page_line,
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
            ctx.page.h1_count += 1
            if ctx.page.h1_count == 1:
                ctx.page.first_h1_line = line

        if ctx.page.headings_seen:
            prev_level = ctx.page.headings_seen[-1]
            if level > prev_level + 1:
                ctx.add_violation(
                    id="heading-order",
                    severity="moderate",
                    line=line,
                    message=f"Heading level skipped: H{prev_level} → H{level}",
                    fix=f"Use H{prev_level + 1} here, or restructure heading hierarchy to avoid gaps",
                    wcag="1.3.1 Info and Relationships",
                )
        ctx.page.headings_seen.append(level)

    def finalize(self, ctx: ParseContext) -> None:
        if ctx.fragment_mode or not ctx.page.is_full_page or ctx.page.h1_count == 1:
            return
        ctx.add_violation(
            id="heading-single-h1",
            severity="moderate",
            line=ctx.page.first_h1_line,
            message=f"Page has {ctx.page.h1_count} <h1> elements; expected exactly one per page",
            fix="Use a single <h1> for the page title and demote other top-level headings to <h2>",
            wcag="1.3.1 Info and Relationships",
        )


class TableRule(A11yRule):
    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "table":
            ctx.tables.table_depth += 1
            if ctx.tables.table_depth == 1:
                ctx.tables.current_table_has_th = False
                ctx.tables.current_table_has_caption = False
                ctx.tables.current_table_is_presentation = attrs.get_lower("role") == "presentation"
                ctx.tables.current_table_line = line
            return

        if ctx.tables.table_depth <= 0:
            return
        if tag == "th":
            ctx.tables.current_table_has_th = True
        if tag == "caption":
            ctx.tables.current_table_has_caption = True

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag != "table":
            return

        if ctx.tables.table_depth == 1 and not ctx.tables.current_table_is_presentation:
            if not ctx.tables.current_table_has_th:
                ctx.add_violation(
                    id="table-th",
                    severity="serious",
                    line=ctx.tables.current_table_line,
                    message="Data table has no <th> header cells",
                    fix="Add <th scope='col'> for column headers and <th scope='row'> for row headers",
                    wcag="1.3.1 Info and Relationships",
                )
            if not ctx.tables.current_table_has_caption:
                ctx.add_violation(
                    id="table-caption",
                    severity="moderate",
                    line=ctx.tables.current_table_line,
                    message="Table is missing a <caption> describing its purpose",
                    fix="Add <caption>Table description</caption> as first child of <table>",
                    wcag="1.3.1 Info and Relationships",
                )
        ctx.tables.table_depth = max(0, ctx.tables.table_depth - 1)


class LandmarkNestingRule(A11yRule):
    """Nested <main> landmarks / duplicate role='main'."""

    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag != "main" and attrs.get_lower("role") != "main":
            return
        if ctx.page.main_depth > 0:
            ctx.add_violation(
                id="landmark-nesting",
                severity="serious",
                line=line,
                message="<main> landmark nested inside another <main>",
                fix="Use only one <main> per page; use <section> for sub-regions",
                wcag="1.3.1 Info and Relationships",
            )
        ctx.page.main_depth += 1

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag == "main":
            ctx.page.main_depth = max(0, ctx.page.main_depth - 1)


class EmptyHeadingRule(A11yRule):
    """<h1>-<h6> with no text content."""

    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            ctx.page.heading_buffers[line] = {"tag": tag, "text": ""}

    def on_data(self, ctx: ParseContext, data: str) -> None:
        for buf in ctx.page.heading_buffers.values():
            buf["text"] += data

    def finalize(self, ctx: ParseContext) -> None:
        for line, buf in ctx.page.heading_buffers.items():
            if not buf["text"].strip():
                ctx.add_violation(
                    id="empty-heading",
                    severity="moderate",
                    line=line,
                    message=f"<{buf['tag']}> has no text content",
                    fix="Add visible heading text, or aria-label if intentionally hidden",
                    wcag="1.3.1 Info and Relationships",
                )


class ListStructureRule(A11yRule):
    """Three or more consecutive links in bare <div>s (heuristic)."""

    def on_starttag(self, ctx: ParseContext, tag: str, attrs: TagAttrs, line: int) -> None:
        if tag == "a" and ctx.in_tag("div") and not ctx.in_tag(("ul", "ol", "nav")):
            ctx.page.anchor_streak += 1
            if ctx.page.anchor_streak == 3:
                ctx.add_violation(
                    id="list-structure",
                    severity="moderate",
                    line=line,
                    message="Three or more consecutive links in bare <div>s (heuristic) — consider <ul>/<nav>",
                    fix="Wrap navigation links in <ul> or <nav>",
                    wcag="1.3.1 Info and Relationships",
                )
        elif tag in ("div", "p", "section"):
            ctx.page.anchor_streak = 0

    def on_endtag(self, ctx: ParseContext, tag: str) -> None:
        if tag in ("div", "nav", "ul", "ol"):
            ctx.page.anchor_streak = 0