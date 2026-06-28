"""Shared parse context and attribute helpers for the accessibility linter."""

from __future__ import annotations

from dataclasses import dataclass, field


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


def violation(
    *,
    id: str,
    severity: str,
    line: int,
    message: str,
    fix: str,
    wcag: str,
) -> dict:
    return {
        "id": id,
        "severity": severity,
        "line": line,
        "message": message,
        "fix": fix,
        "wcag": wcag,
    }


@dataclass
class ParseContext:
    """Mutable state shared across accessibility rules during HTML parsing."""

    fragment_mode: bool = False
    violations: list[dict] = field(default_factory=list)
    tag_stack: list[str] = field(default_factory=list)

    ids_seen: set[str] = field(default_factory=set)
    duplicate_ids: set[tuple[str, int]] = field(default_factory=set)

    is_full_page: bool = False
    has_main: bool = False
    has_header: bool = False
    has_nav: bool = False
    has_footer: bool = False
    h1_count: int = 0

    headings_seen: list[int] = field(default_factory=list)

    label_fors: set[str] = field(default_factory=set)
    inputs_needing_labels: list[dict] = field(default_factory=list)

    fieldset_stack: list[dict] = field(default_factory=list)
    radio_checkbox_groups: dict[tuple[str, str], dict] = field(default_factory=dict)

    described_by_checks: list[dict] = field(default_factory=list)

    button_depth: int = 0
    current_button: dict | None = None
    in_svg_depth: int = 0
    in_title_depth: int = 0
    current_title_text: str = ""

    link_depth: int = 0
    current_link: dict | None = None

    table_depth: int = 0
    current_table_has_th: bool = False
    current_table_has_caption: bool = False
    current_table_is_presentation: bool = False
    current_table_line: int = 0

    def push_tag(self, tag: str) -> None:
        self.tag_stack.append(tag)

    def pop_tag(self, tag: str) -> None:
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

    def in_tag(self, tag: str) -> bool:
        return tag in self.tag_stack

    def add_violation(self, **kwargs) -> None:
        self.violations.append(violation(**kwargs))

    def track_id(self, id_val: str, line: int) -> None:
        if id_val in self.ids_seen:
            self.duplicate_ids.add((id_val, line))
        self.ids_seen.add(id_val)