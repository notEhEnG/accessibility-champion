#!/usr/bin/env python3
"""CI gate: fail if any a11y module exceeds MAX_LINES."""
from __future__ import annotations

import sys
from pathlib import Path

MAX_LINES = 400
ROOT = Path(__file__).resolve().parents[1]
TARGETS = list(ROOT.glob("a11y_*.py")) + list((ROOT / "a11y_rules").glob("*.py"))


def main() -> int:
    failed = False
    for path in sorted(TARGETS):
        if path.name == "__init__.py":
            continue
        count = len(path.read_text(encoding="utf-8").splitlines())
        if count > MAX_LINES:
            print(f"FAIL {path.relative_to(ROOT)}: {count} lines (max {MAX_LINES})")
            failed = True
        else:
            print(f"ok   {path.relative_to(ROOT)}: {count}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
