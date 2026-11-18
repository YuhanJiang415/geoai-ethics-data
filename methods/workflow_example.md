# Supplementary S1: a public workflow walkthrough

Updated 17 November 2026. This is a paraphrased reading guide to the saved benchmark findings, not a recovered execution log or a new audit. It includes selected paper-level findings as an explicit exception to the aggregate corpus release. The web page quotes short verbatim sentences from both open-access papers (CC BY-NC-ND 4.0) with attribution; this file does not.

Main example: Hou et al. (2024), Global Streetscapes — A comprehensive dataset of 10 million street-level images across 688 cities for urban science and analytics. DOI: 10.1016/j.isprsjprs.2024.06.023; benchmark paper 026. NOT_TRIGGERED comparison: benchmark paper 060, DOI: 10.1016/j.jag.2024.103731.

1. Ontology (Section 3.2): distinguish a technical feature, an intermediate risk mechanism, a terminal ethical impact, and a mitigation. The privacy example is data fusion → sensitive disclosure → group privacy violation. A causal assertion is conditional; it is not an estimated effect or evidence that harm occurred.
2. Knowledge graph (Section 3.3): the saved retrieval includes privacy, opacity and bias-related edges. Archived matching edges have weight 1 (one supporting document, not a probability); some are lifted hierarchy edges. Exact identity of the archived graph with the historical runtime graph is not established.
3. Audit and gates (Section 3.4): inspect topology, provenance, quotation matching and instantiation separately. A failed initial quotation check marks uncertainty and does not delete the record. A separate verified implementation span can support an instantiation label.
4. Corpus admission (Section 3.5): geospatial imagery plus model-derived attributes establish the substantive GeoAI connection. The saved index and source XML establish benchmark inclusion. The original per-paper relevance-agent response is unavailable; the explanation here is reconstructed.
5. Verification (Section 3.6): exact DOI-plus-suffix identifiers join findings to expert/model labels. Both experts pass all three axes for all six main-example findings. The model fails causal validity only for #1 (algorithmic bias → marginalization and exclusion); groundedness and verdict pass. No separate adjudication of this model dissent is available.

## Three saved gate outcomes

| Case | Saved status | Initial quotation check | Separate instantiation quotation | Meaning |
| --- | --- | --- | --- | --- |
| Paper 026 #4: black-box nature → opacity | INSTANTIATED | Failed | Verified | The audit identifies an implemented opacity mechanism; this does not establish a downstream harm. |
| Paper 026 #2: data fusion → sensitive disclosure | POTENTIAL | Passed | None verified | The technical configuration is documented; a disclosure event is not established. The terminal privacy edge #3 is also POTENTIAL. |
| Paper 060 #2: black-box network → lack of transparency | NOT_TRIGGERED | Failed | None verified | The saved judgment treats an Integrated Gradients explanation module as counterevidence to the unqualified opacity pathway. It does not establish complete transparency. |

Paper 026 #0 is an INSTANTIATED mitigation (data integration inhibits algorithmic bias); implementation of a safeguard does not prove every downstream risk is prevented. A pass on verdict correctness means the assigned label is appropriate, not that the pathway is instantiated. Automatic quotation checks and expert groundedness ratings answer different questions.

## Scope and provenance

Based on supplementary/Supplementary_S1.md and its evidence notes, reconciled with revision_1117/GeoAI_Ethics_Audit_manuscript_1117.accepted.txt. Explanatory summaries are reconstructed. Historical intermediate responses and complete run fingerprints were not recovered. Five saved harm-family labels are distinct from the derived sixth family and eleven themes; final theme-family inclusion rules remain unavailable. No undocumented adjudication, original agent response or harm event is inferred.
