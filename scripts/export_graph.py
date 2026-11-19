"""Export the released knowledge graph to assets/graph_data.js for graph.html.

Reads only files inside this release (knowledge_graph/*.graphml and the consensus
entity-resolution record), so the viewer always matches the published graph.
Standard library only. make_page.py calls main(); it can also be run directly:

    python3 scripts/export_graph.py
"""
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]
GRAPH = OUT / "knowledge_graph/geoai_knowledge_merged_hier_merged_consensus_hier.graphml"
RESOLUTION = OUT / "knowledge_graph/entity_resolution_consensus.json"
TARGET = OUT / "assets/graph_data.js"
NS = {"g": "http://graphml.graphdrawing.org/xmlns"}


def read_graphml(path):
    root = ET.parse(path).getroot()
    keys = {k.get("id"): k.get("attr.name") for k in root.findall("g:key", NS)}
    def attrs(el):
        return {keys.get(d.get("key"), d.get("key")): (d.text or "") for d in el.findall("g:data", NS)}
    graph = root.find("g:graph", NS)
    nodes = {n.get("id"): attrs(n) for n in graph.findall("g:node", NS)}
    edges = [(e.get("source"), e.get("target"), attrs(e)) for e in graph.findall("g:edge", NS)]
    return nodes, edges


def main():
    nodes, raw_edges = read_graphml(GRAPH)
    # "lifted" edges repeat instance-level causal links at concept level; drawing them doubles the clutter.
    edges = [(u, v, d) for u, v, d in raw_edges if d.get("derived") != "lifted"]

    merged_from = {}
    for entry in json.loads(RESOLUTION.read_text(encoding="utf-8")):
        for group in entry.get("consensus_groups") or []:
            members, canon = group.get("members", []), group.get("canonical")
            if len(members) > 1:
                merged_from[canon] = [m for m in members if m != canon]

    indeg, outdeg = Counter(), Counter()
    for u, v, _ in raw_edges:
        outdeg[u] += 1
        indeg[v] += 1
    parents = {v for u, v, d in edges if d.get("relation") == "IS_A"}

    out_nodes = []
    for nid, d in nodes.items():
        n = {"id": nid, "label": d.get("label") or nid, "type": d.get("type") or "Unknown",
             "harm_family": d.get("harm_family", ""), "indeg": indeg[nid], "outdeg": outdeg[nid],
             "degree": indeg[nid] + outdeg[nid]}
        if d.get("concept"):
            n["concept"] = d["concept"]
        if merged_from.get(nid):
            n["merged_from"] = merged_from[nid]
        if nid in parents and n["type"] != "HarmCategory":
            n["is_concept"] = True
        out_nodes.append(n)

    out_edges = []
    for u, v, d in edges:
        e = {"from": u, "to": v, "relation": d.get("relation") or "RELATED_TO"}
        try:
            e["weight"] = int(float(d.get("weight") or 1))
        except ValueError:
            e["weight"] = 1
        # Source documents and conditions are already public in the GraphML and source_documents.txt.
        if d.get("sources"):
            e["sources"] = sorted({s.strip() for s in d["sources"].split(";") if s.strip()})
        if d.get("conditions"):
            e["conditions"] = d["conditions"]
        out_edges.append(e)

    stats = {
        "nodes": len(out_nodes), "edges": len(out_edges),
        "merged_nodes": sum(1 for n in out_nodes if n.get("merged_from")),
        "by_type": dict(Counter(n["type"] for n in out_nodes)),
        "by_relation": dict(Counter(e["relation"] for e in out_edges)),
        "by_harm": dict(Counter(n["harm_family"] for n in out_nodes
                                if n["harm_family"] and n["type"] == "EthicalImpact")),
        "sources": len({s for e in out_edges for s in e.get("sources", [])}),
    }
    data = {"graph": GRAPH.relative_to(OUT).as_posix(), "stats": stats, "nodes": out_nodes, "edges": out_edges}
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    TARGET.write_text("window.GRAPH_DATA=" + payload + ";\n", encoding="utf-8")
    return stats


if __name__ == "__main__":
    print(json.dumps(main(), indent=1))
