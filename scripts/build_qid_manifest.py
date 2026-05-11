#!/usr/bin/env python3
"""Build a working manifest of (colony_id, name, qid, ...) sorted alphabetically.

Output: data/qid_manifest.tsv — one row per territory that has a wikidata_id.
This is the work queue Opus iterates through with MCP lookups.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

PROP_RE = re.compile(r"^  ([a-z_]+):\s*(.*?),?\s*$")
MERGE_RE = re.compile(r"^MERGE \(c:HistoricalTerritory[^)]*\{colony_id:\s*'([^']+)'\}\)")


def parse_str(s: str) -> str:
    s = s.strip().rstrip(",").strip()
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        return s[1:-1]
    return s


def parse_str_list(s: str) -> str:
    s = s.strip().rstrip(",").strip()
    if not (s.startswith("[") and s.endswith("]")):
        return ""
    inner = s[1:-1].strip()
    if not inner:
        return ""
    return ";".join(parse_str(x) for x in inner.split(","))


def parse(path: Path) -> list[dict]:
    rows: list[dict] = []
    cur: dict | None = None
    in_block = False
    for line in path.read_text().splitlines():
        m = MERGE_RE.match(line)
        if m:
            cur = {"colony_id": m.group(1), "name": "", "canonical_name": "",
                   "wikidata_id": "", "modern_nation_qids": "",
                   "established_year": "", "end_date": "", "region": "",
                   "colony_type": "", "capital": "", "successor_dominion": ""}
            in_block = True
            continue
        if not in_block or cur is None:
            continue
        if line.startswith("};"):
            if cur.get("wikidata_id"):
                rows.append(cur)
            cur = None
            in_block = False
            continue
        pm = PROP_RE.match(line)
        if not pm:
            continue
        key, val = pm.group(1), pm.group(2)
        if key == "modern_nation_qids":
            cur["modern_nation_qids"] = parse_str_list(val)
        elif key in cur:
            cur[key] = parse_str(val)
    rows.sort(key=lambda r: r["colony_id"])
    return rows


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    src = root / "data" / "britishempire_kg_export.cypher"
    out = root / "data" / "qid_manifest.tsv"
    rows = parse(src)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
