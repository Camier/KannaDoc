from typing import List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict

EntityType = Literal[
    "Culture",
    "TraditionalUse",
    "Preparation",
    "Taxon",
    "PlantPart",
    "RawMaterial",
    "CompoundClass",
    "Compound",
    "Concentration",
    "Target",
    "Mechanism",
    "PharmEffect",
    "Indication",
    "Evidence",
    "Study",
]

ENTITY_TYPES = [
    "Culture",
    "TraditionalUse",
    "Preparation",
    "Taxon",
    "PlantPart",
    "RawMaterial",
    "CompoundClass",
    "Compound",
    "Concentration",
    "Target",
    "Mechanism",
    "PharmEffect",
    "Indication",
    "Evidence",
    "Study",
]

RelationType = Literal[
    "TRANSFORMS", "CONTAINS", "ACTS_ON", "PRODUCES", "TREATS", "SUGGESTS"
]

RELATIONSHIP_TYPES = [
    "TRANSFORMS",
    "CONTAINS",
    "ACTS_ON",
    "PRODUCES",
    "TREATS",
    "SUGGESTS",
]

# Mapping of common LLM-generated relationship types to canonical types
RELATIONSHIP_TYPE_ALIASES = {
    "SUPPORTS": "SUGGESTS",
    "CAUSES": "PRODUCES",
    "DERIVES_FROM": "TRANSFORMS",
    "EXTRACTED_FROM": "CONTAINS",
    "INHIBITS": "ACTS_ON",
    "ACTIVATES": "ACTS_ON",
    "BINDS": "ACTS_ON",
    "MODULATES": "ACTS_ON",
    "AFFECTS": "ACTS_ON",
    "INDICATES": "SUGGESTS",
    "IMPLIES": "SUGGESTS",
    "USED_FOR": "TREATS",
    "TREATS_WITH": "TREATS",
    "HAS": "CONTAINS",
    "INCLUDES": "CONTAINS",
    "COMPOSED_OF": "CONTAINS",
    "PART_OF": "CONTAINS",
    "YIELDS": "PRODUCES",
    "GENERATES": "PRODUCES",
    "RESULTS_IN": "PRODUCES",
    "LEADS_TO": "PRODUCES",
    "CONVERTS": "TRANSFORMS",
    "PROCESSES": "TRANSFORMS",
    "PREPARES": "TRANSFORMS",
}


def normalize_relationship_type(rel_type: str) -> str:
    """Normalize relationship type to canonical form.
    
    Maps common LLM-generated relationship types to our 6 canonical types:
    TRANSFORMS, CONTAINS, ACTS_ON, PRODUCES, TREATS, SUGGESTS
    
    Args:
        rel_type: Raw relationship type from LLM
        
    Returns:
        Canonical relationship type (defaults to SUGGESTS if unknown)
    """
    if not rel_type:
        return "SUGGESTS"
    normalized = rel_type.upper().strip()
    if normalized in RELATIONSHIP_TYPES:
        return normalized
    if normalized in RELATIONSHIP_TYPE_ALIASES:
        return RELATIONSHIP_TYPE_ALIASES[normalized]
    return "SUGGESTS"



class Entity(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique ID for this entity instance in the chunk")
    type: str = Field(..., description="Entity type")
    name: str = Field(..., description="The canonical name of the entity")
    attributes: Dict[str, Any] = Field(default_factory=dict)
    source_chunk_ids: List[str] = Field(default_factory=list)


class Culture(Entity):
    type: Literal["Culture"] = "Culture"


class TraditionalUse(Entity):
    type: Literal["TraditionalUse"] = "TraditionalUse"


class Preparation(Entity):
    type: Literal["Preparation"] = "Preparation"


class Taxon(Entity):
    type: Literal["Taxon"] = "Taxon"


class PlantPart(Entity):
    type: Literal["PlantPart"] = "PlantPart"


class RawMaterial(Entity):
    type: Literal["RawMaterial"] = "RawMaterial"


class CompoundClass(Entity):
    type: Literal["CompoundClass"] = "CompoundClass"


class Compound(Entity):
    type: Literal["Compound"] = "Compound"


class Concentration(Entity):
    type: Literal["Concentration"] = "Concentration"


class Target(Entity):
    type: Literal["Target"] = "Target"


class Mechanism(Entity):
    type: Literal["Mechanism"] = "Mechanism"


class PharmEffect(Entity):
    type: Literal["PharmEffect"] = "PharmEffect"


class Indication(Entity):
    type: Literal["Indication"] = "Indication"


class Evidence(Entity):
    type: Literal["Evidence"] = "Evidence"


class Study(Entity):
    type: Literal["Study"] = "Study"


class Relationship(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Unique ID for this relationship")
    type: RelationType = Field(..., description="Relationship type")
    source_entity_id: str = Field(..., description="ID of the source entity")
    target_entity_id: str = Field(..., description="ID of the target entity")
    attributes: Dict[str, Any] = Field(default_factory=dict)


class ExtractionResultV2(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_version: str = Field(default="2.0")
    doc_id: str = Field(...)
    extracted_at: str = Field(...)
    extractor: str = Field(default="Minimax-M2.1")
    entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
