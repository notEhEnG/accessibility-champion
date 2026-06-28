"""Optional axe-core integration via an inline Node.js script."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from a11y_context import Violation

IMPACT_TO_SEVERITY = {
    "critical": "critical",
    "serious": "serious",
    "moderate": "moderate",
    "minor": "minor",
}

# Embedded Node script — requires `npm install axe-core jsdom` (or global equivalents).
AXE_NODE_SCRIPT = r"""
const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");

const htmlPath = process.argv[1];
if (!htmlPath) {
  process.stderr.write("missing html path\n");
  process.exit(2);
}

(async () => {
  let axe, JSDOM;
  try {
    axe = require("axe-core");
    ({ JSDOM } = require("jsdom"));
  } catch (err) {
    process.stderr.write("axe-core or jsdom not installed: " + err.message + "\n");
    process.exit(2);
  }

  const html = fs.readFileSync(htmlPath, "utf8");
  const dom = new JSDOM(html, {
    url: pathToFileURL(path.resolve(htmlPath)).href,
    runScripts: "outside-only",
  });
  dom.window.eval(axe.source);
  const results = await dom.window.axe.run(dom.window.document);
  process.stdout.write(JSON.stringify(results));
})().catch((err) => {
  process.stderr.write(String(err) + "\n");
  process.exit(1);
});
"""


def is_node_available() -> bool:
    return shutil.which("node") is not None


def run_axe(html_path: Path, *, timeout: int = 60) -> dict | None:
    """Run axe-core against a local HTML file. Returns parsed JSON or None on failure."""
    if not is_node_available():
        return None
    proc = subprocess.run(
        ["node", "-e", AXE_NODE_SCRIPT, str(html_path.resolve())],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def map_axe_to_violations(axe_json: dict) -> list[Violation]:
    """Map axe-core JSON to the shared Violation schema."""
    violations: list[Violation] = []
    for item in axe_json.get("violations", []):
        nodes = item.get("nodes") or []
        line = 1
        if nodes and nodes[0].get("html"):
            line = max(1, nodes[0]["html"].count("\n") + 1)
        wcag = ", ".join(t for t in item.get("tags", []) if t.startswith("wcag"))
        violations.append({
            "id": f"axe-{item.get('id', 'unknown')}",
            "severity": IMPACT_TO_SEVERITY.get(item.get("impact", "moderate"), "moderate"),
            "line": line,
            "message": item.get("help", "axe violation"),
            "fix": item.get("helpUrl", ""),
            "wcag": wcag,
        })
    return violations


def dedupe_violations(static: list[Violation], axe: list[Violation]) -> list[Violation]:
    """Merge axe findings into static results, deduplicating by rule id + line."""
    seen = {(v["id"], v["line"]) for v in static}
    merged = list(static)
    for item in axe:
        key = (item["id"], item["line"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return sorted(merged, key=lambda v: v["line"])


def merge_axe_results(
    html_path: Path,
    static_violations: list[Violation],
    *,
    timeout: int = 60,
) -> list[Violation]:
    """Run axe when available; warn and return static-only results otherwise."""
    if not is_node_available():
        print(
            "Warning: Node.js not found — skipping axe-core audit. Install Node.js and "
            "run `npm install axe-core jsdom` for --axe support.",
            file=sys.stderr,
        )
        return static_violations

    raw = run_axe(html_path, timeout=timeout)
    if raw is None:
        print(
            "Warning: axe-core audit failed or dependencies missing. "
            "Install with `npm install axe-core jsdom`. Using static results only.",
            file=sys.stderr,
        )
        return static_violations

    axe_violations = map_axe_to_violations(raw)
    return dedupe_violations(static_violations, axe_violations)