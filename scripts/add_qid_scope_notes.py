#!/usr/bin/env python3
"""Add qid_scope_note column to data/qid_manifest.tsv.

Sources:
1. Phase 1 issues CSV (data/wikidata_qid_issues.csv) for QID_REUSED,
   QID_REUSED_TOO_BROAD, DATE_RANGE_MISMATCH categories.
2. Hard-coded Pass C scope notes for entries where the resolved QID has a
   known date/scope variance (geographic vs polity, parent/successor entity,
   sub-period mappings, etc.).
"""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TSV = REPO / "data" / "qid_manifest.tsv"
ISSUES = REPO / "data" / "wikidata_qid_issues.csv"

# Pass C scope notes — entries where the new QID has a known scope/date variance
PASS_C_NOTES = {
    "bahamas_colony_1666_1973":
        "Q21815597 inception 1718 (file's 1666 reflects earliest English settlement); 1973 dissolved exact match.",
    "bay_islands_1852_1859":
        "Q107987587 dissolved 1862 per WD (file 1859); minor end-date variance.",
    "berbice_colony_1803_1831":
        "Q675322 covers Dutch+British Berbice 1627-1815 (merged into British Guiana); file row's 1803-1831 is the British sub-period.",
    "demerara_colony_1803_1831":
        "Q1185346 covers Dutch+British Demerara 1745-1815 (merged into British Guiana); file row's 1803-1831 is the British sub-period.",
    "essequibo_colony_1803_1831":
        "Q1368792 covers Dutch+British Essequibo 1616-1815 (merged into British Guiana); file row's 1803-1831 is the British sub-period.",
    "mosquito_coast_1638_1860":
        "Q6037274 (Mosquitia) WD inception 1687 dissolved 1894; file's 1638-1860 reflects different start (early English contact) and end (Kingdom of Mosquitia phase).",
    "coorg_province_1834_1947":
        "Q24905912 dissolved 1950 per WD (file 1947); the 1947-1950 sub-period was post-independence Coorg State successor.",
    "newfoundland_commission_1934_1949":
        "Q38610 Dominion of Newfoundland covers 1907-1949; file row tracks the 1934-1949 Commission of Government sub-period (no separate territorial WD entity for the Commission).",
    "prince_edward_island_1769_1873":
        "Q1978 also assigned to prince_edward_island_province_1873; WD entity covers PEI continuously (colony 1769-1873 + province 1873-onwards). File row tracks the colony sub-period.",
    "heard_and_mcdonald_islands_1833_1947":
        "Q131198 transferred from UK to Australia 1953; file row covers the British colonial period 1833-1947.",
    "henderson_island_1902_ongoing":
        "Q379759 is the geographic atoll; file row tracks British administrative period (annexed via Pitcairn Islands 1902).",
    "ducie_island_1902_ongoing":
        "Q1122663 is the geographic atoll; file row tracks British administrative period via Pitcairn Islands.",
    "oeno_island_1902_ongoing":
        "Q940773 is the geographic atoll; file row tracks British administrative period via Pitcairn Islands.",
    "heligoland_1807_1890":
        "Q3129772 is the geographic German island; British colonial period 1807-1890 not separately represented in WD.",
    "minorca_first_1708_1756":
        "Q52636 is the modern Spanish island Menorca (also assigned to minorca_second and minorca_third); British colonial period 1708-1756 (1st of 3 occupations) not separately represented in WD.",
    "minorca_second_1763_1782":
        "Q52636 is the modern Spanish island Menorca (also assigned to minorca_first and minorca_third); British colonial period 1763-1782 (2nd of 3 occupations) not separately represented in WD.",
    "minorca_third_1798_1802":
        "Q52636 is the modern Spanish island Menorca (also assigned to minorca_first and minorca_second); British colonial period 1798-1802 (3rd of 3 occupations) not separately represented in WD.",
    "james_island_trading_post_1661_1816":
        "Q23498700 is the fort/building entity (Fort James Island); file row covers the British trading post period 1661-1816 on the island now called Kunta Kinteh Island.",
    "kingdom_of_ireland_1541_1801":
        "Q215530 inception 1542 per WD (file 1541); 1-year variance reflects Crown of Ireland Act 1542.",
    "gilbert_islands_1976_1979":
        "Q271876 is the geographic Gilbert Islands chain; file row covers the brief 1976-1979 separate-colony sub-period before Kiribati independence (no separate WD colony entity).",
    "province_of_freedom_1787_1792":
        "Q3483448 is the Sierra Leone Company (also assigned to sierra_leone_company_settlement_1792_1808); the Province of Freedom 1787-1792 was its early-period predecessor administration.",
    "sierra_leone_company_settlement_1792_1808":
        "Q3483448 also assigned to province_of_freedom_1787_1792; the Sierra Leone Company entity covers both periods.",
    "assam_bengal_presidency_1826_1874":
        "Q817165 is the parent Bengal Presidency (also assigned to bengal_presidency_company and bengal_presidency_crown rows); file row covers Assam-within-Bengal sub-period 1826-1874.",
    "banda_islands_british_occupation_1810_1817":
        "Q18639233 covers the broader French/British interregnum in the Dutch East Indies 1806-1816; file row covers Banda Islands sub-period of British rule 1810-1817.",
    "german_east_africa_british_occupied_1916_1922":
        "Q158725 Tanganyika Territory inception 1922; file row covers the pre-mandate British military occupation 1916-1922 of the same territory.",
    "dominica_colony_1763_1978":
        "Q784 is modern Dominica sovereign state (since 1978); file row's 1763-1978 colonial precursor not separately represented in WD.",
    "grenada_colony_1763_1974":
        "Q3116419 is the geographic island; no separate Colony of Grenada entity in WD; file row covers British colonial period 1763-1974.",
    "andaman_and_nicobar_islands_1789_1947":
        "Q40888 is modern Indian union territory (since 1956); file row covers earlier British colonial period 1789-1947 not separately represented in WD.",
    "assam_province_1874_1905":
        "Q17513379 is the restored Assam Province 1912-1947 (also assigned to assam_province_restored_1912_1947); file row covers the earlier 1874-1905 Chief Commissioner's Province (no separate WD entity).",
    "iraq_1932_ongoing":
        "Q796 modern Iraq covers monarchy (1932-1958) + republic (1958-onwards) as one continuous entity.",
    "antigua_colony_1632_1981":
        "Q130386222 Colony of Antigua covers a narrower period than file's full 1632-1981 (WD entity flag images dated 1956-1967); no broader colony entity in WD.",
    "ellice_islands_1976_1978":
        "Q109039320 WD inception 1975 (file 1976); 1975 referendum, 1976 formal split from Gilbert.",
    "ajmer_merwara_1818_1947":
        "Q412980 dissolved 1936 per WD (file 1947); 1936 was reorganization, administered until 1947.",
    "norfolk_island_1788_1914":
        "Q31057 is modern Australian external territory; file row covers earlier British colonial penal period 1788-1914 not separately represented in WD.",
    "norfolk_island_whaling_station_1830_1870":
        "Q31057 is modern Australian external territory (also assigned to norfolk_island_1788_1914); file row covers a whaling sub-period not separately represented in WD.",
    "christmas_island_1888_1958":
        "Q31063 is modern Australian external territory (since 1958); file row covers earlier British colonial period 1888-1958 not separately represented in WD.",
    "cocos_keeling_islands_1857_1955":
        "Q36004 is modern Australian external territory (since 1955); file row covers earlier British colonial period 1857-1955 not separately represented in WD.",
    "cook_islands_1888_1901":
        "Q26988 is modern Cook Islands self-governing state (since 1965); file row covers earlier British protectorate period 1888-1901 not separately represented in WD.",
    "south_georgia_whaling_stations_1904_1965":
        "Q35086 is the parent South Georgia and the South Sandwich Islands BOT (also assigned to south_georgia, south_sandwich_islands rows); file row covers the whaling-stations sub-period not separately represented in WD.",
    "deception_island_whaling_1906_1931":
        "Modern_nation_qids field uses Q35086 (South Georgia & Sandwich BOT) but Deception Island is in the South Shetlands (part of British Antarctic Territory Q165783); minor data-quality variance.",
}

