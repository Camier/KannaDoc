"""Entity extraction module for ethnopharmacology documents.

V3.1 Schema - 17 entity types, 16 relationship types.
"""

from lib.entity_extraction.schemas import (
    # Core types
    EntityType,
    RelationType,
    Measurement,
    Entity,
    Relationship,
    ExtractionResult,
    EntityUnion,
    # Ethnographic entities
    Culture,
    UseRecord,
    TraditionalUse,
    Preparation,
    # Botanical entities
    Taxon,
    PlantPart,
    RawMaterial,
    # Chemical entities
    CompoundClass,
    Compound,
    # Pharmacological entities
    Target,
    Effect,
    Condition,
    # Clinical entities
    Evidence,
    Study,
    Dosage,
    AdverseEvent,
    # Commercial entities
    Product,
)
from lib.entity_extraction.prompt import build_messages_v31, SYSTEM_PROMPT_V31
from lib.entity_extraction.extractor import (
    V31Extractor,
    parse_extraction_result,
    normalize_extraction_dict,
)

__all__ = [
    # Core types
    "EntityType",
    "RelationType",
    "Measurement",
    "Entity",
    "Relationship",
    "ExtractionResult",
    "EntityUnion",
    # Ethnographic entities
    "Culture",
    "UseRecord",
    "TraditionalUse",
    "Preparation",
    # Botanical entities
    "Taxon",
    "PlantPart",
    "RawMaterial",
    # Chemical entities
    "CompoundClass",
    "Compound",
    # Pharmacological entities
    "Target",
    "Effect",
    "Condition",
    # Clinical entities
    "Evidence",
    "Study",
    "Dosage",
    "AdverseEvent",
    # Commercial entities
    "Product",
    # Prompt
    "build_messages_v31",
    "SYSTEM_PROMPT_V31",
    # Extractor
    "V31Extractor",
    "parse_extraction_result",
    "normalize_extraction_dict",
]
