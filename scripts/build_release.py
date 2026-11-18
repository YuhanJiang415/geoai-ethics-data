"""Build the public data release from the private audit outputs.

Reads  results_final_v2/ (per-paper audit outputs, tags) and geoai_audit/ (prompts, ontology)
Writes public_release/{data,knowledge_graph,prompts,ontology}/

Nothing copyrighted leaves this script: no abstracts, no full-text quotes, no retrieved
passages from the knowledge-graph source documents, and no per-paper audit findings.
Audit outputs are released only as aggregates; any cross-tab cell describing fewer than
K_MIN papers is suppressed.

Usage:  python public_release/scripts/build_release.py      (from the GeoAI_Project root)
"""
import ast
import collections
import csv
import glob
import gzip
import json
import re
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SRC = PROJECT / "results_final_v2"
OUT = PROJECT / "public_release"
K_MIN = 5
FAMILIES = ["EqualRightsViolation", "PhysicalHarm", "EconomicLoss",
            "PrivacyViolation", "PsychologicalHarm"]
STATUSES = ["INSTANTIATED", "POTENTIAL", "NOT_TRIGGERED"]
PROVENANCE = ["graph_exact", "graph_anchored", "inferred"]


def norm(s):
    return " ".join((s or "").lower().split()).strip(". ")


def split(v):
    return [x.strip() for x in (v or "").split(";") if x.strip()]


def write_csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# ---- load ---------------------------------------------------------------------------

tags = list(csv.DictReader(open(SRC / "metadata/tags.csv", encoding="utf-8")))
tag_by_doi = {r["doi"].lower(): r for r in tags}

# Per-paper audit summary, kept in memory only: never written out row by row.
paper = {}
edge_stats = collections.defaultdict(lambda: collections.Counter())
edge_papers = collections.defaultdict(set)
ent_stats = collections.defaultdict(lambda: collections.Counter())
ent_papers = collections.defaultdict(set)
status_tab = collections.Counter()

for f in sorted(glob.glob(str(SRC / "journals/*_raw.json"))):
    corpus = Path(f).name[:-len("_raw.json")]
    for p in json.load(open(f))["papers"]:
        doi = p["source"]["doi"].lower()
        fams, n_mit = set(), 0
        for t in p["triples"]:
            h, e, ta = t["head"], t["edge"], t["tail"]
            st, pv = e.get("instantiation"), e.get("provenance")
            fam = ta.get("harm_family") if ta["type"] == "EthicalImpact" else None
            if fam:
                fams.add(fam)
            if h["type"] == "Mitigation":
                n_mit += 1
            status_tab[(h["type"], e["relation_type"], ta["type"], st, pv,
                        e.get("quote_verified"))] += 1
            key = (h["type"], norm(h["entity"]), e["relation_type"], ta["type"],
                   norm(ta["entity"]), fam or "")
            edge_stats[key]["n"] += 1
            edge_stats[key][st] += 1
            edge_stats[key][pv] += 1
            edge_papers[key].add(doi)
            for node, role in ((h, "head"), (ta, "tail")):
                k = (node["type"], norm(node["entity"]), fam if node is ta else "")
                ent_stats[k][role] += 1
                ent_stats[k][st] += 1
                ent_papers[k].add(doi)
        paper[doi] = {"corpus": corpus, "n": len(p["triples"]), "fams": fams,
                      "mit": n_mit > 0}

# ---- data/papers.csv : bibliographic IDs -------------------------------------------

write_csv(OUT / "data/papers.csv",
          ["doi", "year", "journal", "title", "article_type", "text_source", "audit_corpus", "audited"],
          [[r["doi"], r["year"], r["journal"], r["title"], r["article_type"], r["text_source"],
            paper.get(r["doi"].lower(), {}).get("corpus", ""),
            int(r["doi"].lower() in paper)] for r in tags])

# ---- data/paper_tags.csv : descriptive (non-audit) metadata ------------------------

TAG_COLS = ["sensor", "spatial_resolution", "study_region", "study_region_scope",
            "study_region_continent", "study_region_global", "affected_population",
            "application_domain", "geoai_method", "ethical_theme", "first_author_country"]
write_csv(OUT / "data/paper_tags.csv", ["doi"] + TAG_COLS,
          [[r["doi"]] + [r[c] for c in TAG_COLS] for r in tags])

# ---- data/aggregates ---------------------------------------------------------------

AGG = OUT / "data/aggregates"

edges = sorted(edge_stats.items(), key=lambda kv: -kv[1]["n"])
write_csv(AGG / "edges.csv.gz",
          ["head_type", "head", "relation", "tail_type", "tail", "harm_family", "n_triples",
           "n_papers"] + [s.lower() for s in STATUSES] + PROVENANCE,
          [list(k) + [c["n"], len(edge_papers[k])] + [c[s] for s in STATUSES]
           + [c[p] for p in PROVENANCE] for k, c in edges])

