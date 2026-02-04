"""LAYRA V3.1 entity/relationship schema.

This module defines the canonical Pydantic models for the extraction output used by
LAYRA's ethnopharmacology RAG system.

Design goals
- Property-graph friendly: entities + relationships with rich edge attributes.
- Hybrid schema: stable, generalizable core + domain detail via `attributes`.
- Ethnobotany n-ary claims: UseRecord reifies Culture+Taxon+Part+Prep+Purpose.
- Study connectivity: relationships ensure Study nodes are never orphaned.

Notes
- Most domain-specific details live in `attributes` to keep the core schema stable.
- Confidence is interpreted as *extraction confidence*, not epistemic truth.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union

from typing_extensions import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

CONFIDENCE_VERIFIED_THRESHOLD: float = 0.7

# -----------------------------------------------------------------------------
# Shared value objects
# -----------------------------------------------------------------------------


class Measurement(BaseModel):
    """Structured quantitative measurement.

    Used as a value object inside relationship.attributes, e.g.
    - CONTAINS.attributes["measurement"] for composition/content.
    - ACTS_ON.attributes["measurement"] for potency/affinity.

    Examples
    - {"value": 0.3, "unit": "%", "measurement_type": "content"}
    - {"value": 2.5, "unit": "uM", "measurement_type": "IC50"}
    """

    model_config = ConfigDict(extra="ignore")

    value: float
    unit: str
    measurement_type: str  # "content" | "IC50" | "EC50" | "Ki" | "LD50" | ...
    notes: Optional[str] = None


# -----------------------------------------------------------------------------
# Entity models
# -----------------------------------------------------------------------------

EntityType = Literal[
    # Ethnographic
    "Culture",
    "UseRecord",
    "TraditionalUse",
    "Preparation",
    # Botanical
    "Taxon",
    "PlantPart",
    "RawMaterial",
    # Chemical
    "CompoundClass",
    "Compound",
    # Pharmacological
    "Target",
    "Effect",
    "Condition",
    # Clinical
    "Evidence",
    "Study",
    "Dosage",
    "AdverseEvent",
    # Commercial
    "Product",
]


class Entity(BaseModel):
    """Base node type for the knowledge graph."""

    model_config = ConfigDict(extra="ignore")

    id: str
    type: EntityType
    name: str

    # Hybrid extension point
    attributes: Dict[str, Any] = Field(default_factory=dict)

    # Provenance
    source_chunk_ids: List[str] = Field(default_factory=list)

    # Extraction metadata
    confidence: Optional[float] = None  # 0.0–1.0
    evidence: Optional[str] = None      # short quote/snippet

    # Auto-derived helper flag
    verified: bool = True

    @model_validator(mode="after")
    def _auto_set_verified(self) -> "Entity":
        # Do not force verified=True; only downgrade when confidence is low.
        if self.confidence is not None and self.confidence < CONFIDENCE_VERIFIED_THRESHOLD:
            self.verified = False
            # Mark for follow-up without breaking downstream code.
            if isinstance(self.attributes, dict):
                self.attributes.setdefault("verification_needed", True)
        return self


# --- Ethnographic ------------------------------------------------------------


class Culture(Entity):
    """Ethnic group or community with traditional plant knowledge."""

    type: Literal["Culture"] = "Culture"


class UseRecord(Entity):
    """Reified ethnobotanical use instance.

    Binds: Culture + (Taxon/Material) + (PlantPart/Preparation/RawMaterial) + Purpose.

    Typical attributes
    - route: "oral" | "topical" | ...
    - administration_method_text: free text
    - context: ritual/medicinal/food/etc.
    """

    type: Literal["UseRecord"] = "UseRecord"


class TraditionalUse(Entity):
    """Traditional medicinal application/purpose (the 'what for')."""

    type: Literal["TraditionalUse"] = "TraditionalUse"


class Preparation(Entity):
    """Method of processing plant material (the 'how')."""

    type: Literal["Preparation"] = "Preparation"


# --- Botanical ---------------------------------------------------------------


class Taxon(Entity):
    """Taxonomic entity: species, genus, or family."""

    type: Literal["Taxon"] = "Taxon"


class PlantPart(Entity):
    """Unprocessed anatomical plant part."""

    type: Literal["PlantPart"] = "PlantPart"


class RawMaterial(Entity):
    """Processed plant material ready for use or extraction."""

    type: Literal["RawMaterial"] = "RawMaterial"


# --- Chemical ----------------------------------------------------------------


class CompoundClass(Entity):
    """Chemical category/class of compounds."""

    type: Literal["CompoundClass"] = "CompoundClass"


class Compound(Entity):
    """Specific chemical molecule."""

    type: Literal["Compound"] = "Compound"


# --- Pharmacological ---------------------------------------------------------


class Target(Entity):
    """Biological target: protein, receptor, enzyme, pathway, or process."""

    type: Literal["Target"] = "Target"


class Effect(Entity):
    """Pharmacological effect at any level.

    Effect level and valence are stored in attributes:
    - attributes.level: "molecular"|"cellular"|"systemic"|"behavioral"
    - attributes.valence: "positive"|"negative"|"neutral"
    """

    type: Literal["Effect"] = "Effect"


class Condition(Entity):
    """Disease, disorder, symptom, or wellness state."""

    type: Literal["Condition"] = "Condition"


# --- Clinical ----------------------------------------------------------------


class Evidence(Entity):
    """Evidence type/quality category (e.g., in vitro, RCT, meta-analysis)."""

    type: Literal["Evidence"] = "Evidence"


class Study(Entity):
    """Specific research study instance."""

    type: Literal["Study"] = "Study"


class Dosage(Entity):
    """Dosage regimen with clinical detail.

    Canonical keys in attributes (when extractable):
    - amount (float), unit (str), frequency (str), duration (str), route (str)
    """

    type: Literal["Dosage"] = "Dosage"


class AdverseEvent(Entity):
    """Side effect or adverse reaction (clinical harms)."""

    type: Literal["AdverseEvent"] = "AdverseEvent"


# --- Commercial --------------------------------------------------------------


class Product(Entity):
    """Commercial product or standardized extract."""

    type: Literal["Product"] = "Product"


# Discriminated union for parsing entity lists.
EntityUnion = Annotated[
    Union[
        Culture,
        UseRecord,
        TraditionalUse,
        Preparation,
        Taxon,
        PlantPart,
        RawMaterial,
        CompoundClass,
        Compound,
        Target,
        Effect,
        Condition,
        Evidence,
        Study,
        Dosage,
        AdverseEvent,
        Product,
    ],
    Field(discriminator="type"),
]


# -----------------------------------------------------------------------------
# Relationship models
# -----------------------------------------------------------------------------

RelationType = Literal[
    # Ethnobotanical
    "HAS_USE",        # Culture → UseRecord
    "INVOLVES",       # UseRecord → (Taxon|PlantPart|Preparation|RawMaterial|TraditionalUse)

    # Botanical / Processing
    "HAS_PART",       # Taxon → PlantPart
    "TRANSFORMS",     # Preparation → RawMaterial

    # Chemical
    "CONTAINS",       # (Taxon|PlantPart|RawMaterial|Product) → Compound
    "HAS_CLASS",      # Compound → CompoundClass

    # Pharmacological
    "ACTS_ON",        # Compound → Target
    "PRODUCES",       # (Compound|Effect) → Effect

    # Clinical / Safety
    "TREATS",         # (Compound|Effect|RawMaterial|Product) → Condition
    "SUGGESTS",       # (TraditionalUse|Evidence|UseRecord) → Condition
    "CAUSES",         # (Compound|RawMaterial|Product) → AdverseEvent
    "INTERACTS_WITH", # Compound ↔ Compound (bidirectional)

    # Study
    "HAS_EVIDENCE",   # Study → Evidence
    "STUDIES",        # Study → (Taxon|Compound|RawMaterial|Product)
    "TESTED_AT",      # Study → Dosage
    "REPORTS",        # Study → (Effect|Condition|AdverseEvent|Target)
]


class Relationship(BaseModel):
    """Edge between two entities."""

    model_config = ConfigDict(extra="ignore")

    id: str
    type: RelationType
    source_entity_id: str
    target_entity_id: str

    # Hybrid extension point
    attributes: Dict[str, Any] = Field(default_factory=dict)

    # Extraction metadata
    confidence: Optional[float] = None
    evidence: Optional[str] = None

    # Provenance
    source_chunk_ids: List[str] = Field(default_factory=list)

    # Optional explicit support linkage
    supporting_study_ids: List[str] = Field(default_factory=list)

    # Auto-derived helper flag
    verified: bool = True

    @model_validator(mode="after")
    def _auto_set_verified(self) -> "Relationship":
        if self.confidence is not None and self.confidence < CONFIDENCE_VERIFIED_THRESHOLD:
            self.verified = False
            if isinstance(self.attributes, dict):
                self.attributes.setdefault("verification_needed", True)
        return self

    @property
    def is_bidirectional(self) -> bool:
        return self.type == "INTERACTS_WITH"

    def canonical_pair(self) -> Tuple[str, str]:
        """Canonical (source, target) for bidirectional edges.

        For INTERACTS_WITH, returns the lexicographically ordered pair.
        For other relationships, returns (source_entity_id, target_entity_id).
        """

        if self.type != "INTERACTS_WITH":
            return (self.source_entity_id, self.target_entity_id)
        a, b = self.source_entity_id, self.target_entity_id
        return (a, b) if a <= b else (b, a)


# -----------------------------------------------------------------------------
# Extraction container
# -----------------------------------------------------------------------------


class ExtractionResult(BaseModel):
    """Top-level extraction payload."""

    model_config = ConfigDict(extra="ignore")

    entities: List[EntityUnion] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)


__all__ = [
    "CONFIDENCE_VERIFIED_THRESHOLD",
    "Measurement",
    "EntityType",
    "Entity",
    "Culture",
    "UseRecord",
    "TraditionalUse",
    "Preparation",
    "Taxon",
    "PlantPart",
    "RawMaterial",
    "CompoundClass",
    "Compound",
    "Target",
    "Effect",
    "Condition",
    "Evidence",
    "Study",
    "Dosage",
    "AdverseEvent",
    "Product",
    "EntityUnion",
    "RelationType",
    "Relationship",
    "ExtractionResult",
]
