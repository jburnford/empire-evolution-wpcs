#!/usr/bin/env python3
"""Sync data/britishempire_kg_export.cypher with data/qid_manifest.tsv.

This is a full bidirectional reconciliation:
  - DELETE Cypher MERGE blocks whose colony_id is not in the TSV
    (e.g. Pass D row deletions).
  - UPDATE wikidata_id, successor_dominion, canonical_name, name on each
    Cypher block to match the TSV.
  - UPDATE qid_scope_note: add if non-empty and missing, replace if content
    differs, remove if TSV now has empty note.
  - APPEND new MERGE blocks for TSV rows not yet in Cypher
    (e.g. sind_province_1936_1947).

Renames (old colony_id → new colony_id) are applied first so block lookup
can use the post-rename id.
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

# Old colony_id (in current Cypher) → new colony_id (in updated TSV).
# Applied to the Cypher file BEFORE block-by-block reconciliation, so the
# downstream lookup uses the post-rename id.
RENAMES = {
    "sind_province_1843_1947": "sind_division_bombay_1843_1936",
}

# Explicit set of colony_ids to delete from Cypher. Use this for Pass D
# row removals. Blocks not in TSV but not in this set are KEPT as-is —
# the Cypher includes Cypher-only territory blocks that lack a wikidata_id
# (e.g. java_british_occupation_1811_1816) and shouldn't be auto-deleted.
DELETIONS = {
    "dedhrota",
    "khaniyadhana",
    "lunavada",
    "marwar",
    "princely_states_placeholder_1818_1947",
}

# Fields we keep in sync from TSV → Cypher per block.
SYNC_FIELDS = ["wikidata_id", "successor_dominion", "canonical_name", "name"]

def load_tsv() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    with TSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            out[row["colony_id"]] = row
    return out

def cypher_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")

def update_field(block: str, field: str, new_value: str) -> str:
    """Replace `field: '...'` with `field: 'new_value'` in block (first occurrence)."""
    if not new_value:
        # TSV value empty: leave any existing Cypher value as-is. Cypher may have
        # historical info the TSV doesn't track (e.g. some rows have empty
        # canonical_name in TSV but populated name in Cypher).
        return block
    pattern = re.compile(rf"({re.escape(field)}:\s*)'[^']*'")
    if pattern.search(block):
        return pattern.sub(lambda m: f"{m.group(1)}'{cypher_escape(new_value)}'", block, count=1)
    return block

def sync_scope_note(block: str, note: str) -> str:
    """Add / update / remove qid_scope_note property to match TSV.

    Implemented by removing the existing qid_scope_note line entirely (more
    robust than regex-replacing the value, which fails on Cypher-escaped
    quotes like \\'), then re-inserting the new note if non-empty.
    """
    lines = block.split("\n")
    # Strip any existing qid_scope_note line(s).
    cleaned_lines = [ln for ln in lines if "qid_scope_note:" not in ln]
    # If we removed a line, the line before may now have a trailing comma
    # that needs to stay valid Cypher. Cypher does NOT allow trailing commas
    # in property maps, so trim a trailing comma if the next non-stripped
    # line is the closing brace.
    for i in range(len(cleaned_lines) - 1):
        nxt = cleaned_lines[i + 1].strip()
        if nxt.startswith("}"):
            # Previous line ends the property list; trim trailing comma.
            cleaned_lines[i] = re.sub(r",\s*$", "", cleaned_lines[i])

    if not note.strip():
        return "\n".join(cleaned_lines)

    # Insert new note as last property before the closing brace.
    escaped = cypher_escape(note)
    brace_idx = None
    for i in range(len(cleaned_lines) - 1, -1, -1):
        if re.match(r"^\s*\}\s*;?\s*$", cleaned_lines[i]):
            brace_idx = i
            break
    if brace_idx is not None and brace_idx > 0:
        prev = cleaned_lines[brace_idx - 1]
        if not prev.rstrip().endswith(","):
            cleaned_lines[brace_idx - 1] = prev.rstrip() + ","
        cleaned_lines.insert(brace_idx, f"  qid_scope_note: '{escaped}'")
    return "\n".join(cleaned_lines)

def update_block(block: str, cid: str, tsv: dict[str, dict[str, str]]) -> str:
    row = tsv[cid]
    for field in SYNC_FIELDS:
        block = update_field(block, field, row.get(field, ""))
    # Also sync canonical_name → Cypher's `name` field where the TSV
    # canonical_name disambiguates (e.g. Udaipur State (Mewar)) and the
    # Cypher's name field is the un-disambiguated form.
    canon = row.get("canonical_name", "").strip()
    if canon and "(" in canon:
        # Disambiguation hint present in canonical_name; mirror to `name`.
        block = update_field(block, "name", canon)
    return sync_scope_note(block, row.get("qid_scope_note", ""))

def render_new_block(row: dict[str, str], label_suffix: str = "Province") -> str:
    """Render a new MERGE block for a row that doesn't exist in Cypher yet."""
    cid = row["colony_id"]
    lines = [
        "",
        f"MERGE (c:HistoricalTerritory:{label_suffix} {{colony_id: '{cid}'}})",
        "SET c += {",
    ]
    # Required-ish fields
    fields_to_include = [
        ("canonical_name", row["canonical_name"]),
        ("capital", row["capital"]),
        ("colony_id", cid),
        ("colony_type", row["colony_type"]),
        ("end_date", row["end_date"]),
        ("modern_nation_qids", row["modern_nation_qids"]),
        ("region", row["region"]),
        ("successor_dominion", row["successor_dominion"]),
        ("qid_scope_note", row["qid_scope_note"]),
    ]
    props = []
    for k, v in fields_to_include:
        v = (v or "").strip()
        if not v:
            continue
        if k == "modern_nation_qids":
            # Render as list literal
            props.append(f"  {k}: ['{cypher_escape(v)}']")
        else:
            props.append(f"  {k}: '{cypher_escape(v)}'")
    # established_year is integer
    if row.get("established_year"):
        props.append(f"  established_year: {row['established_year']}")
    # wikidata_id last (matches existing style)
    if row["wikidata_id"]:
        props.append(f"  wikidata_id: '{row['wikidata_id']}'")
    # Add commas (all but last)
    for i in range(len(props) - 1):
        props[i] = props[i] + ","
    lines.extend(props)
    lines.append("};")
    return "\n".join(lines)

def main() -> int:
    tsv = load_tsv()
    cypher_text = CYPHER.read_text(encoding="utf-8")

    # Apply renames
    for old, new in RENAMES.items():
        cypher_text = re.sub(
            rf"(MERGE \(c:[^)]*\{{colony_id:\s*)'{re.escape(old)}'(\}}\))",
            rf"\1'{new}'\2",
            cypher_text,
        )
        cypher_text = cypher_text.replace(
            f"colony_id: '{old}'", f"colony_id: '{new}'"
        )

    # Walk block-by-block
    out_lines: list[str] = []
    lines = cypher_text.split("\n")
    cypher_block_cids: set[str] = set()
    i = 0
    blocks_kept = 0
    blocks_deleted = 0
    while i < len(lines):
        line = lines[i]
        m = MERGE_RE.match(line)
        if m:
            cid = m.group(1)
            block_lines = [line]
            i += 1
            while i < len(lines):
                block_lines.append(lines[i])
                if re.match(r"^\s*\}\s*;\s*$", lines[i]):
                    i += 1
                    break
                i += 1
            block = "\n".join(block_lines)
            if cid in DELETIONS:
                # Explicit Pass D deletion.
                blocks_deleted += 1
            elif cid in tsv:
                new_block = update_block(block, cid, tsv)
                out_lines.append(new_block)
                cypher_block_cids.add(cid)
                blocks_kept += 1
            else:
                # Cypher-only block without a TSV row (e.g. territories
                # without a wikidata_id). Keep unchanged.
                out_lines.append(block)
                blocks_kept += 1
        else:
            out_lines.append(line)
            i += 1

    print(f"Blocks kept/updated: {blocks_kept}, deleted: {blocks_deleted}", file=sys.stderr)

    # Append any TSV rows that aren't in the Cypher yet
    missing_in_cypher = [
        cid for cid in tsv
        if cid not in cypher_block_cids
    ]
    for cid in missing_in_cypher:
        new_block = render_new_block(tsv[cid])
        out_lines.append(new_block)
        print(f"Appended new MERGE block for {cid}", file=sys.stderr)

    CYPHER.write_text("\n".join(out_lines), encoding="utf-8")
    return 0

if __name__ == "__main__":
    sys.exit(main())
