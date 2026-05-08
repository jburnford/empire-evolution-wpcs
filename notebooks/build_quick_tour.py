#!/usr/bin/env python3
"""
Generate notebooks/quick_tour.ipynb from cell sources defined in this script.
Re-run after editing the CELLS list to refresh the notebook.
"""
import json
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parent / "quick_tour.ipynb"


def md(*lines):
    return {"cell_type": "markdown", "metadata": {}, "source": "\n".join(lines)}


def code(*lines):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": "\n".join(lines)}


CELLS = [
md(
"# British Empire KG — quick tour with FalkorDBLite + pyvis",
"",
"This notebook loads the canonical Cypher export into an embedded",
"FalkorDB instance (no Docker, no Neo4j server) and builds three small",
"visualizations on top of it:",
"",
"1. **Schema-level stats** — label and relationship-type counts",
"2. **Lineage of modern Canada** — predecessor tree via `EVOLVED_INTO` /",
"   `PARTITIONED_INTO`",
"3. **Southeast Asia subgraph** — colored by colonial type, showing the",
"   1963 Malaysia formation and 1965 Singapore separation",
"",
"All three are rendered as interactive HTML through pyvis.",
),

md(
"## Setup",
"",
"From the repo root:",
"",
"```bash",
"pip install -r requirements.txt jupyter pyvis networkx pandas",
"python scripts/load_falkordb.py --reset    # creates ./empire.db",
"jupyter notebook notebooks/quick_tour.ipynb",
"```",
"",
"The DB file is git-ignored; the loader regenerates it from",
"`data/britishempire_kg_export.cypher` (~2 seconds).",
),

code(
"from pathlib import Path",
"import pandas as pd",
"import networkx as nx",
"from pyvis.network import Network",
"from IPython.display import IFrame",
"from redislite.falkordb_client import FalkorDB",
"",
"# Locate empire.db at the repo root regardless of where the notebook is launched",
"REPO_ROOT = Path.cwd()",
"if REPO_ROOT.name == 'notebooks':",
"    REPO_ROOT = REPO_ROOT.parent",
"DB_PATH = REPO_ROOT / 'empire.db'",
"assert DB_PATH.exists(), f'No graph at {DB_PATH}. Run: python scripts/load_falkordb.py --reset'",
"",
"db = FalkorDB(str(DB_PATH))",
"g = db.select_graph('empire')",
"",
"def cypher(q):",
"    \"\"\"Run a Cypher query and return the raw result rows.\"\"\"",
"    return g.query(q).result_set",
),

md(
"## 1. Schema-level stats",
"",
"What kinds of polities and what kinds of relationships does the graph contain?",
),

code(
"# Count nodes by their specific subtype label (drop the always-present base label).",
"rows = cypher('''",
"  MATCH (n:HistoricalTerritory)",
"  UNWIND labels(n) AS lbl",
"  WITH lbl WHERE lbl <> 'HistoricalTerritory' AND lbl <> 'Colony'",
"  RETURN lbl, count(*) AS n",
"  ORDER BY n DESC",
"''')",
"pd.DataFrame(rows, columns=['label', 'count'])",
),

code(
"# Edge-type breakdown",
"rows = cypher('''",
"  MATCH ()-[r]->()",
"  RETURN type(r) AS rel, count(*) AS n",
"  ORDER BY n DESC",
"''')",
"pd.DataFrame(rows, columns=['relationship', 'count'])",
),

md(
"## 2. The lineage of modern Canada",
"",
"What polities flowed into the entity we now call Canada? Cypher's variable-",
"length pattern syntax expresses this naturally: walk *backwards* from",
"`canada_independent_1931` along `EVOLVED_INTO`, `PARTITIONED_INTO`, and",
"`MERGED_INTO` edges.",
),

code(
"LINEAGE_QUERY = '''",
"  MATCH path = (anc:HistoricalTerritory)",
"               -[:EVOLVED_INTO|PARTITIONED_INTO|MERGED_INTO*0..6]->",
"               (tgt:HistoricalTerritory {colony_id: 'canada_independent_1931'})",
"  RETURN nodes(path) AS chain, relationships(path) AS rels",
"'''",
"results = cypher(LINEAGE_QUERY)",
"print(f'{len(results)} ancestor paths to Canada')",
"",
"# Fold the paths into a single networkx DiGraph (deduplicating shared nodes)",
"ng = nx.DiGraph()",
"for chain, rels in results:",
"    for n in chain:",
"        nid = n.properties['colony_id']",
"        ng.add_node(nid,",
"                    label=n.properties.get('canonical_name', nid),",
"                    est=n.properties.get('established_year'),",
"                    ind=n.properties.get('independence_year'),",
"                    type=n.properties.get('colony_type'),",
"                    region=n.properties.get('region'))",
"    for i, r in enumerate(rels):",
"        # FalkorDB returns int node IDs on edges, so look up the colony_id from chain",
"        s = chain[i].properties['colony_id']",
"        t = chain[i + 1].properties['colony_id']",
"        ng.add_edge(s, t, relation=r.relation)",
"",
"print(f'{ng.number_of_nodes()} unique nodes, {ng.number_of_edges()} unique edges')",
),

code(
"# Render with pyvis. The `notebook=True` flag emits a single self-contained",
"# HTML file that we then embed via IFrame.",
"net = Network(notebook=True, cdn_resources='in_line', directed=True,",
"              height='620px', width='100%', bgcolor='#0a0a1a', font_color='#eee')",
"",
"REL_COLOR = {'EVOLVED_INTO': '#88ccff', 'PARTITIONED_INTO': '#ffaa66',",
"             'MERGED_INTO': '#aaffaa'}",
"",
"for n, attrs in ng.nodes(data=True):",
"    period = f\"{attrs.get('est') or '?'}–{attrs.get('ind') or 'ongoing'}\"",
"    title = f\"<b>{attrs['label']}</b><br>{attrs.get('type') or '?'}<br>{period}<br>{attrs.get('region') or ''}\"",
"    net.add_node(n, label=attrs['label'], title=title)",
"for s, t, attrs in ng.edges(data=True):",
"    rel = attrs.get('relation', '')",
"    net.add_edge(s, t, label=rel, color=REL_COLOR.get(rel, '#888'), arrows='to',",
"                 font={'size': 10, 'color': '#ccc'})",
"",
"net.save_graph('canada_lineage.html')",
"IFrame('canada_lineage.html', width='100%', height=640)",
),

md(
"## 3. Southeast Asia regional subgraph",
"",
"All territorial nodes whose `region = 'Southeast Asia'`, with the",
"relationships that connect them. Colored by colonial-type taxonomy.",
"Highlights the messy 1946 Straits Settlements dissolution and the",
"1963–1965 Malaysia/Singapore restructuring.",
),

code(
"rows = cypher('''",
"  MATCH (a:HistoricalTerritory) WHERE a.region = 'Southeast Asia'",
"  OPTIONAL MATCH (a)-[r]->(b:HistoricalTerritory) WHERE b.region = 'Southeast Asia'",
"  RETURN a, r, b",
"''')",
"",
"G = nx.DiGraph()",
"for a, r, b in rows:",
"    aid = a.properties['colony_id']",
"    G.add_node(aid,",
"               label=a.properties.get('canonical_name', aid),",
"               est=a.properties.get('established_year'),",
"               ind=a.properties.get('independence_year'),",
"               type=a.properties.get('colony_type'))",
"    if b is not None:",
"        bid = b.properties['colony_id']",
"        G.add_node(bid,",
"                   label=b.properties.get('canonical_name', bid),",
"                   est=b.properties.get('established_year'),",
"                   ind=b.properties.get('independence_year'),",
"                   type=b.properties.get('colony_type'))",
"        G.add_edge(aid, bid, relation=r.relation)",
"",
"print(f'{G.number_of_nodes()} nodes, {G.number_of_edges()} edges in Southeast Asia')",
),

code(
"TYPE_COLOR = {",
"    'Crown Colony': '#5a8fd9', 'Protectorate': '#d97a5a',",
"    'Federation': '#7bd97a', 'Independence': '#d95a8f',",
"    'Princely State': '#d9c95a', 'Colony': '#9d77c4',",
"    'Company Territory': '#c4a777', 'Trading Post': '#c4a777',",
"    'Military Administration': '#888888',",
"}",
"",
"net = Network(notebook=True, cdn_resources='in_line', directed=True,",
"              height='720px', width='100%', bgcolor='#0a0a1a', font_color='#eee')",
"net.barnes_hut(spring_length=180)",
"",
"for n, attrs in G.nodes(data=True):",
"    period = f\"{attrs.get('est') or '?'}–{attrs.get('ind') or 'ongoing'}\"",
"    color = TYPE_COLOR.get(attrs.get('type'), '#888')",
"    title = f\"<b>{attrs['label']}</b><br>{attrs.get('type') or '?'}<br>{period}\"",
"    net.add_node(n, label=attrs['label'], title=title, color=color)",
"for s, t, attrs in G.edges(data=True):",
"    rel = attrs.get('relation', '')",
"    net.add_edge(s, t, label=rel, arrows='to', font={'size': 9, 'color': '#bbb'})",
"",
"net.save_graph('se_asia.html')",
"IFrame('se_asia.html', width='100%', height=740)",
),

md(
"## What's next",
"",
"Same recipe scales to other questions:",
"",
"- **Time slice** — `MATCH (n) WHERE n.established_year <= 1900 AND",
"  (n.independence_year IS NULL OR n.independence_year >= 1900)` to see",
"  who was active at the turn of the twentieth century",
"- **Princely-state network** — filter to `:PrincelyState` and chase",
"  `EVOLVED_INTO` into Dominion of India / Pakistan to see the 1947–1950",
"  accession cascade",
"- **Partition vs. evolution** — group by edge type to compare typologies",
"  of imperial dissolution",
"",
"The advantage of having the graph in-process via FalkorDBLite is that any",
"of these can be a single Cypher query plus a few lines of pyvis.",
),
]


nb = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

NOTEBOOK.write_text(json.dumps(nb, indent=1))
print(f"wrote {NOTEBOOK} ({len(CELLS)} cells)")
