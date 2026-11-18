"""
GeoAI Ethics Ontology (schema definitions).

STRUCTURE: adapts the bow-tie risk model to GeoAI ethics.
  TechnicalFeature (cause) -> RiskMechanism (central event) -> EthicalImpact (consequence)
  Mitigation = barriers/controls, attaching to a RiskMechanism or an EthicalImpact.

NODES:
  - TechnicalFeature: a concrete algorithm, model, hardware, data attribute, or
    processing step. The cause side of the bow-tie.
  - RiskMechanism: the process by which a technical feature generates a societal/
    human risk; the bow-tie central event (the "how harm arises", not the harm).
  - EthicalImpact: the realized harm to humans/society. MUST be assignable to exactly
    one of five harm families: PsychologicalHarm, PhysicalHarm, EconomicLoss,
    PrivacyViolation, EqualRightsViolation (recorded in `harm_family`). If a candidate
    impact fits no family, it is NOT an EthicalImpact and must not be extracted.
  - Mitigation: a barrier/control that reduces a RiskMechanism or an EthicalImpact.

EDGES are of two families.
  Family 1 - INFLUENCE, described by (sign, magnitude):
    - PROMOTES        (+, partial): A increases the likelihood or severity of B.
    - INHIBITS        (-, partial): A decreases the likelihood or severity of B.
    - NEGATES         (-, total):   A reduces B to impossibility; the absolute
                                    endpoint of INHIBITS.
    - The (+, total) cell ("A guarantees B") is intentionally EXCLUDED: categorical
      causation of a downstream ethical harm is not an attestable claim type in the
      literature, so no such relation is defined.
  Family 2 - DEPENDENCY (no sign/magnitude):
    - PREREQUISITE_OF: B structurally requires A to exist or function; a logical/
      enabling precondition, NOT a causal influence.

CONDITION is an edge annotation (not a relation): the circumstance under which an
edge holds ("General" if unconditional), including impact scope (individual/local/
global) where the text states it.
"""
from pydantic import BaseModel, Field
from typing import List, Optional

class Node(BaseModel):
    entity: str = Field(description="The core concept, or 'unknown' if missing")
    type: str = Field(description="Must be TechnicalFeature, RiskMechanism, EthicalImpact, or Mitigation")
    harm_family: Optional[str] = Field(
        default=None,
        description="ONLY for EthicalImpact nodes: exactly one of "
        "[PsychologicalHarm, PhysicalHarm, EconomicLoss, PrivacyViolation, EqualRightsViolation]. "
        "null for all other node types."
    )

class Edge(BaseModel):
    relation_type: str = Field(description="Must be PROMOTES, INHIBITS, PREREQUISITE_OF, or NEGATES")
    condition: str = Field(description="The specific context/condition under which this holds. 'General' if unconditional.")
    evidence: str = Field(description="Short quote from the text supporting this relationship.")

class PropertyGraphTriple(BaseModel):
    head: Node
    edge: Edge
    tail: Node

class Chain(BaseModel):
    steps: List[PropertyGraphTriple]

class ExtractionResult(BaseModel):
    chains: List[Chain]
    