#!/usr/bin/env python3
"""Patch the 14 stale Wikidata QIDs in viz/empire_evolution.html.

The viz is a self-contained hand-curated D3.js Sankey with an embedded JS
data array. After Phase 2 QID corrections, 14 of its 58 QIDs no longer
match the corrected TSV. This script applies the same swaps to the viz
file. For the Sind row, which was split in Pass C, the viz's existing
entry (est: 1936) maps to the post-split Sind Province (Q7522091), so the
id is also updated to 'sind_province_1936_1947'.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

VIZ = Path(__file__).resolve().parent.parent / "viz" / "empire_evolution.html"

QID_SWAPS: list[tuple[str, str]] = [
    ("Q1143638",  "Q2032545"),    # Red River Colony
    ("Q1553529",  "Q107987587"),  # Bay Islands
    ("Q173095",   "Q52636"),      # Minorca (3 occurrences)
    ("Q179876",   "Q215530"),     # Kingdom of Ireland
    ("Q1948981",  "Q6037274"),    # Mosquito Coast → Mosquitia
    ("Q2199929",  "Q1368792"),    # Essequibo
    ("Q2259576",  "Q83536"),      # Anglo-Corsican Kingdom
    ("Q2399707",  "Q1185346"),    # Demerara
    ("Q3104",     "Q3129772"),    # Heligoland (island)
    ("Q4700553",  "Q412980"),     # Ajmer-Merwara
    ("Q48378",    "Q38610"),      # Newfoundland Commission → Dominion of Newfoundland
    ("Q861922",   "Q675322"),     # Berbice
    ("Q864930",   "Q24905912"),   # Coorg Province
    ("Q7523949",  "Q7522091"),    # Sind (was sind_province_1843_1947 with est:1936; now sind_province_1936_1947)
]

# Additional id rename for Sind to match TSV's new row
ID_RENAMES: list[tuple[str, str]] = [
    ("'sind_province_1843_1947'", "'sind_province_1936_1947'"),
]

def main() -> int:
    text = VIZ.read_text(encoding="utf-8")
    summary = []
    for old, new in QID_SWAPS:
        # Match qid: 'OLD' exactly (with optional whitespace)
        pattern = re.compile(rf"qid:\s*'{re.escape(old)}'")
        n = len(pattern.findall(text))
        if n == 0:
            print(f"WARN: {old} not found in viz", file=sys.stderr)
            continue
        text = pattern.sub(f"qid: '{new}'", text)
        summary.append((old, new, n))
        print(f"  {old} -> {new} ({n} replacement{'s' if n != 1 else ''})")

    for old, new in ID_RENAMES:
        n = text.count(old)
        if n == 0:
            print(f"WARN: id rename {old} not found", file=sys.stderr)
            continue
        text = text.replace(old, new)
        print(f"  id rename {old} -> {new} ({n})")

    VIZ.write_text(text, encoding="utf-8")
    print(f"Applied {len(summary)} QID swaps", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
