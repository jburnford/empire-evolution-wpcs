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

## Render the paper

```bash
quarto render paper/empire-evolution-wpcs.qmd
```

(Renders both HTML and PDF if a TeX distribution is available.)

## Load the graph

```bash
cypher-shell -u neo4j -p <password> -f data/britishempire_kg_export.cypher
```

The cypher file is self-contained: it creates a uniqueness constraint on
`colony_id`, MERGEs all 751 nodes with their multi-label classification, and
MERGEs all 1,213 relationships. Re-running is idempotent.

## Open the visualization

```bash
xdg-open viz/empire_evolution.html      # Linux
open viz/empire_evolution.html          # macOS
```

The data is embedded in the HTML; no server needed.

## Citation

```
Clifford, Jim. (2026). A Cypher Knowledge Graph of British Imperial
Territorial Evolution. Working Papers in Critical Search.
```

(Update with version tag and DOI on publication.)

## License

- Paper text: CC-BY 4.0
- Dataset: CC-BY 4.0 (incorporates Wikidata QIDs and curated date/typology
  decisions; Wikidata content is CC0)

See `LICENSE` for full terms.
