#!/usr/bin/env python3
"""Phase 2.5: fill the remaining scope-note gaps identified in audit.

Adds qid_scope_note text to rows that were missed by the initial Pass E pass:
  1. Sister-row reuse gaps (15 rows) — file rows reusing a QID whose sister
     rows have notes but the row itself doesn't.
  2. Geographic stand-in (1 row) — south_shetland_islands_whaling_1820_1959.
  3. Pass D pending-review markers (6 rows) — POSSIBLE_FILE_DUPLICATE (5) +
     PLACEHOLDER_NOT_ENTITY (1).
  4. Self-reference stand-ins (14 rows) — wikidata_id == modern_nation_qids
     where the file row covers a colonial precursor of the modern entity.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TSV = REPO / "data" / "qid_manifest.tsv"

NEW_NOTES: dict[str, str] = {
    # --- 1. Sister-row reuse gaps (15) ---
    "new_zealand_colony_1840_1907":
        "[QID_REUSED] Q664 covers continuous NZ state; also assigned to dominion_of_new_zealand_1907_1947 and new_zealand_independent_1947.",
    "dominion_of_new_zealand_1907_1947":
        "[QID_REUSED] Q664 covers continuous NZ state; also assigned to new_zealand_colony_1840_1907 and new_zealand_independent_1947.",
    "new_zealand_independent_1947":
        "[QID_REUSED] Q664 covers continuous NZ state; also assigned to new_zealand_colony_1840_1907 and dominion_of_new_zealand_1907_1947.",
    "commonwealth_of_australia_1901_ongoing":
        "[QID_REUSED] Q408 modern sovereign Australia; also assigned to australia_independent_1942.",
    "australia_independent_1942":
        "[QID_REUSED] Q408 modern sovereign Australia; also assigned to commonwealth_of_australia_1901_ongoing.",
    "gold_coast_colony_1874_1957":
        "[QID_REUSED] Q503623 also assigned to british_gold_coast_1821_1874; WD entity covers full Gold Coast Colony 1821-1957 (both file sub-periods).",
    "canada_dominion_of_1867_ongoing":
        "[QID_REUSED] Q16 modern Canada; also assigned to canada_independent_1931.",
    "canada_independent_1931":
        "[QID_REUSED] Q16 modern Canada; also assigned to canada_dominion_of_1867_ongoing.",
    "dominion_of_newfoundland_1907_1934":
        "[QID_REUSED] Q38610 also assigned to newfoundland_commission_1934_1949; WD entity covers full 1907-1949 Dominion span.",
    "federal_colony_leeward_islands_1833-1960":
        "[QID_REUSED] Q1796551 also assigned to leeward_islands_colony_1671_1816; WD entity covers both 1671-1816 first colony AND 1833-1960 federal colony.",
    "federation_of_malaya_1948_1957":
        "[QID_REUSED] Q1479726 also assigned to malaya_independent_1957_1963; WD Federation of Malaya 1948-1963 covers both colonial Federation and independent phases.",
    "mauritius_1814_1968":
        "[QID_REUSED] Q12053604 British Mauritius also assigned to isle_de_france_british_occupation_1810_1814; WD entity covers full 1810-1968 British rule.",
    "prince_edward_island_province_1873":
        "[QID_REUSED] Q1978 also assigned to prince_edward_island_1769_1873; WD entity covers PEI continuously (colony 1769-1873 + province 1873-onwards).",
    "united_states_1776":
        "[QID_REUSED] Q30 modern USA; also assigned to united_states_of_america_1783. File row tracks Declaration of Independence sub-period; WD entity is the continuous modern state.",
    "united_states_of_america_1783":
        "[QID_REUSED] Q30 modern USA; also assigned to united_states_1776. File row tracks Treaty of Paris recognition sub-period; WD entity is the continuous modern state.",

    # --- 2. Geographic stand-in (1) ---
    "south_shetland_islands_whaling_1820_1959":
        "Q140948 is the geographic archipelago (part of British Antarctic Territory); file row tracks the 1820-1959 whaling-period administrative use of the islands (no separate temporal entity in WD).",

    # --- 3. Pass D pending-review markers (6) ---
    "dedhrota_1900_1947":
        "[POSSIBLE_FILE_DUPLICATE] Sister row 'dedhrota' (Q131126101) also maps to a 'Dedhrota princely state' entity in WD. Pending Pass D human review to decide merge or keep both.",
    "khaniyadhana":
        "[POSSIBLE_FILE_DUPLICATE] Sister row 'khaniadhana_state_1724_1948' (Q16852121) also maps to Khaniadhana princely state. Spelling variant of same place. Pending Pass D human review.",
    "lunavada_state_1434_1948":
        "[POSSIBLE_FILE_DUPLICATE] Sister row 'lunavada' (Q2240915) also maps to Lunavada princely state. Pending Pass D human review to decide merge or keep both.",
    "marwar":
        "[POSSIBLE_FILE_DUPLICATE] Sister row 'jodhpur_state_1226_1949' (Q6207845) maps to Kingdom of Marwar (the polity); this row is the region. Pending Pass D human review.",
    "udaipur_state_1818_1948":
        "[POSSIBLE_FILE_DUPLICATE] Sister row 'udaipur_state' (Q130642141) also maps to Udaipur State. Pending Pass D human review to decide merge or keep both.",
    "princely_states_placeholder_1818_1947":
        "[PLACEHOLDER_NOT_ENTITY] Q1336152 is the CLASS 'princely state' (instance-of type), not a specific entity. File row is a meta/aggregate placeholder; pending Pass D human review (likely deletion).",

    # --- 4. Self-reference stand-ins (14): wikidata_id == modern_nation_qids ---
    "anguilla_1650_ongoing":
        "Q25228 is the modern British Overseas Territory; file row's 1650 start date predates the WD entity's effective inception as a separate BOT.",
    "bermuda_1609_ongoing":
        "Q23635 is the modern British Overseas Territory; file row's 1609 start date predates the WD entity's effective inception.",
    "british_virgin_islands_1672_ongoing":
        "Q25305 is the modern British Overseas Territory; file row's 1672 start date predates the WD entity's effective inception.",
    "brunei_protectorate_1888_1984":
        "Q921 is modern sovereign Brunei; file row's 1888-1984 covers the British protectorate sub-period not separately represented in WD.",
    "cayman_islands_1670_ongoing":
        "Q5785 is the modern British Overseas Territory; file row's 1670 start date predates the WD entity's effective inception.",
    "falkland_islands_1833_ongoing":
        "Q9648 is the modern British Overseas Territory; file row's 1833 start date predates the WD entity's effective inception.",
    "gibraltar_1704_ongoing":
        "Q1410 is the modern British Overseas Territory; file row's 1704 start date predates the WD entity's effective inception.",
    "montserrat_1632_ongoing":
        "Q13353 is the modern British Overseas Territory; file row's 1632 start date predates the WD entity's effective inception.",
    "pitcairn_islands_1838_ongoing":
        "Q35672 is the modern British Overseas Territory; file row's 1838 start date predates the WD entity's effective inception.",
    "saint_helena_ascension_and_tristan_da_cunha_1588_ongoing":
        "Q192184 is the modern British Overseas Territory (current consolidated form since 2009); file row's 1588 start date covers earlier colonial history not separately represented in WD.",
    "swaziland_1903_1968":
        "Q1050 is modern sovereign Eswatini; file row's 1903-1968 covers the British protectorate sub-period not separately represented in WD.",
    "turks_and_caicos_islands_1799_ongoing":
        "Q18221 is the modern British Overseas Territory; file row's 1799 start date predates the WD entity's effective inception.",
    "canada_dominion_of_1867_ongoing":
        "[QID_REUSED] Q16 modern Canada; also assigned to canada_independent_1931. File row's 1867 start date is the Dominion's inception which the WD modern-Canada entity inherits.",
    "commonwealth_of_australia_1901_ongoing":
        "[QID_REUSED] Q408 modern sovereign Australia; also assigned to australia_independent_1942. File row's 1901 start date is federation inception which the WD modern-Australia entity inherits.",
}

def main() -> int:
    data = TSV.read_bytes()
    lines = data.split(b"\n")

    header_idx = 0
    header_fields = lines[header_idx].rstrip(b"\r").split(b"\t")
    assert header_fields[-1] == b"qid_scope_note", "Expected last column qid_scope_note"
    note_col = len(header_fields) - 1

    cid_to_idx: dict[str, int] = {}
    for i, line in enumerate(lines):
        if not line or i == 0:
            continue
        body = line.rstrip(b"\r")
        cid = body.split(b"\t", 1)[0].decode("ascii", errors="replace")
        cid_to_idx[cid] = i

    applied = 0
    overwritten = 0
    missing_in_tsv = []
    for cid, note in NEW_NOTES.items():
        if cid not in cid_to_idx:
            missing_in_tsv.append(cid)
            continue
        idx = cid_to_idx[cid]
        line = lines[idx]
        had_cr = line.endswith(b"\r")
        body = line[:-1] if had_cr else line
        fields = body.split(b"\t")
        existing = fields[note_col].decode("utf-8")
        if existing.strip():
            # Replace with new note (more comprehensive)
            overwritten += 1
        else:
            applied += 1
        fields[note_col] = note.encode("utf-8")
        lines[idx] = b"\t".join(fields) + (b"\r" if had_cr else b"")

    if missing_in_tsv:
        print(f"ERROR: {len(missing_in_tsv)} colony_ids not found in TSV:", file=sys.stderr)
        for c in missing_in_tsv:
            print(f"  - {c}", file=sys.stderr)
        return 1

    TSV.write_bytes(b"\n".join(lines))
    print(f"Applied {applied} new scope notes, overwrote {overwritten}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