ents = sorted(ent_stats.items(), key=lambda kv: -len(ent_papers[kv[0]]))
write_csv(AGG / "entities.csv.gz",
          ["type", "entity", "harm_family", "n_papers", "n_as_head", "n_as_tail"]
          + [s.lower() for s in STATUSES],
          [list(k) + [len(ent_papers[k]), c["head"], c["tail"]] + [c[s] for s in STATUSES]
           for k, c in ents])

write_csv(AGG / "triples_by_type_status.csv",
          ["head_type", "relation", "tail_type", "instantiation", "provenance", "quote_verified",
           "n_triples"],
          [list(k) + [v] for k, v in sorted(status_tab.items(), key=lambda kv: -kv[1])])


def group_rows(groups):
    """groups: value -> list of dois. One row per value, audit cells suppressed below K_MIN."""
    rows = []
    for val, dois in sorted(groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))):
        n = len(dois)
        aud = [paper[d] for d in dois if d in paper]
        if n < K_MIN:
            rows.append([val, n] + [""] * (4 + len(FAMILIES)))
            continue
        rows.append([val, n, len(aud), sum(a["n"] > 0 for a in aud), sum(a["n"] for a in aud),
                     sum(a["mit"] for a in aud)]
                    + [sum(fam in a["fams"] for a in aud) for fam in FAMILIES])
    return rows


AGG_HEADER = ["value", "n_papers", "n_audited", "n_with_triples", "n_triples",
              "n_with_mitigation"] + [f"n_{f}" for f in FAMILIES]

dims = {"year": lambda r: [r["year"]], "journal": lambda r: [r["journal"]],
        "text_source": lambda r: [r["text_source"]],
        "ethical_keyword": lambda r: ["yes" if r["ethical_theme"] else "no"],
        "first_author_country": lambda r: split(r["first_author_country"])[:1],
        # Exclusive grouping used for Figure 9: "Global North; Global South" is its own value.
        "study_region_global_combination": lambda r: ["; ".join(split(r["study_region_global"]))]
        if r["study_region_global"] else []}
for c in TAG_COLS:
    dims.setdefault(c, lambda r, c=c: split(r[c]))
for name, fn in dims.items():
    g = collections.defaultdict(list)
    for r in tags:
        for v in fn(r) or ["(none)"]:
            g[v].append(r["doi"].lower())
    write_csv(AGG / f"by_{name}.csv", AGG_HEADER, group_rows(g))

g = collections.defaultdict(list)
for r in tags:
    for v in split(r["ethical_theme"]):
        for y in [r["year"]]:
            g[f"{y}|{v}"].append(r["doi"].lower())
write_csv(AGG / "by_year_x_ethical_theme.csv", AGG_HEADER, group_rows(g))

for a, b in (("year", "journal"), ("study_region_global_combination", "application_domain"),
             ("study_region_continent", "spatial_resolution")):
    g = collections.defaultdict(list)
    for r in tags:
        for va in dims[a](r) or ["(none)"]:
            for vb in dims[b](r) or ["(none)"]:
                g[f"{va}|{vb}"].append(r["doi"].lower())
    write_csv(AGG / f"by_{a}_x_{b}.csv", AGG_HEADER, group_rows(g))

# Study region vs first-author country: descriptive metadata only, no audit content.
m = collections.Counter()
for r in tags:
    fa = (split(r["first_author_country"]) or ["(none)"])[0]
    for s in split(r["study_region"]) or ["(none)"]:
        m[(s, fa)] += 1
write_csv(AGG / "study_region_x_first_author_country.csv",
          ["study_region", "first_author_country", "n_papers"],
          [[s, a, n] for (s, a), n in sorted(m.items(), key=lambda kv: -kv[1])])

# ---- data/summary.json --------------------------------------------------------------

n_tr = sum(p["n"] for p in paper.values())
inst = collections.Counter()
prov_ei = collections.Counter()
for (ht, rel, tt, st, pv, qv), n in status_tab.items():
    inst[st] += n
    if tt == "EthicalImpact":
        prov_ei[pv] += n
cchain = json.load(open(SRC / "ablation_consistency/reports/corpus_cchain_report.json"))["combined"]
summary = {
    "n_papers_corpus": len(tags),
    "n_papers_audited": len(paper),
    "n_papers_with_triples": sum(p["n"] > 0 for p in paper.values()),
    "n_triples": n_tr,
    "n_distinct_risk_mechanisms": len({k[1] for k in ent_stats if k[0] == "RiskMechanism"}),
    "n_distinct_ethical_impacts": len({k[1] for k in ent_stats if k[0] == "EthicalImpact"}),
    "share_ethical_keyword": round(sum(bool(r["ethical_theme"]) for r in tags) / len(tags), 4),
    "instantiation_share": {k: round(v / n_tr, 4) for k, v in inst.items()},
    "provenance_share_edges_to_impact": {k: round(v / sum(prov_ei.values()), 4)
                                         for k, v in prov_ei.items()},
    "connected_rate": cchain["connected_rate_mean"],
    "closure_rate": cchain["closure_rate_mean"],
    "suppression_k_min": K_MIN,
}
(OUT / "data/summary.json").write_text(json.dumps(summary, indent=2))

# ---- data/benchmark : rating and ablation aggregates --------------------------------

