#!/usr/bin/env python3
"""Strip centroid coordinate properties from britishempire_kg_export.cypher.

Removes: latitude, longitude, location, coordinates_source, spatial_updated.
Operates in-place. Safe against trailing-comma syntax errors because the
file's territory blocks never end with one of these properties (verified).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

STRIP_PROPS = {"latitude", "longitude", "location", "coordinates_source", "spatial_updated"}
STRIP_RE = re.compile(r"^  (" + "|".join(STRIP_PROPS) + r"):")


def strip(path: Path) -> tuple[int, dict[str, int]]:
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    kept: list[str] = []
    counts: dict[str, int] = {p: 0 for p in STRIP_PROPS}
    for line in lines:
        m = STRIP_RE.match(line)
        if m:
            counts[m.group(1)] += 1
            continue
        kept.append(line)
    path.write_text("".join(kept))
    return len(lines) - len(kept), counts


def main() -> int:
    path = Path(__file__).resolve().parent.parent / "data" / "britishempire_kg_export.cypher"
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        return 1
    removed, counts = strip(path)
    print(f"stripped {removed} lines from {path}")
    for prop, n in sorted(counts.items()):
        print(f"  {prop}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
