#!/usr/bin/env python3
"""Sync data/britishempire_kg_export.cypher with corrected data/qid_manifest.tsv.

For each MERGE block in the Cypher file, look up the colony_id in the TSV and:
  1. Update wikidata_id if it differs (Pass A/B/C QID swaps).
  2. Update successor_dominion if it differs (Pass A2 india→pakistan).
  3. Inject qid_scope_note property if the TSV row has one (Pass E).
  4. Rename colony_id 'sind_province_1843_1947' → 'sind_division_bombay_1843_1936'
     (and apply its other field updates).
  5. Append a new MERGE block for the new sind_province_1936_1947 row.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TSV = REPO / "data" / "qid_manifest.tsv"
CYPHER = REPO / "data" / "britishempire_kg_export.cypher"

MERGE_RE = re.compile(r"^MERGE \(c:[^)]*\{colony_id:\s*'([^']+)'\}\)")

# Old colony_id (in current Cypher) → new colony_id (in updated TSV)
RENAMES = {
    "sind_province_1843_1947": "sind_division_bombay_1843_1936",
}

def load_tsv() -> dict[str, dict[str, str]]:
    """Return {colony_id: {wikidata_id, successor_dominion, qid_scope_note, ...}}."""
    out: dict[str, dict[str, str]] = {}
    with TSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            out[row["colony_id"]] = row
    return out

def cypher_escape(s: str) -> str:
    """Escape single quotes for Cypher string literal."""
    return s.replace("\\", "\\\\").replace("'", "\\'")

def update_block(block: str, target_cid: str, tsv: dict[str, dict[str, str]]) -> str:
    """Apply TSV-driven updates to one MERGE block string."""
    # Determine target row
    if target_cid in tsv:
        row = tsv[target_cid]
    else:
        return block  # no TSV row found; leave block unchanged

    new_qid = row["wikidata_id"]
    new_succ = row["successor_dominion"]
    new_note = row.get("qid_scope_note", "")

    # 1. Update wikidata_id line
    block = re.sub(
        r"(wikidata_id:\s*)'[^']*'",
        lambda m: f"{m.group(1)}'{new_qid}'" if new_qid else m.group(0),
        block,
        count=1,
    )

    # 2. Update successor_dominion line (only if it exists in current block AND TSV value differs)
    if "successor_dominion:" in block:
        if new_succ:
            block = re.sub(
                r"(successor_dominion:\s*)'[^']*'",
                lambda m: f"{m.group(1)}'{cypher_escape(new_succ)}'",
                block,
                count=1,
            )

    # 3. Inject qid_scope_note property if non-empty and not already present
    if new_note and "qid_scope_note:" not in block:
        # Insert before the closing '};' line, alphabetically positioned
        # (the SET block keys are alphabetical). Insert just before 'region:' or
        # at end of property list — simplest: insert just before the closing brace.
        # Using a careful regex: locate the last property line before "};" or "}".
        escaped = cypher_escape(new_note)
        # Find the line immediately before the closing brace.
        lines = block.split("\n")
        # Find closing brace line (looks like "};" possibly with whitespace)
        brace_idx = None
        for i in range(len(lines) - 1, -1, -1):
            if re.match(r"^\s*\}\s*;?\s*$", lines[i]):
                brace_idx = i
                break
        if brace_idx is not None and brace_idx > 0:
            # Add comma to the line before, then insert our line
            prev = lines[brace_idx - 1]
            if not prev.rstrip().endswith(","):
                lines[brace_idx - 1] = prev.rstrip() + ","
            lines.insert(brace_idx, f"  qid_scope_note: '{escaped}'")
            block = "\n".join(lines)

    return block

def main() -> int:
    tsv = load_tsv()
    cypher_text = CYPHER.read_text(encoding="utf-8")

    # Apply renames in MERGE-line and inside-block colony_id property
    for old, new in RENAMES.items():
        # Replace MERGE line colony_id
        cypher_text = re.sub(
            rf"(MERGE \(c:[^)]*\{{colony_id:\s*)'{re.escape(old)}'(\}}\))",
            rf"\1'{new}'\2",
            cypher_text,
        )
        # Replace inside-SET colony_id property
        cypher_text = cypher_text.replace(
            f"colony_id: '{old}'", f"colony_id: '{new}'"
        )

    # Now process block-by-block
    # A territory MERGE block ends at the first line starting with "};"
    # Strategy: split on lines, walk forward, accumulate blocks
    out_lines: list[str] = []
    lines = cypher_text.split("\n")
    i = 0
    blocks_processed = 0
    while i < len(lines):
        line = lines[i]
        m = MERGE_RE.match(line)
        if m:
            cid = m.group(1)
            # Collect block until a line == "};" (with trailing whitespace tolerated)
            block_lines = [line]
            i += 1
            while i < len(lines):
                block_lines.append(lines[i])
                if re.match(r"^\s*\}\s*;\s*$", lines[i]):
                    i += 1
                    break
                i += 1
            block = "\n".join(block_lines)
            new_block = update_block(block, cid, tsv)
            out_lines.append(new_block)
            blocks_processed += 1
        else:
            out_lines.append(line)
            i += 1

    print(f"Processed {blocks_processed} MERGE blocks", file=sys.stderr)

    # Append new MERGE block for sind_province_1936_1947
    sind_new_cid = "sind_province_1936_1947"
    if sind_new_cid in tsv and f"colony_id: '{sind_new_cid}'" not in cypher_text:
        row = tsv[sind_new_cid]
        scope_note = row.get("qid_scope_note", "")
        new_block_lines = [
            "",
            f"MERGE (c:HistoricalTerritory:Province {{colony_id: '{sind_new_cid}'}})",
            "SET c += {",
            f"  canonical_name: '{cypher_escape(row['canonical_name'])}',",
            f"  capital: '{cypher_escape(row['capital'])}',",
            f"  colony_id: '{sind_new_cid}',",
            f"  colony_type: '{cypher_escape(row['colony_type'])}',",
            f"  end_date: '{cypher_escape(row['end_date'])}',",
            f"  established_year: {row['established_year']},",
            f"  modern_nation_qids: ['{cypher_escape(row['modern_nation_qids'])}'],",
            f"  region: '{cypher_escape(row['region'])}',",
            f"  successor_dominion: '{cypher_escape(row['successor_dominion'])}',",
        ]
        if scope_note:
            new_block_lines.append(f"  qid_scope_note: '{cypher_escape(scope_note)}',")
        new_block_lines.append(f"  wikidata_id: '{row['wikidata_id']}'")
        new_block_lines.append("};")
        out_lines.extend(new_block_lines)
        print(f"Appended new MERGE block for {sind_new_cid}", file=sys.stderr)

    CYPHER.write_text("\n".join(out_lines), encoding="utf-8")
    return 0

if __name__ == "__main__":
    sys.exit(main())
