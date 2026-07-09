"""Phase 2 — extract line mapping and sidecar JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

PHASE = "2"
SIDECAR_VERSION = 1


@dataclass
class LineMapping:
    extracted_line: int
    source_line: int
    tag: str | None = None


@dataclass
class ExtractMap:
    """Phase 2 sidecar schema."""

    source_file: str
    extracted_file: str
    fragment: bool
    mappings: list[LineMapping] = field(default_factory=list)
    phase: str = PHASE
    version: int = SIDECAR_VERSION

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "phase": self.phase,
            "sourceFile": self.source_file,
            "extractedFile": self.extracted_file,
            "fragment": self.fragment,
            "mappings": [asdict(m) for m in self.mappings],
        }

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


def remap_line(line: int, mappings: list[LineMapping]) -> int:
    """Map extracted HTML line → original source line."""
    for m in mappings:
        if m.extracted_line == line:
            return m.source_line
    best = max((m for m in mappings if m.extracted_line <= line), key=lambda x: x.extracted_line, default=None)
    if best:
        return best.source_line + (line - best.extracted_line)
    return line


def remap_violations(violations: list[dict], mappings: list[LineMapping], source_file: str) -> list[dict]:
    out = []
    for v in violations:
        item = dict(v)
        item["line"] = remap_line(v["line"], mappings)
        item["file"] = source_file
        item["phase"] = PHASE
        out.append(item)
    return out