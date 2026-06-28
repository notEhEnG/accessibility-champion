"""Accessibility rules package."""

from __future__ import annotations

from a11y_rules.base import A11yRule
from a11y_rules.document import DocumentRule, DocumentTitleRule
from a11y_rules.structure import LandmarkRule, HeadingRule, TableRule
from a11y_rules.content import ImageRule, FrameRule
from a11y_rules.forms import (
    FormLabelRule,
    PlaceholderRule,
    AutocompleteRule,
    FormGroupRule,
    ButtonTypeRule,
)
from a11y_rules.aria import AriaReferenceRule, DuplicateIdRule
from a11y_rules.links import SkipLinkRule, TargetBlankRule, LinkNameRule
from a11y_rules.media import MediaRule, AudioTranscriptRule
from a11y_rules.interactive import ButtonNameRule, TabIndexRule


def all_rules() -> list[A11yRule]:
    """Return an ordered list of all accessibility rule instances to execute."""
    return [
        DocumentRule(),
        DocumentTitleRule(),
        LandmarkRule(),
        SkipLinkRule(),
        HeadingRule(),
        ImageRule(),
        FormLabelRule(),
        PlaceholderRule(),
        AutocompleteRule(),
        FormGroupRule(),
        AriaReferenceRule(),
        ButtonNameRule(),
        ButtonTypeRule(),
        TargetBlankRule(),
        LinkNameRule(),
        TableRule(),
        MediaRule(),
        AudioTranscriptRule(),
        FrameRule(),
        TabIndexRule(),
        DuplicateIdRule(),
    ]
