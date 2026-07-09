"""Phase 2 — extract HTML from framework templates for linting."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from a11y_mapping import ExtractMap, LineMapping

PHASE = "2"


@dataclass
class ExtractResult:
    source_file: str
    html: str
    mappings: list[LineMapping] = field(default_factory=list)
    fragment: bool = True
    phase: str = PHASE


class HtmlPassthrough:
    extensions = frozenset({".html", ".htm"})

    def extract(self, source: str, path: str) -> ExtractResult:
        lines = source.splitlines()
        mappings = [
            LineMapping(extracted_line=i + 1, source_line=i + 1)
            for i in range(len(lines))
        ]
        fragment = not re.search(r"<(?:html|body)\b", source, re.IGNORECASE)
        return ExtractResult(path, source, mappings, fragment)


class VueExtractor:
    extensions = frozenset({".vue"})

    def extract(self, source: str, path: str) -> ExtractResult:
        match = re.search(r"<template[^>]*>(.*?)</template>", source, re.DOTALL | re.IGNORECASE)
        if not match:
            return ExtractResult(path, source, [], True)
        inner = match.group(1)
        start_line = source[: match.start(1)].count("\n") + 1
        mappings = []
        for i, _ in enumerate(inner.splitlines()):
            mappings.append(LineMapping(extracted_line=i + 1, source_line=start_line + i))
        return ExtractResult(path, inner.strip(), mappings, True)


class TsxExtractor:
    extensions = frozenset({".tsx", ".jsx"})

    def extract(self, source: str, path: str) -> ExtractResult:
        """Phase 2 MVP: first JSX return block as HTML-ish snippet."""
        match = re.search(r"return\s*\(\s*(.*?)\s*\)\s*;?", source, re.DOTALL)
        if not match:
            return ExtractResult(path, "", [], True)
        block = match.group(1)
        start_line = source[: match.start(1)].count("\n") + 1
        mappings = []
        for i, line in enumerate(block.splitlines()):
            tag_m = re.search(r"<(\w+)", line)
            mappings.append(LineMapping(
                extracted_line=i + 1,
                source_line=start_line + i,
                tag=tag_m.group(1) if tag_m else None,
            ))
        return ExtractResult(path, block.strip(), mappings, True)


class SvelteExtractor:
    extensions = frozenset({".svelte"})

    def extract(self, source: str, path: str) -> ExtractResult:
        cleaned = re.sub(r"<script[^>]*>.*?</script>", "", source, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        mappings = [
            LineMapping(extracted_line=i + 1, source_line=i + 1)
            for i in range(len(cleaned.splitlines()))
        ]
        return ExtractResult(path, cleaned.strip(), mappings, True)


class AngularExtractor:
    extensions = frozenset({".component.html"})

    def extract(self, source: str, path: str) -> ExtractResult:
        passthrough = HtmlPassthrough()
        result = passthrough.extract(source, path)
        result.fragment = True
        return result


_EXTRACTORS = [
    HtmlPassthrough(),
    VueExtractor(),
    TsxExtractor(),
    SvelteExtractor(),
    AngularExtractor(),
]


def detect_extractor(path: Path):
    """Return extractor for path extension, or None."""
    ext = path.suffix.lower()
    if path.name.endswith(".component.html"):
        return AngularExtractor()
    for ex in _EXTRACTORS:
        if ext in ex.extensions:
            return ex
    return None


def detect_format(path: Path):
    """ARCHITECTURE alias for detect_extractor."""
    return detect_extractor(path)


def extract_file(path: Path) -> ExtractResult:
    source = path.read_text(encoding="utf-8")
    extractor = detect_extractor(path)
    if extractor is None:
        raise ValueError(f"[Phase {PHASE}] Unsupported format: {path}")
    return extractor.extract(source, str(path))


def write_sidecar(result: ExtractResult, out: Path | None = None) -> Path:
    out = out or Path(f"{result.source_file}.extract-map.json")
    ExtractMap(
        source_file=result.source_file,
        extracted_file=f"{result.source_file}.extracted.html",
        fragment=result.fragment,
        mappings=result.mappings,
    ).write(out)
    return out