def load_phase1_notes() -> dict[str, str]:
    """Load scope notes from issues CSV for the 3 target categories."""
    notes: dict[str, str] = {}
    with ISSUES.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            verdict = row["verdict"]
            if verdict in ("QID_REUSED", "QID_REUSED_TOO_BROAD", "DATE_RANGE_MISMATCH"):
                cid = row["colony_id"]
                # Use the issue note verbatim, prefixed with verdict tag
                note = row["notes"].strip()
                # Strip any embedded tabs/CR for safety
                note = note.replace("\t", " ").replace("\r", "").replace("\n", " ")
                notes[cid] = f"[{verdict}] {note}"
    return notes

def main() -> int:
    phase1 = load_phase1_notes()
    print(f"Loaded {len(phase1)} Phase 1 scope notes from issues CSV", file=sys.stderr)
    print(f"Hard-coded {len(PASS_C_NOTES)} Pass C scope notes", file=sys.stderr)

    overlap = set(phase1) & set(PASS_C_NOTES)
    if overlap:
        print(f"Overlap (Pass C wins): {sorted(overlap)}", file=sys.stderr)

    # Merge: Pass C notes take precedence (more current) where overlap exists
    notes: dict[str, str] = {**phase1, **PASS_C_NOTES}
    print(f"Total scope notes: {len(notes)}", file=sys.stderr)

    data = TSV.read_bytes()
    lines = data.split(b"\n")

    out_lines = []
    rows_with_notes = 0
    for i, line in enumerate(lines):
        if not line:
            out_lines.append(line)
            continue
        had_cr = line.endswith(b"\r")
        body = line[:-1] if had_cr else line
        fields = body.split(b"\t")
        if i == 0:
            # Header — append new column
            assert fields == [
                b"colony_id", b"name", b"canonical_name", b"wikidata_id",
                b"modern_nation_qids", b"established_year", b"end_date",
                b"region", b"colony_type", b"capital", b"successor_dominion",
            ], f"Unexpected header: {fields}"
            fields.append(b"qid_scope_note")
        else:
            assert len(fields) == 11, f"Line {i+1} has {len(fields)} fields, not 11"
            cid = fields[0].decode("ascii", errors="replace")
            note = notes.get(cid, "")
            if note:
                rows_with_notes += 1
            fields.append(note.encode("utf-8"))
        new_line = b"\t".join(fields) + (b"\r" if had_cr else b"")
        out_lines.append(new_line)

    print(f"Wrote scope_note to {rows_with_notes} rows", file=sys.stderr)
    TSV.write_bytes(b"\n".join(out_lines))
    return 0

if __name__ == "__main__":
    sys.exit(main())
