"""Render public_release/index.html from the built release (run after build_release.py)."""
import csv
import gzip
import html
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]
S = json.loads((OUT / "data/summary.json").read_text())


def rows(p):
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def size(p):
    n = p.stat().st_size
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.1f} kB" if n < 1000 else f"{n / 1e3:.0f} kB"


FILES = [
    ("Corpus", [
        ("data/papers.csv", "Bibliographic IDs of all 15,492 papers: DOI, year, journal, title, article type, text source (full text / abstract), audit corpus, audited flag."),
        ("data/paper_tags.csv", "Descriptive metadata per paper (sensor, spatial resolution, study region and scope, continent, Global North/South, affected population, application domain, GeoAI method, author ethical keyword theme, first-author country). Not audit output."),
    ]),
    ("Audit aggregates", [
        ("data/summary.json", "Corpus-level figures reported in Section 4."),
        ("data/aggregates/edges.csv.gz", "Every distinct audited causal edge (head, relation, tail, harm family) with triple and paper counts, by instantiation label and provenance."),
        ("data/aggregates/entities.csv.gz", "Every distinct audited entity with paper counts, head/tail role counts and instantiation labels."),
        ("data/aggregates/triples_by_type_status.csv", "Triple counts by topology, instantiation label, provenance and quote-verification status."),
        ("data/aggregates/by_year.csv", "Per publication year: papers, audited papers, papers with triples, triples, papers with a mitigation, papers per harm family."),
        ("data/aggregates/by_journal.csv", "Same columns per journal."),
        ("data/aggregates/by_*.csv", "Same columns per value of every metadata field, plus cross-tabs year × journal, year × ethical theme, Global North/South × application domain, continent × spatial resolution."),
        ("data/aggregates/study_region_x_first_author_country.csv", "Study-region country × first-author country paper counts (metadata only)."),
    ]),
    ("Verification and ablation", [
        ("data/benchmark/llm_judge_pass_rates.csv", "Pass rates of each model annotator on groundedness, causal validity and verdict correctness for the 100- and 500-paper samples, the no-KG ablation and the repeat run."),
        ("data/benchmark/kg_ablation_report.json", "Structural metrics and provenance with and without the knowledge graph."),
        ("data/benchmark/kgoff_vs_kgon_jaccard.json", "Run-to-run Jaccard agreement (harm families, concepts, triples) across the no-KG run and two KG runs."),
        ("data/benchmark/corpus_cchain_report.json", "Connected and closure rates per audit corpus."),
    ]),
    ("Knowledge graph", [
        ("knowledge_graph/geoai_knowledge_merged_hier_merged_consensus_hier.graphml", "The causal knowledge graph used by the audit, including the IS_A layer."),
        ("knowledge_graph/geoai_knowledge_merged_hier_merged_consensus.graphml", "The causal skeleton before the IS_A layer."),
        ("knowledge_graph/triples.json", "Causal triples extracted from the 28 source documents, before entity alignment."),
        ("knowledge_graph/triples_resolved_consensus.json", "The same triples after entity alignment."),
        ("knowledge_graph/entity_resolution_consensus.json", "Embedding-proposed candidate synonym groups and the final merges."),
        ("knowledge_graph/entity_resolution_per_model/", "Independent merge and hypernym decisions of each of the three models, with a disagreement report."),
        ("knowledge_graph/hierarchy_consensus.json", "IS_A links of the concept hierarchy."),
        ("knowledge_graph/source_documents.txt", "The 28 source documents."),
    ]),
    ("Method", [
        ("ontology/schema.py", "Ontology node, edge and output schema."),
        ("ontology/validation.py", "Admissible-topology rules enforced at every stage."),
        ("prompts/", "Every prompt sent to a language model: preprocessing, audit reasoner, instantiation gate, KG extraction, entity resolution, and the annotation codebook used by annotators."),
        ("scripts/build_release.py", "The script that produced this release from the private audit outputs."),
    ]),
]


def file_rows():
    out = []
    for group, items in FILES:
        out.append(f'<tr class="grp"><th colspan="3">{group}</th></tr>')
        for path, desc in items:
            p = OUT / path
            if path.endswith("/") or "*" in path:
                meta = ""
            else:
                meta = size(p) + (f" · {rows(p):,} rows" if p.suffix in (".csv", ".gz") else "")
            link = path if "*" not in path else "data/aggregates/"
            out.append(f'<tr><td><a href="{link}"><code>{html.escape(path)}</code></a></td>'
                       f'<td>{html.escape(desc)}</td><td class="meta">{meta}</td></tr>')
    return "\n".join(out)


