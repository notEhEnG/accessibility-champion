"""Phase 3 — external stylesheet resolution (best-effort)."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

PHASE = "3"
LINK_HREF_RE = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)


def fetch_linked_css(html: str, base_url: str | None = None) -> str:
    """Best-effort fetch/resolve linked stylesheets. Missing → empty string, no error."""
    chunks: list[str] = []
    for match in re.finditer(r'<link[^>]+rel=["\']stylesheet["\'][^>]*>', html, re.I):
        href_m = LINK_HREF_RE.search(match.group(0))
        if not href_m:
            continue
        href = href_m.group(1).strip()
        if not href or href.startswith("data:"):
            continue
        text = _resolve_css_href(href, base_url)
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def _resolve_css_href(href: str, base_url: str | None) -> str:
    candidates: list[Path | str] = []
    if base_url:
        if base_url.startswith(("http://", "https://")):
            candidates.append(urljoin(base_url.rstrip("/") + "/", href))
        else:
            candidates.append(Path(base_url) / href)
    if href.startswith(("http://", "https://")):
        candidates.append(href)
    else:
        candidates.append(Path(href))
    for target in candidates:
        if isinstance(target, Path):
            if target.is_file():
                try:
                    return target.read_text(encoding="utf-8")
                except OSError:
                    continue
        else:
            try:
                with urlopen(target, timeout=5) as resp:
                    return resp.read(500_000).decode("utf-8", errors="replace")
            except Exception:
                continue
    return ""