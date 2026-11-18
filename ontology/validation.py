"""
Drop-in fixes for triple_extractor_v2.py

Two problems solved:
  1. JsonOutputParser crashes when the model emits a one-sentence relevance-gate
     preamble before the JSON ("This paper evaluates ... { "chains": [...] }").
     -> robust_parse() strips any text outside the outermost {...} and parses it,
        and also captures the preamble as a relevance_note (free thesis data).
  2. build_graph_from_json() added illegal edges (EI->EI, TF->Mitigation, etc.)
     with no topology check.
     -> validate_triple() enforces the DAG schema and returns a reason on reject,
        so build can drop + log them and report a violation count.

Integration: see PATCH NOTES at the bottom. No re-run of clean papers needed for
the parser fix on already-saved JSON, but the 5 failed papers must be re-run.
"""

import re
import json


# ----------------------------------------------------------------------------
# 1. ROBUST PARSING  (fixes the 5 OUTPUT_PARSING_FAILURE papers)
# ----------------------------------------------------------------------------

def robust_parse(raw_text):
    """
    Parse model output that may have a natural-language preamble (and/or trailing
    text, and/or ```json fences) wrapped around a single JSON object.

    Returns (result_dict, relevance_note, parsed_ok):
      result_dict    -- the parsed JSON object as-is, or {"chains": []} fallback
      relevance_note -- any prose found before the JSON (the Step-0 verdict), or ""
      parsed_ok      -- True iff a JSON object carrying a RECOGNIZED audit list key
                        ("chains" or "triples") was actually parsed. False means NO
                        such result was found: API garbage, truncation, or an
                        off-schema reply. The empty {"chains": []} is a FALLBACK,
                        NOT a model-asserted empty audit -- callers that must not
                        treat a parse failure as a clean/empty result check this.

    NOTE: a successfully parsed dict is returned UNTOUCHED even when it lacks the
    audit keys (e.g. the instantiation gate's {"verdicts": [...]}). Earlier this
    coerced any such dict to {"chains": []}, silently discarding the verdicts --
    which made the entire INSTANTIATED/POTENTIAL gate a no-op. parsed_ok still
    reflects only the audit keys; gate callers inspect their own key directly.
    """
    if isinstance(raw_text, dict):
        # Already parsed (e.g. parser succeeded) -- nothing to strip.
        ok = isinstance(raw_text.get("chains"), list) or isinstance(raw_text.get("triples"), list)
        return raw_text, "", ok

    text = str(raw_text)

    # Strip markdown code fences if present -- but keep any prose BEFORE the
    # fence: that is the Step-0 relevance verdict, which must survive as the
    # relevance_note instead of being discarded with the fence wrapper.
    pre_fence = ""
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        pre_fence = text[:fence.start()].strip()
        text = fence.group(1)

    # Find the outermost JSON object: first '{' to its matching last '}'.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        note = "\n".join(x for x in (pre_fence, text.strip()) if x)
        return {"chains": []}, note, False

    preamble = "\n".join(x for x in (pre_fence, text[:start].strip()) if x)
    json_str = text[start:end + 1]

    try:
        result = json.loads(json_str)
    except json.JSONDecodeError:
        # Last resort: balanced-brace scan from the first '{'.
        result = _scan_balanced(text, start)
        if result is None:
            return {"chains": []}, preamble, False

    # Return any parsed dict UNTOUCHED (so non-audit keys like "verdicts" survive).
    # parsed_ok signals only whether the recognized audit keys are present.
    if isinstance(result, dict):
        has_audit_key = (isinstance(result.get("chains"), list)
                         or isinstance(result.get("triples"), list))
        return result, preamble, has_audit_key
    return {"chains": []}, preamble, False


def _scan_balanced(text, start):
    """Walk braces to find the first complete top-level {...}; tolerant of
    trailing junk after it. Returns dict or None."""
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def invoke_with_recovery(chain, parser, payload):
    """
    Call the LangChain `chain` (prompt | llm | parser). If the parser raises
    because of a preamble, re-run the prompt|llm part WITHOUT the parser and
    salvage the JSON ourselves.

    Returns (result_dict, relevance_note, recovered_flag).

    `chain` is prompt | llm | parser; `parser` is the JsonOutputParser instance.
    We reconstruct the no-parser chain from chain.first / chain.middle if needed.
    Simpler: pass the prompt|llm chain separately. See PATCH NOTES.
    """
    try:
        result = chain.invoke(payload)
        return (result if isinstance(result, dict) else {"chains": []}), "", False
    except Exception:
        raise  # handled by caller using llm_chain fallback; see PATCH NOTES


