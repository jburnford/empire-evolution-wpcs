#!/usr/bin/env python3
"""
Load britishempire_kg_export.cypher into an embedded FalkorDB instance
(FalkorDBLite — no Docker, no Neo4j, just `pip install falkordblite`).

Usage:
  python3 scripts/load_falkordb.py              # default: ./empire.db, graph "empire"
  python3 scripts/load_falkordb.py --interactive  # drop into a query REPL after loading

The canonical .cypher is Neo4j-flavored; this loader preprocesses three
constructs FalkorDB's parser doesn't accept:
  1. `CREATE CONSTRAINT … REQUIRE …`     → dropped (FalkorDB has implicit indexing)
  2. `datetime('iso-string')`             → unwrapped to `'iso-string'`
  3. `point({srid: 4326, longitude, latitude})` → `point({latitude, longitude})`
The loss is small: temporal types become ISO-format strings; spatial points
keep lat/lon (the SRID is implied).
"""
import argparse
import re
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CYPHER = REPO_DIR / "data" / "britishempire_kg_export.cypher"


# ── preprocessing ──

def preprocess_for_falkordb(text: str) -> str:
    """Convert Neo4j-flavored Cypher into FalkorDB-flavored Cypher (in-memory)."""
    # 1. Drop CREATE CONSTRAINT statements entirely.
    text = re.sub(
        r"CREATE\s+CONSTRAINT[^;]*;",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # 2. Unwrap datetime('…') → '…'   (FalkorDB has no datetime() function).
    text = re.sub(
        r"datetime\(\s*('([^']*)'|\"([^\"]*)\")\s*\)",
        lambda m: f"'{m.group(2) or m.group(3)}'",
        text,
    )

    # 3. point({srid: …, longitude: x, latitude: y}) → point({latitude: y, longitude: x})
    #    (FalkorDB requires exactly the latitude/longitude keys, no srid.)
    def fix_point(match: re.Match) -> str:
        body = match.group(1)
        kv = {}
        for part in re.split(r",\s*", body):
            if ":" not in part:
                continue
            k, v = part.split(":", 1)
            kv[k.strip()] = v.strip()
        lat = kv.get("latitude")
        lon = kv.get("longitude")
        if lat is None or lon is None:
            return match.group(0)
        return f"point({{latitude: {lat}, longitude: {lon}}})"

    text = re.sub(r"point\(\s*\{([^}]*)\}\s*\)", fix_point, text)
    return text


def split_statements(text: str) -> list[str]:
    out, buf = [], []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        if "//" in s:
            s = s.split("//", 1)[0].rstrip()
        buf.append(s)
        if s.endswith(";"):
            stmt = " ".join(buf).rstrip(";").strip()
            if stmt:
                out.append(stmt)
            buf = []
    return out


# ── main ──

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cypher", default=str(DEFAULT_CYPHER),
                   help=f"path to the Neo4j-format export (default: {DEFAULT_CYPHER.relative_to(REPO_DIR)})")
    p.add_argument("--db", default="empire.db", help="local FalkorDBLite DB file (default: ./empire.db)")
    p.add_argument("--graph", default="empire", help="graph name inside the DB (default: empire)")
    p.add_argument("--interactive", action="store_true",
                   help="drop into a REPL after loading; type Cypher queries, blank line to exit")
    p.add_argument("--reset", action="store_true",
                   help="delete the existing graph before loading")
    args = p.parse_args()

    try:
        from redislite.falkordb_client import FalkorDB
    except ImportError:
        sys.exit("FalkorDBLite is not installed. Run: pip install falkordblite")

    cypher = Path(args.cypher).read_text()
    cypher = preprocess_for_falkordb(cypher)
    statements = split_statements(cypher)
    print(f"Loaded {len(statements)} statements from {args.cypher}")

    db = FalkorDB(args.db)
    g = db.select_graph(args.graph)
    if args.reset:
        try:
            g.delete()
        except Exception:
            pass
        g = db.select_graph(args.graph)

    ok, fail = 0, 0
    fail_examples = []
    for i, stmt in enumerate(statements, 1):
        try:
            g.query(stmt)
            ok += 1
        except Exception as e:
            fail += 1
            if len(fail_examples) < 5:
                fail_examples.append((i, str(e)[:200], stmt[:160]))
        if i % 500 == 0:
            print(f"  ... {i}/{len(statements)}  ({ok} ok, {fail} fail)")

    print(f"\nDone: {ok} ok, {fail} failed (graph '{args.graph}' in {args.db})")
    if fail_examples:
        print("\nExamples of failures:")
        for i, err, stmt in fail_examples:
            print(f"  [{i}] {err}")
            print(f"      stmt: {stmt}")

    # Quick stats
    try:
        rows = g.query("MATCH (n:HistoricalTerritory) RETURN count(n) AS n").result_set
        n_nodes = rows[0][0] if rows else 0
        rows = g.query("MATCH ()-[r]->() RETURN count(r) AS n").result_set
        n_rels = rows[0][0] if rows else 0
        print(f"\nGraph stats: {n_nodes} territories, {n_rels} relationships")
    except Exception as e:
        print(f"(stats query failed: {e})")

    if args.interactive:
        print("\nInteractive Cypher REPL (blank line to exit). Try:")
        print("  MATCH (n) RETURN labels(n), count(n) ORDER BY count(n) DESC")
        while True:
            try:
                q = input("\ncypher> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not q:
                break
            if not q.endswith(";"):
                q = q + ";"
            try:
                res = g.query(q.rstrip(";"))
                for row in res.result_set[:50]:
                    print("  ", row)
                more = len(res.result_set) - 50
                if more > 0:
                    print(f"  ... ({more} more rows)")
            except Exception as e:
                print(f"error: {e}")


if __name__ == "__main__":
    main()
