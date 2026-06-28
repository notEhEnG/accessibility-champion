"""Shared parse context, violation model, and attribute helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict


class Violation(TypedDict):
    id: str
    severity: str
    line: int
    message: str
    fix: str
    wcag: str


@dataclass
class TagAttrs:
    """HTML attributes with case-preserving values."""

    raw: dict[str, str]

    @classmethod
    def from_parser(cls, attrs: list[tuple[str, str | None]]) -> TagAttrs:
        return cls({k: v if v is not None else "" for k, v in attrs})

    def get(self, name: str) -> str | None:
        target = name.lower()
        for key, value in self.raw.items():
            if key.lower() == target:
                return value
        return None

    def has(self, name: str) -> bool:
        return self.get(name) is not None

    def get_lower(self, name: str) -> str | None:
        value = self.get(name)
        return value.lower() if value else None


def make_violation(
    *,
    id: str,
    severity: str,
    line: int,
    message: str,
    fix: str,
    wcag: str,
) -> Violation:
    return Violation(
        id=id,
        severity=severity,
        line=line,
        message=message,
        fix=fix,
        wcag=wcag,
    )


@dataclass
class PageState:
    is_full_page: bool = False
    has_main: bool = False
    has_header: bool = False
    has_nav: bool = False
    has_footer: bool = False
    h1_count: int = 0
    headings_seen: list[int] = field(default_factory=list)
    head_depth: int = 0
    document_title_depth: int = 0
    document_title: str = ""
    has_skip_link: bool = False
    html_line: int = 1
    nav_line: int = 1
    head_line: int = 1


@dataclass
class FormState:
    label_fors: set[str] = field(default_factory=set)
    inputs_needing_labels: list[dict] = field(default_factory=list)
    placeholder_controls: list[dict] = field(default_factory=list)
    fieldset_stack: list[dict] = field(default_factory=list)
    radio_checkbox_groups: dict[tuple[str, str], dict] = field(default_factory=dict)
    form_depth: int = 0


@dataclass
class AudioEntry:
    line: int
    offset: int


@dataclass
class MediaState:
    video_depth: int = 0
    current_video: dict | None = None
    audio_entries: list[AudioEntry] = field(default_factory=list)


@dataclass
class LinkState:
    link_depth: int = 0
    current_link: dict | None = None


@dataclass
class ButtonState:
    button_depth: int = 0
    current_button: dict | None = None
    in_svg_depth: int = 0
    in_title_depth: int = 0
    current_title_text: str = ""


@dataclass
class TableState:
    table_depth: int = 0
    current_table_has_th: bool = False
    current_table_has_caption: bool = False
    current_table_is_presentation: bool = False
    current_table_line: int = 0


@dataclass
class AriaState:
    ids_seen: set[str] = field(default_factory=set)
    duplicate_ids: set[tuple[str, int]] = field(default_factory=set)
    described_by_checks: list[dict] = field(default_factory=list)
    labelled_by_checks: list[dict] = field(default_factory=list)
    aria_invalid_checks: list[dict] = field(default_factory=list)


@dataclass
class ParseContext:
    """Mutable state shared across accessibility rules during HTML parsing."""

    source: str = ""
    fragment_mode: bool = False
    violations: list[Violation] = field(default_factory=list)
    tag_stack: list[str] = field(default_factory=list)
    page: PageState = field(default_factory=PageState)
    forms: FormState = field(default_factory=FormState)
    media: MediaState = field(default_factory=MediaState)
    links: LinkState = field(default_factory=LinkState)
    buttons: ButtonState = field(default_factory=ButtonState)
    tables: TableState = field(default_factory=TableState)
    aria: AriaState = field(default_factory=AriaState)

    def push_tag(self, tag: str) -> None:
        self.tag_stack.append(tag)

    def pop_tag(self, tag: str) -> None:
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

    def in_tag(self, tag: str) -> bool:
        return tag in self.tag_stack

    def add_violation(self, **kwargs: str | int) -> None:
        self.violations.append(make_violation(**kwargs))  # type: ignore[arg-type]

    def track_id(self, id_val: str, line: int) -> None:
        if id_val in self.aria.ids_seen:
            self.aria.duplicate_ids.add((id_val, line))
        self.aria.ids_seen.add(id_val)

    def page_line(self, fallback: int = 1) -> int:
        """Best line number for page-level violations."""
        return self.page.html_line or fallback