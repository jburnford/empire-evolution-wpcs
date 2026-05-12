#!/usr/bin/env python3
"""Pass D: resolve POSSIBLE_FILE_DUPLICATE and PLACEHOLDER_NOT_ENTITY rows.

User decisions:
  - Dedhrota: merge — keep dedhrota_1900_1947 (Q11916768), delete 'dedhrota'.
  - Khaniyadhana: merge — keep khaniadhana_state_1724_1948 (Q16852121),
    delete 'khaniyadhana'.
  - Lunavada: merge — keep lunavada_state_1434_1948 (Q18127558),
    delete 'lunavada'.
  - Marwar/Jodhpur: merge — keep jodhpur_state_1226_1949 (Q6207845),
    delete 'marwar'.
  - Udaipur: keep both — they are TWO DIFFERENT places sharing the name
    (Mewar/Rajasthan vs Chhattisgarh). Update canonical_name to
    disambiguate; rewrite scope notes accordingly.
  - princely_states_placeholder_1818_1947: delete (meta-placeholder, not
    a real territorial entity).

Also clears the now-obsolete POSSIBLE_FILE_DUPLICATE scope notes on the
4 kept-after-merge rows.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TSV = REPO / "data" / "qid_manifest.tsv"

ROWS_TO_DELETE = {
    "dedhrota",
    "khaniyadhana",
    "lunavada",
    "marwar",
    "princely_states_placeholder_1818_1947",
}

# For the 4 kept-after-merge rows, clear the obsolete POSSIBLE_FILE_DUPLICATE note.
CLEAR_SCOPE_NOTES = {
    "dedhrota_1900_1947",
    "khaniadhana_state_1724_1948",
    "lunavada_state_1434_1948",
    "jodhpur_state_1226_1949",
}

# Udaipur disambiguation: keep both rows; update canonical_name + scope_note.
UDAIPUR_UPDATES = {
    "udaipur_state": {
        "canonical_name": "Udaipur State (Mewar)",
        "qid_scope_note": (
            "Q130642141 is Udaipur State in the Kingdom of Mewar (Rajasthan); "
            "distinct from the same-named udaipur_state_1818_1948 row which is "
            "the unrelated Udaipur State in Chhattisgarh."
        ),
    },
    "udaipur_state_1818_1948": {
        "canonical_name": "Udaipur State (Chhattisgarh)",
        "qid_scope_note": (
            "Q1457519 is Udaipur State in Chhattisgarh (1818-1948); distinct "
            "from the same-named udaipur_state row which is the unrelated "
            "Udaipur State in the Kingdom of Mewar (Rajasthan)."
        ),
    },
}

def main() -> int:
    data = TSV.read_bytes()
    lines = data.split(b"\n")

    header = lines[0].rstrip(b"\r").decode("utf-8").split("\t")
    col_idx = {name: i for i, name in enumerate(header)}

    out_lines = [lines[0]]
    deleted = 0
    cleared = 0
    updated = 0
    seen_cids = set()
    seen_deletions = set()
    for line in lines[1:]:
        if not line:
            out_lines.append(line)
            continue
        had_cr = line.endswith(b"\r")
        body = line[:-1] if had_cr else line
        fields = body.split(b"\t")
        cid = fields[0].decode("ascii", errors="replace")
        seen_cids.add(cid)
        if cid in ROWS_TO_DELETE:
            deleted += 1
            seen_deletions.add(cid)
            continue
        if cid in CLEAR_SCOPE_NOTES:
            fields[col_idx["qid_scope_note"]] = b""
            cleared += 1
        if cid in UDAIPUR_UPDATES:
            updates = UDAIPUR_UPDATES[cid]
            for k, v in updates.items():
                fields[col_idx[k]] = v.encode("utf-8")
            updated += 1
        out_lines.append(b"\t".join(fields) + (b"\r" if had_cr else b""))

    missing = ROWS_TO_DELETE - seen_deletions
    if missing:
        print(f"ERROR: rows-to-delete not found in TSV: {missing}", file=sys.stderr)
        return 1

    TSV.write_bytes(b"\n".join(out_lines))
    print(f"Deleted {deleted} rows", file=sys.stderr)
    print(f"Cleared scope notes on {cleared} rows", file=sys.stderr)
    print(f"Updated Udaipur disambiguation on {updated} rows", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