# Build the catalogue from actual public files, so all links work on static hosts.
import zipfile

GROUPS = {"Corpus": "corpus", "Audit aggregates": "aggregates", "Verification and ablation": "validation", "Knowledge graph": "graph", "Method": "method"}
DESCRIPTIONS = {path: desc for _, items in FILES for path, desc in items}
TITLES = {
    "data/papers.csv": "Paper catalogue", "data/paper_tags.csv": "Descriptive paper metadata",
    "data/summary.json": "Corpus summary", "data/aggregates/edges.csv.gz": "Aggregated causal edges",
    "data/aggregates/entities.csv.gz": "Aggregated entities",
    "data/aggregates/triples_by_type_status.csv": "Triple topology & status",
    "knowledge_graph/geoai_knowledge_merged_hier_merged_consensus_hier.graphml": "Audit knowledge graph",
    "knowledge_graph/geoai_knowledge_merged_hier_merged_consensus.graphml": "Causal graph before hierarchy",
    "data/benchmark/llm_judge_pass_rates.csv": "Model annotator pass rates",
    "data/benchmark/kg_ablation_report.json": "Knowledge-graph ablation",
    "data/benchmark/kgoff_vs_kgon_jaccard.json": "Run-to-run agreement",
    "data/benchmark/corpus_cchain_report.json": "Causal-chain structure",
    "data/benchmark/coverage_thresholds.csv": "Coverage by evidence threshold · Appendix A2",
    "data/benchmark/coverage_sensitivity.csv": "High-frequency edge sensitivity · Appendix A2",
    "data/benchmark/pipeline_comparison.csv": "Human-reference pipeline comparison · Appendix A1",
    "data/benchmark/pipeline_comparison_summary.json": "Comparison metrics & confidence intervals",
    "data/benchmark/external_controls.json": "External controls · Appendix A3",
    "data/benchmark/supplementary_notes.md": "Supplementary experiment definitions & limitations",
    "methods/workflow_example.md": "Worked audit example · Supplementary S1",
    "methods/Supplementary_Material.pdf": "Supplementary Material · S1–S2 (PDF)",
}
DESCRIPTIONS.update({
    "data/benchmark/coverage_thresholds.csv": "Ten evidence thresholds with paper counts and both corpus/completed-audit denominators; an instantiation label does not establish observed harm.",
    "data/benchmark/coverage_sensitivity.csv": "Recomputed coverage after fixed top-k risk-edge removal and exploratory opacity lexical filtering.",
    "data/benchmark/pipeline_comparison.csv": "Four configurations on 100 papers: expert-reference recovery, schema conformance and quote/graph anchoring. Rates are proportions.",
    "data/benchmark/pipeline_comparison_summary.json": "Aggregate human-reference metrics, paired confidence intervals, diagnostics and separately reported model ratings; no paper-level findings.",
    "data/benchmark/external_controls.json": "Aggregate non-AI EO, unrelated-text and three-run paired-abstract controls, including limitations of instantiation discrimination.",
    "data/benchmark/supplementary_notes.md": "Definitions, sample sizes, confidence intervals, source provenance and interpretation limits for Appendices A1–A3.",
    "methods/Supplementary_Material.pdf": "Supplementary Material requested in peer review: S1 worked example of the ontology-grounded audit and S2 literature search.",
    "methods/workflow_example.md": "Paraphrased Supplementary S1 walkthrough with three saved gate outcomes and expert/model disagreement; a selected exception to aggregate-only corpus findings.",
})
paths = [p for folder in ("data", "knowledge_graph", "prompts", "ontology", "methods")
         for p in sorted((OUT / folder).rglob("*"))
         if p.is_file() and not p.name.startswith(".") and "__pycache__" not in p.parts]
paths.append(OUT / "scripts/build_release.py")
priority = ["data/papers.csv", "data/paper_tags.csv", "data/summary.json",
            "data/aggregates/edges.csv.gz", "data/aggregates/entities.csv.gz",
            "data/aggregates/by_year.csv", "data/aggregates/by_journal.csv",
            "data/aggregates/triples_by_type_status.csv"]
