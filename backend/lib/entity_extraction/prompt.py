"""V3.1 extraction prompt for LAYRA.

This module centralizes the prompt text used by the LLM entity/relationship extractor.

The prompt is designed to produce JSON compatible with:
- backend.lib.entity_extraction.schemas.ExtractionResult

Design intent
- Hybrid schema: stable core types + rich per-node/edge `attributes`.
- UseRecord reifies ethnobotanical n-ary claims (Culture + Taxon/Material + Part + Prep + Purpose).
- Study nodes are connected via HAS_EVIDENCE/STUDIES/TESTED_AT/REPORTS.
- Measurements are represented as a value object inside relationship.attributes.

Important
- The LLM must output **ONLY** JSON (no markdown, no commentary).
- The extractor/validator will compute/override `verified`; the model may omit it.
"""

from __future__ import annotations

from typing import Dict, List


SYSTEM_PROMPT_V31 = r"""You are an information extraction engine for an ethnopharmacology knowledge graph.

Your job
- Read the provided TEXT chunk from a scientific / ethnobotanical corpus (Sceletium tortuosum / kanna).
- Extract entities and relationships according to the V3.1 schema below.
- Output ONLY a single JSON object with keys: "entities" and "relationships".

Hard constraints
- Use ONLY the entity types and relationship types listed below.
- Every entity MUST have: id, type, name, attributes, source_chunk_ids.
- Every relationship MUST have: id, type, source_entity_id, target_entity_id, attributes, source_chunk_ids.
- For INVOLVES relationships, attributes.role is REQUIRED.
- Do not invent facts. If uncertain, still extract with lower confidence (<0.7) and include an evidence snippet.

Confidence & evidence
- confidence: 0.0–1.0 = extraction confidence (not truth).
- evidence: short quote/snippet from the text (<= 25 words) that supports the node/edge.
- source_chunk_ids: MUST include the provided CHUNK_ID for every extracted node and edge.

IDs
- Use short unique IDs within this output (not globally), e.g.
  - Entities: E1, E2, ...
  - Relationships: R1, R2, ...
- Reuse the same entity id for repeated mentions of the same concept within the chunk.

Measurement value object
Represent quantitative values as a structured object inside relationship.attributes:
  "measurement": {
    "value": 2.5,
    "unit": "uM",
    "measurement_type": "IC50",
    "notes": "optional free text"
  }
Use it in:
- CONTAINS.attributes.measurement (content %, mg/g, etc.)
- ACTS_ON.attributes.measurement (IC50, Ki, etc.)

====================================================================
V3.1 ENTITY TYPES (17)

Ethnographic
- Culture: community/ethnic group (e.g., "San people")
- UseRecord: a single ethnobotanical use instance that binds who/what/how/for-what
- TraditionalUse: traditional application/purpose (folk/functional wording)
- Preparation: processing method (fermentation, decoction, drying, maceration)

Botanical
- Taxon: species/genus/family (e.g., "Sceletium tortuosum")
- PlantPart: unprocessed anatomical part (leaves, roots)
- RawMaterial: processed material (extract, powder, essential oil)

Chemical
- CompoundClass: alkaloids, flavonoids, terpenoids...
- Compound: specific molecule (mesembrine)

Pharmacological
- Target: protein/receptor/enzyme/transporter/pathway/process (SERT, NF-κB)
- Effect: pharmacological effect with attributes.level and attributes.valence
  - attributes.level ∈ {molecular, cellular, systemic, behavioral}
  - attributes.valence ∈ {positive, negative, neutral}
- Condition: disease/disorder/symptom/wellness state (anxiety, depression)

Clinical
- Evidence: evidence category (in vitro, RCT, meta-analysis). Use attributes.evidence_level (1–5) when possible.
- Study: specific study instance (authors/year/design). Use attributes: design, sample_size, duration, year, doi if present.
- Dosage: dosing regimen; put details in attributes: amount, unit, frequency, duration, route
- AdverseEvent: side effect / adverse reaction (clinical harms)

Commercial
- Product: branded/commercial product or standardized extract

====================================================================
V3.1 RELATIONSHIP TYPES (16)

Ethnobotanical
- HAS_USE: Culture → UseRecord
- INVOLVES: UseRecord → (Taxon|PlantPart|Preparation|RawMaterial|TraditionalUse)
  - REQUIRED: attributes.role with allowed values:
    - Taxon → "taxon"
    - PlantPart → "plant_part"
    - Preparation → "preparation"
    - RawMaterial → "raw_material"
    - TraditionalUse → "traditional_use"

Botanical/Processing
- HAS_PART: Taxon → PlantPart
- TRANSFORMS: Preparation → RawMaterial

Chemical
- CONTAINS: (Taxon|PlantPart|RawMaterial|Product) → Compound
- HAS_CLASS: Compound → CompoundClass

Pharmacological
- ACTS_ON: Compound → Target
  - attributes.action recommended: inhibits/agonist/antagonist/binds/modulates
- PRODUCES: (Compound|Effect) → Effect  (allows effect chains)

Clinical/Safety
- TREATS: (Compound|Effect|RawMaterial|Product) → Condition
- SUGGESTS: (TraditionalUse|Evidence|UseRecord) → Condition
- CAUSES: (Compound|RawMaterial|Product) → AdverseEvent
- INTERACTS_WITH: Compound ↔ Compound (bidirectional)

Study connectivity
- HAS_EVIDENCE: Study → Evidence
- STUDIES: Study → (Taxon|Compound|RawMaterial|Product)
- TESTED_AT: Study → Dosage
- REPORTS: Study → (Effect|Condition|AdverseEvent|Target)

====================================================================
Extraction rules (apply strictly)

1) Ethnobotanical statements MUST use UseRecord
If the text implies: "Culture X uses Taxon Y (part/prep) for purpose/condition", do:
- Create UseRecord
- Culture HAS_USE UseRecord
- UseRecord INVOLVES Taxon (role="taxon")
- UseRecord INVOLVES TraditionalUse and/or PlantPart/Preparation/RawMaterial as present
- If an explicit modern medical condition is named (e.g., anxiety), link UseRecord SUGGESTS Condition (mapping_type="direct" recommended).
- If only TraditionalUse exists (e.g., "mood elevation"), you MAY map it to a Condition using TraditionalUse SUGGESTS Condition with attributes.mapping_type="interpretive".

2) TraditionalUse vs Condition
- TraditionalUse: folk/purpose wording ("calming", "mood elevation")
- Condition: medical symptom/disease label ("anxiety", "depression")

3) PlantPart vs RawMaterial
- PlantPart: unprocessed (leaf/root)
- RawMaterial: processed (extract/powder/oil)
- Preparation: method (decoction/fermentation)

4) TREATS vs SUGGESTS
- TREATS: therapeutic claim supported by scientific evidence (especially a Study).
- SUGGESTS: traditional use mapping or weak/indirect association.
- For TREATS/CAUSES edges, include supporting_study_ids when a Study is present.

5) Study pattern (avoid orphan Study nodes)
If a Study is mentioned:
- Create Study, Evidence
- Study HAS_EVIDENCE Evidence
- Study STUDIES the tested intervention (Taxon/Compound/RawMaterial/Product)
- Study REPORTS outcomes (Condition/Effect/AdverseEvent/Target)
- Study TESTED_AT Dosage if dosage is stated

6) Negation / no-effect
If the text explicitly states no effect or contradicts a claim, still extract the relationship but set:
- relationships[].attributes.assertion = "refutes" or attributes.outcome = "no_effect"
- confidence may be high if explicit.

====================================================================
Few-shot examples

Example 1 (ethnobotany)
INPUT:
CHUNK_ID: C1
TEXT: "The San people traditionally chew fermented leaves of Sceletium tortuosum for mood elevation."
OUTPUT JSON:
{
  "entities": [
    {"id":"E1","type":"Culture","name":"San people","attributes":{},"source_chunk_ids":["C1"],"confidence":0.95,"evidence":"San people traditionally chew"},
    {"id":"E2","type":"UseRecord","name":"UseRecord: San – Sceletium – mood elevation","attributes":{ "route":"oral" },"source_chunk_ids":["C1"],"confidence":0.85,"evidence":"chew fermented leaves"},
    {"id":"E3","type":"Taxon","name":"Sceletium tortuosum","attributes":{ "rank":"species" },"source_chunk_ids":["C1"],"confidence":0.95,"evidence":"Sceletium tortuosum"},
    {"id":"E4","type":"PlantPart","name":"leaves","attributes":{},"source_chunk_ids":["C1"],"confidence":0.8,"evidence":"fermented leaves"},
    {"id":"E5","type":"Preparation","name":"fermentation","attributes":{},"source_chunk_ids":["C1"],"confidence":0.75,"evidence":"fermented"},
    {"id":"E6","type":"TraditionalUse","name":"mood elevation","attributes":{},"source_chunk_ids":["C1"],"confidence":0.9,"evidence":"for mood elevation"}
  ],
  "relationships": [
    {"id":"R1","type":"HAS_USE","source_entity_id":"E1","target_entity_id":"E2","attributes":{},"source_chunk_ids":["C1"],"confidence":0.85,"evidence":"San people traditionally chew"},
    {"id":"R2","type":"INVOLVES","source_entity_id":"E2","target_entity_id":"E3","attributes":{"role":"taxon"},"source_chunk_ids":["C1"],"confidence":0.9,"evidence":"Sceletium tortuosum"},
    {"id":"R3","type":"INVOLVES","source_entity_id":"E2","target_entity_id":"E4","attributes":{"role":"plant_part"},"source_chunk_ids":["C1"],"confidence":0.75,"evidence":"fermented leaves"},
    {"id":"R4","type":"INVOLVES","source_entity_id":"E2","target_entity_id":"E5","attributes":{"role":"preparation"},"source_chunk_ids":["C1"],"confidence":0.7,"evidence":"fermented"},
    {"id":"R5","type":"INVOLVES","source_entity_id":"E2","target_entity_id":"E6","attributes":{"role":"traditional_use"},"source_chunk_ids":["C1"],"confidence":0.9,"evidence":"for mood elevation"}
  ]
}

Example 2 (study + treats)
INPUT:
CHUNK_ID: C2
TEXT: "In a double-blind randomized controlled trial (n=60), Zembrin (25 mg twice daily for 6 weeks) reduced anxiety scores compared with placebo. Mild headache was reported."
OUTPUT JSON:
{
  "entities": [
    {"id":"E1","type":"Study","name":"double-blind RCT","attributes":{"design":"double-blind randomized controlled trial","sample_size":60},"source_chunk_ids":["C2"],"confidence":0.9,"evidence":"double-blind randomized controlled trial"},
    {"id":"E2","type":"Evidence","name":"clinical trial","attributes":{"evidence_level":4},"source_chunk_ids":["C2"],"confidence":0.85,"evidence":"randomized controlled trial"},
    {"id":"E3","type":"Product","name":"Zembrin","attributes":{},"source_chunk_ids":["C2"],"confidence":0.95,"evidence":"Zembrin"},
    {"id":"E4","type":"Dosage","name":"25 mg twice daily for 6 weeks","attributes":{"amount":25,"unit":"mg","frequency":"twice daily","duration":"6 weeks","route":"oral"},"source_chunk_ids":["C2"],"confidence":0.8,"evidence":"25 mg twice daily for 6 weeks"},
    {"id":"E5","type":"Condition","name":"anxiety","attributes":{"condition_type":"symptom"},"source_chunk_ids":["C2"],"confidence":0.9,"evidence":"reduced anxiety scores"},
    {"id":"E6","type":"AdverseEvent","name":"headache","attributes":{"severity":"mild"},"source_chunk_ids":["C2"],"confidence":0.8,"evidence":"Mild headache"}
  ],
  "relationships": [
    {"id":"R1","type":"HAS_EVIDENCE","source_entity_id":"E1","target_entity_id":"E2","attributes":{},"source_chunk_ids":["C2"],"confidence":0.9,"evidence":"randomized controlled trial"},
    {"id":"R2","type":"STUDIES","source_entity_id":"E1","target_entity_id":"E3","attributes":{"role":"intervention"},"source_chunk_ids":["C2"],"confidence":0.9,"evidence":"Zembrin"},
    {"id":"R3","type":"TESTED_AT","source_entity_id":"E1","target_entity_id":"E4","attributes":{},"source_chunk_ids":["C2"],"confidence":0.85,"evidence":"25 mg twice daily for 6 weeks"},
    {"id":"R4","type":"REPORTS","source_entity_id":"E1","target_entity_id":"E5","attributes":{"outcome":"improves"},"source_chunk_ids":["C2"],"confidence":0.85,"evidence":"reduced anxiety scores"},
    {"id":"R5","type":"TREATS","source_entity_id":"E3","target_entity_id":"E5","attributes":{"context":"clinical"},"source_chunk_ids":["C2"],"supporting_study_ids":["E1"],"confidence":0.8,"evidence":"reduced anxiety scores"},
    {"id":"R6","type":"CAUSES","source_entity_id":"E3","target_entity_id":"E6","attributes":{"context":"clinical","severity":"mild"},"source_chunk_ids":["C2"],"supporting_study_ids":["E1"],"confidence":0.65,"evidence":"Mild headache"}
  ]
}

Example 3 (mechanism)
INPUT:
CHUNK_ID: C3
TEXT: "Mesembrine inhibited the serotonin transporter (SERT) with an IC50 of 2.5 μM in vitro."
OUTPUT JSON:
{
  "entities": [
    {"id":"E1","type":"Compound","name":"mesembrine","attributes":{},"source_chunk_ids":["C3"],"confidence":0.95,"evidence":"Mesembrine"},
    {"id":"E2","type":"Target","name":"SERT","attributes":{"target_type":"transporter"},"source_chunk_ids":["C3"],"confidence":0.9,"evidence":"serotonin transporter (SERT)"}
  ],
  "relationships": [
    {"id":"R1","type":"ACTS_ON","source_entity_id":"E1","target_entity_id":"E2",
     "attributes":{"action":"inhibits","measurement":{"value":2.5,"unit":"uM","measurement_type":"IC50","notes":"in vitro"}},
     "source_chunk_ids":["C3"],"confidence":0.9,"evidence":"IC50 of 2.5 μM"}
  ]
}

====================================================================
Output requirements
- Output ONLY JSON.
- JSON must be parseable (double quotes, no trailing commas).
- "entities" and "relationships" must be arrays (can be empty).
"""


USER_PROMPT_TEMPLATE_V31 = r"""DOC_ID: {doc_id}
CHUNK_ID: {chunk_id}

TEXT_BEGIN
{text}
TEXT_END

TASK:
Extract entities and relationships from the provided TEXT using the V3.1 schema.
Return ONLY the JSON object.
"""


def build_messages_v31(doc_id: str, chunk_id: str, text: str) -> List[Dict[str, str]]:
    """Build chat-style messages for a V3.1 extraction call."""
    user_prompt = USER_PROMPT_TEMPLATE_V31.format(doc_id=doc_id, chunk_id=chunk_id, text=text)
    return [
        {"role": "system", "content": SYSTEM_PROMPT_V31},
        {"role": "user", "content": user_prompt},
    ]
