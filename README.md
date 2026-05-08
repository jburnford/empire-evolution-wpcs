# empire-evolution-wpcs

A Cypher knowledge graph and interactive visualization of British imperial
territorial evolution, prepared for submission to *Working Papers in Critical
Search* (WPCS).

## Contents

- `paper/empire-evolution-wpcs.qmd` — Quarto source for the paper
- `paper/references.bib` — bibliography
- `data/britishempire_kg_export.cypher` — full graph: 751 historical
  territories (313 colonial polities + 438 princely states) and 1,213 typed
  relationships
- `viz/empire_evolution.html` — self-contained D3.js Sankey visualization
- `scripts/load_falkordb.py` — load the graph into an embedded FalkorDB instance
  (no Docker, no Neo4j server)

## Quick start: spin up the graph in-process

```bash
pip install -r requirements.txt
python3 scripts/load_falkordb.py --interactive
```

This loads the 751 nodes / 1,213 edges into an embedded FalkorDB
("FalkorDBLite") instance saved to `./empire.db` and drops you into a
Cypher REPL. No Neo4j installation, no Docker, no Java.

Sample query at the prompt:

```cypher
MATCH (a:HistoricalTerritory)-[:PARTITIONED_INTO]->(b:HistoricalTerritory)
RETURN a.canonical_name, b.canonical_name, b.established_year
ORDER BY b.established_year LIMIT 20
```

> **Note**: the canonical export uses Neo4j-flavored Cypher
> (`CREATE CONSTRAINT`, `datetime(...)`, `point({srid: 4326, ...})`). The
> FalkorDB loader silently rewrites these on the fly to match FalkorDB's
> parser; temporal types degrade to ISO strings and points retain
> latitude/longitude only. See `scripts/load_falkordb.py` for the rewrite
> rules.

## Alternative: load into Neo4j

```bash
cypher-shell -u neo4j -p <password> -f data/britishempire_kg_export.cypher
```

Neo4j 5.x is recommended (the export uses `CREATE CONSTRAINT IF NOT EXISTS
FOR ... REQUIRE` syntax). Re-running is idempotent.

## Open the visualization

```bash
xdg-open viz/empire_evolution.html      # Linux
open viz/empire_evolution.html          # macOS
```

The data is embedded in the HTML; no server needed.

## Render the paper

```bash
quarto render paper/empire-evolution-wpcs.qmd
```

Renders both HTML and PDF if a TeX distribution is available.

## Citation

```
Clifford, Jim. (2026). A Cypher Knowledge Graph of British Imperial
Territorial Evolution. Working Papers in Critical Search.
```

(Update with version tag and DOI on publication.)

## License

- Paper text: CC-BY 4.0
- Dataset: CC-BY 4.0 (incorporates Wikidata QIDs and curated date/typology
  decisions; Wikidata content itself is CC0)

See `LICENSE` for full terms.
