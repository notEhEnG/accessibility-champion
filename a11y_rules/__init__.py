"""Accessibility rules package."""

from __future__ import annotations

from a11y_rules.base import A11yRule
from a11y_rules.document import DocumentRule, DocumentTitleRule, LangSubtagRule
from a11y_rules.structure import (
    LandmarkRule,
    HeadingRule,
    TableRule,
    LandmarkNestingRule,
    EmptyHeadingRule,
    ListStructureRule,
)
from a11y_rules.content import ImageRule, FrameRule, DecorativeImgRoleRule
from a11y_rules.forms import (
    FormLabelRule,
    PlaceholderRule,
    AutocompleteRule,
    FormGroupRule,
    ButtonTypeRule,
    RequiredIndicatorRule,
    SelectEmptyLabelRule,
)
from a11y_rules.aria import (
    AriaReferenceRule,
    DuplicateIdRule,
    AriaHiddenFocusableRule,
    RedundantRoleRule,
)
from a11y_rules.links import (
    SkipLinkRule,
    TargetBlankRule,
    LinkNameRule,
    EmptyLinkRule,
    FilenameLinkTextRule,
)
from a11y_rules.media import MediaRule, AudioTranscriptRule
from a11y_rules.interactive import ButtonNameRule, TabIndexRule


def all_rules() -> list[A11yRule]:
    """Return an ordered list of all accessibility rule instances to execute."""
    return [
        DocumentRule(),
        DocumentTitleRule(),
        LandmarkRule(),
        LandmarkNestingRule(),
        SkipLinkRule(),
        HeadingRule(),
        EmptyHeadingRule(),
        ImageRule(),
        DecorativeImgRoleRule(),
        FormLabelRule(),
        PlaceholderRule(),
        AutocompleteRule(),
        FormGroupRule(),
        RequiredIndicatorRule(),
        SelectEmptyLabelRule(),
        AriaReferenceRule(),
        AriaHiddenFocusableRule(),
        RedundantRoleRule(),
        ButtonNameRule(),
        ButtonTypeRule(),
        TargetBlankRule(),
        # EmptyLink/FilenameLinkText run before LinkNameRule so per-link state is intact.
        EmptyLinkRule(),
        FilenameLinkTextRule(),
        LinkNameRule(),
        ListStructureRule(),
        TableRule(),
        MediaRule(),
        AudioTranscriptRule(),
        FrameRule(),
        TabIndexRule(),
        DuplicateIdRule(),
        LangSubtagRule(),
    ]