paths.sort(key=lambda p: (priority.index(p.relative_to(OUT).as_posix())
                         if p.relative_to(OUT).as_posix() in priority else len(priority),
                         p.relative_to(OUT).as_posix()))
catalogue = []
for p in paths:
    path = p.relative_to(OUT).as_posix()
    group = ("validation" if path.startswith("data/benchmark/") else
             "aggregates" if path.startswith("data/aggregates/") or path == "data/summary.json" else
             "corpus" if path.startswith("data/") else "graph" if path.startswith("knowledge_graph/") else "method")
    label = p.name.removesuffix(".csv.gz").removesuffix(p.suffix).removeprefix("by_").replace("_x_", " × ").replace("_", " ")
    desc = DESCRIPTIONS.get(path)
    if not desc:
        desc = (f"Paper and audit counts grouped by {label}, including mitigation and recorded harm families where applicable." if group == "aggregates" else
                "Released model prompt template, provided as plain text for inspection and reuse." if path.startswith("prompts/") else
                "Independent model decisions and supporting records for entity alignment and concept hierarchy.")
    title = TITLES.get(path, label.capitalize()).replace("Geoai", "GeoAI").replace("geoai", "GeoAI")
    item = {"path": path, "group": group, "title": title,
            "description": desc, "size": size(p), "format": "CSV.GZ" if p.suffix == ".gz" else p.suffix[1:].upper()}
    if p.suffix in (".csv", ".gz"):
        opener = gzip.open if p.suffix == ".gz" else open
        with opener(p, "rt", encoding="utf-8", newline="") as f:
            reader = csv.reader(f); item["columns"] = next(reader); sample = []; count = 0
            for row in reader:
                count += 1
                if len(sample) < 5: sample.append(row)
            item.update(rows=count, sample=sample)
    elif p.suffix != ".pdf":
        item["preview"] = p.read_text(encoding="utf-8")[:4000]
    catalogue.append(item)

def render_row(item):
    e = html.escape; path = e(item["path"], quote=True)
    meta = item["size"] + (f" · {item['rows']:,} rows" if "rows" in item else "")
    return f'''<tr data-group="{item['group']}" data-path="{path}">
    <td><span class="file-format">{e(item['format'])}</span></td>
    <td><a class="file-title" href="{path}" download>{e(item['title'])}</a><p class="file-desc">{e(item['description'])}</p><code class="file-path">{path}</code></td>
    <td class="file-meta">{e(meta)}</td><td class="file-actions"><button class="preview-button" type="button" data-preview="{path}">Preview</button><a class="download-icon" href="{path}" download aria-label="Download {e(item['title'], quote=True)}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/></svg></a></td></tr>'''

with open(OUT / "data/aggregates/by_year.csv", newline="") as f:
    annual = sorted(list(csv.DictReader(f)), key=lambda r: int(r["value"]))
filters = f'<button class="filter active" data-filter="all" aria-pressed="true">All files <span>{len(catalogue)}</span></button>'
for label, g in GROUPS.items():
    count = sum(x["group"] == g for x in catalogue)
    filters += f'<button class="filter" data-filter="{g}" aria-pressed="false">{label} <span>{count}</span></button>'
(OUT / "downloads").mkdir(exist_ok=True)
archive = OUT / "downloads/geoai-ethics-data.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in paths + [OUT / "README.md", OUT / "LICENSE"]:
        z.write(p, arcname="geoai-ethics-data/" + p.relative_to(OUT).as_posix())
payload = json.dumps({"summary": S, "annual": annual, "files": catalogue}, ensure_ascii=False).replace("<", "\\u003c")
tokens = {"@@PAYLOAD@@": payload, "@@ROWS@@": "\n".join(map(render_row, catalogue)), "@@FILTERS@@": filters,
          "@@FILE_COUNT@@": str(len(catalogue)), "@@START_YEAR@@": annual[0]["value"], "@@END_YEAR@@": annual[-1]["value"],
          "@@ARCHIVE_SIZE@@": size(archive)}
page = (OUT / "scripts/page.html").read_text(encoding="utf-8")
for token, value in tokens.items(): page = page.replace(token, value)
(OUT / "index.html").write_text(page, encoding="utf-8")
print(f"Built index.html: {len(catalogue)} files; archive {size(archive)}")