rows = []
for f in sorted(glob.glob(str(SRC / "benchmark_100_500/ratings_*/*.json"))
                + glob.glob(str(SRC / "ablation_consistency/ratings/*.json"))):
    d = json.load(open(f))
    rows.append([Path(f).parent.name, Path(f).stem, d["expert"], d["total_triples"],
                 d["scored_triples"]]
                + [round(d["counts"][a]["pass"] / max(1, d["counts"][a]["pass"] + d["counts"][a]["fail"]), 4)
                   for a in ("ground", "causal", "verdict")])
write_csv(OUT / "data/benchmark/llm_judge_pass_rates.csv",
          ["set", "file", "judge", "total_triples", "scored_triples", "ground", "causal", "verdict"], rows)
for name in ("kg_ablation_report", "kgoff_vs_kgon_jaccard", "consistency_report_gemini",
             "corpus_cchain_report"):
    shutil.copy(SRC / f"ablation_consistency/reports/{name}.json", OUT / f"data/benchmark/{name}.json")

# ---- knowledge_graph : drop verbatim `evidence` from the 28 source documents --------

KG_SRC, KG = SRC / "knowledge_graph", OUT / "knowledge_graph"
KG.mkdir(parents=True, exist_ok=True)
ev_key = re.compile(r'<key id="(\w+)"[^>]*attr\.name="evidence"[^>]*/>')
for g in ("geoai_knowledge_merged_hier_merged_consensus_hier.graphml",
          "geoai_knowledge_merged_hier_merged_consensus.graphml"):
    x = (KG_SRC / g).read_text(encoding="utf-8")
    for kid in ev_key.findall(x):
        x = re.sub(rf'\s*<data key="{kid}">.*?</data>', "", x, flags=re.S)
    x = ev_key.sub("", x)
    (KG / g).write_text(x, encoding="utf-8")
for name in ("triples.json", "triples_resolved_consensus.json"):
    t = json.load(open(KG_SRC / name))
    for tr in t:
        tr["edge"].pop("evidence", None)
    (KG / name).write_text(json.dumps(t, ensure_ascii=False, indent=1))
for name in ("entity_resolution_consensus.json", "hierarchy_consensus.json", "source_documents.txt"):
    shutil.copy(KG_SRC / name, KG / name)
shutil.copytree(KG_SRC / "entity_resolution_per_model", KG / "entity_resolution_per_model",
                dirs_exist_ok=True)

# ---- prompts : every template string handed to the LLMs -----------------------------

PROMPT_FILES = {"audit_agent_fast.py": "geoai_audit/agent/audit_agent_fast.py",
                "build_graph.py": "geoai_audit/pipeline/build_graph.py",
                "entity_resolution.py": "geoai_audit/pipeline/entity_resolution.py",
                "llm_judge.py": "geoai_audit/evaluation/llm_judge.py"}
PROMPT_ROLES = {"extract_keywords_from_text": "01_preprocess_key_concepts",
                "expand_keywords": "02_preprocess_concept_expansion",
                "_condense": "03_preprocess_contribution_condensation",
                "_emit_audit_triples": "04_audit_reasoner",
                "_instantiation_gate": "05_instantiation_gate",
                "extraction_template": "kg_01_causal_chain_extraction",
                "_RESOLVE_PROMPT": "kg_02_entity_resolution_and_hierarchy",
                "RUBRIC": "eval_codebook_judge_rubric"}
PDIR = OUT / "prompts"
shutil.rmtree(PDIR, ignore_errors=True)
PDIR.mkdir(parents=True)
index = []
for short, rel in PROMPT_FILES.items():
    tree = ast.parse((PROJECT / rel).read_text(encoding="utf-8"))
    consts = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    consts[tgt.id] = node.value.value
    found = []
    for fdef in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)] + [tree]:
        for node in ast.walk(fdef):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "from_template" \
                    and node.args:
                a = node.args[0]
                if isinstance(a, ast.Constant) and fdef is not tree:
                    found.append((fdef.name, a.value))
                elif isinstance(a, ast.Name) and a.id in consts:
                    found.append((a.id, consts[a.id]))
    for name in ("_RESOLVE_PROMPT", "RUBRIC"):
        if name in consts:
            found.append((name, consts[name]))
    for tag, text in dict(found).items():
        if tag not in PROMPT_ROLES:
            continue
        fn = f"{PROMPT_ROLES[tag]}.txt"
        (PDIR / fn).write_text(text.strip() + "\n", encoding="utf-8")
        index.append([fn, rel, len(text)])
write_csv(PDIR / "INDEX.csv", ["file", "source", "n_chars"], index)

# ---- ontology ----------------------------------------------------------------------

(OUT / "ontology").mkdir(exist_ok=True)
for rel in ("geoai_audit/ontology/schema.py", "geoai_audit/ontology/validation.py"):
    shutil.copy(PROJECT / rel, OUT / "ontology" / Path(rel).name)

print(json.dumps(summary, indent=2))
print(f"edges {len(edges)}  entities {len(ents)}  prompts {len(index)}")
