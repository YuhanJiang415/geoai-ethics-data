# GeoAI Ethics Audit — public data release

Open `index.html` directly in a browser. The site also works on static hosting,
including hosting below a subdirectory; all links and assets are relative.
There are no external fonts, analytics, CDNs, build dependencies or API requests.

The portal centres on dataset downloads and an interactive worked ethics-audit
example. Four entry cards introduce the corpus, aggregate pathways, knowledge
graph and method resources. The complete searchable catalogue is expandable.
The worked example switches between potential privacy risk, an instantiated
mechanism, an implemented mitigation and a not-triggered comparison. Optional
reading contains workflow/verification notes, temporal context and experiment
links. File previews, light/dark themes, a citation copy button and a complete
data ZIP are also available. Previews and chart data are embedded in the
page so that they work when opening the HTML from disk.

## Update the portal

After changing public files, run from the project root:

```sh
python3 public_release/scripts/make_page.py
```

This rebuilds `index.html` and `downloads/geoai-ethics-data.zip` from the files
already in this public directory. The archive includes public data, knowledge
graph, prompts, ontology, the original aggregation script and this README.
It never reads or packages private audit outputs.

Edit `scripts/page.html` for page content, `assets/style.css` for presentation,
and `assets/app.js` for browser interactions. Regeneration preserves the design.
Serve or publish the entire `public_release/` directory, not just the HTML file.

## Rebuild the underlying data

`scripts/build_release.py` is the original exporter. Running it requires the
original private project, including `results_final_v2/` and `geoai_audit/` source
modules. It is not needed to build, view or host this portal.

## Release scope

No full texts, abstracts, verbatim quotes or knowledge-graph source passages are included.
Corpus audit outputs are aggregated; corpus audit cells describing fewer than five
papers are blank. A blank is not zero. Supplementary benchmark/control outcomes
retain their stated sample sizes. The paraphrased Supplementary S1 walkthrough
is a selected paper-level example; complete per-paper audit outputs are excluded.
The graph and aggregates retain the five harm families recorded at audit time;
derived six-family and eleven-theme mappings are additional analysis layers.

Data and code licences remain pending author selection. The portal does not
assign a licence or invent a publication DOI.

## Supplementary update — 17 November 2026

Appendices A1–A3 are represented by `data/benchmark/pipeline_comparison.csv`,
`pipeline_comparison_summary.json`, `coverage_thresholds.csv`,
`coverage_sensitivity.csv`, `external_controls.json` and `supplementary_notes.md`.
The last file records definitions, source paths, sample sizes and limitations.
The public Supplementary S1 guide is `methods/workflow_example.md`.
These exports contain aggregate metrics and a paraphrased selected example;
source passages and private per-paper records were not copied.

The page distinguishes any-triple coverage from instantiated risk/impact edges
and complete instantiated paths. Labels do not establish observed harm.
Run 1 and Run 2 map to saved `pipeline_run2` and `pipeline_run3`; the original
372-finding audit is separate. Family recovery is comparable across alternatives;
the experiments do not establish overall detection superiority.

## Page organisation

The main reading path is dataset entry points → worked audit example → complete
file catalogue. Main and supplementary experiment results are supporting files,
not a results dashboard. The example preserves the saved statuses and distinguishes
risk-promoting edges from mitigating edges, quotation checks from instantiation,
and implemented mechanisms from observed harm. Case tabs support arrow keys,
Home and End. Category links open the catalogue automatically.
