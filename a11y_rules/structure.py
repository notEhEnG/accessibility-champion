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
            line=ctx.page_line(),
            message=f"Page has {ctx.page.h1_count} <h1> elements; expected exactly one per page",
            fix="Use a single <h1> for the page title and demote other top-level headings to <h2>",
            wcag="1.3.1 Info and Relationships",
        )


class SkipLinkRule(A11yRule):
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