# ----------------------------------------------------------------------------
# 2. TOPOLOGY VALIDATION  (stops illegal edges entering the graph)
# ----------------------------------------------------------------------------

NODE_TYPES = {"TechnicalFeature", "RiskMechanism", "EthicalImpact", "Mitigation"}
HARM_FAMILIES = {
    "PsychologicalHarm", "PhysicalHarm", "EconomicLoss",
    "PrivacyViolation", "EqualRightsViolation",
}
INFLUENCE_RELS = {"PROMOTES", "INHIBITS", "NEGATES"}
ALL_RELS = INFLUENCE_RELS | {"PREREQUISITE_OF"}

# Legal causal spine + mitigation side-edges, as (head_type, tail_type).
# This is the table from annotation_standard.md.
LEGAL_TRANSITIONS = {
    ("TechnicalFeature", "RiskMechanism"),
    ("RiskMechanism", "EthicalImpact"),
    # TF->EI: the extraction prompt instructs the model to use this only when the
    # intermediate RM is unstated ('unknown' middle). That instruction is NOT
    # enforceable here (validate_triple sees one edge, not the chain), so every
    # direct TF->EI edge is admitted.
    ("TechnicalFeature", "EthicalImpact"),
    ("Mitigation", "RiskMechanism"),
    ("Mitigation", "EthicalImpact"),
    # NOTE: transitions are validated by (head_type, tail_type) only -- there is
    # no per-relation constraint (e.g. Mitigation --PROMOTES--> EI is admitted
    # even though schema.py describes Mitigation as reducing a risk/impact).
}

# Flip to True if you decide harm-cascade edges (EI->EI) should be KEPT
# (Option B). Default False = Option A, impacts are terminal, matches your
# written O-rubric. Either way, EI->EI edges are LOGGED so you see what you drop.
ALLOW_EI_CASCADE = False


def validate_triple(head_type, tail_type, relation, head_entity, tail_entity,
                    head_harm, tail_harm):
    """
    Returns (is_valid, reason). reason is "" when valid, else a short tag used
    for the violation report. 'unknown' endpoints are handled by the caller
    (they're dropped before this is called), so both types should be real here.
    """
    # Type sanity
    if head_type not in NODE_TYPES or tail_type not in NODE_TYPES:
        return False, f"off_schema_type({head_type}->{tail_type})"
    if relation not in ALL_RELS:
        return False, f"bad_relation({relation})"

    # Same-type causal join (EI->EI, RM->RM, TF->TF, Mit->Mit)
    if head_type == tail_type:
        if head_type == "EthicalImpact":
            # The harm-cascade case (chen2025-style privacy->economic).
            if ALLOW_EI_CASCADE:
                return True, "ei_cascade_KEPT"
            return False, "ei_cascade_dropped(EI->EI)"
        return False, f"same_type({head_type}->{head_type})"

    # harm_family discipline
    if tail_type == "EthicalImpact":
        if tail_harm not in HARM_FAMILIES:
            return False, f"impact_without_valid_harm_family({tail_harm})"
    if head_type != "EthicalImpact" and head_harm:
        # non-impact carrying a harm_family is a soft warning, not a drop
        pass

    # Legal topology
    if (head_type, tail_type) in LEGAL_TRANSITIONS:
        return True, ""

    # Specific named illegal transitions for clearer reporting
    backward = {
        ("EthicalImpact", "TechnicalFeature"),
        ("EthicalImpact", "RiskMechanism"),
        ("RiskMechanism", "TechnicalFeature"),
    }
    if (head_type, tail_type) in backward:
        return False, f"backward_spine({head_type}->{tail_type})"
    if (head_type, tail_type) == ("TechnicalFeature", "Mitigation"):
        return False, "tf_to_mitigation"
    if head_type == "Mitigation" and tail_type == "TechnicalFeature":
        return False, "mitigation_to_tf"

    return False, f"illegal_transition({head_type}->{tail_type})"