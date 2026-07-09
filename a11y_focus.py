"""Focus-outline checks — delegates to the shared CSS walker in a11y_css (Phase 3)."""

from __future__ import annotations


def check_focus_visible(source: str) -> list[dict]:
    """Scan <style> blocks and inline style attributes for outline suppression
    without a matching :focus-visible / :focus fallback."""
    from a11y_css import find_focus_suppression_rules

    return find_focus_suppression_rules(source)
