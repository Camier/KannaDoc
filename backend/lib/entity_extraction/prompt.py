"""Extraction prompt template optimized for MiniMax M2.1.

Following MiniMax best practices:
- Clear and specific instructions
- Explain intent ("why") to improve performance
- Focus on examples and details
- Single-task focus (extraction only)
"""


def build_prompt(chunk_text: str, max_length: int = 8000) -> str:
    """Build the extraction prompt for a given text chunk.

    Args:
        chunk_text: The text to extract entities from
        max_length: Maximum text length (truncate if longer)

    Returns:
        Formatted prompt string
    """
    # Truncate if too long to stay within context limits
    if len(chunk_text) > max_length:
        chunk_text = chunk_text[:max_length] + "... [TRUNCATED]"

    return EXTRACTION_PROMPT.format(text=chunk_text)


EXTRACTION_PROMPT = """You are extracting entities for an ethnopharmacology knowledge graph. This data will be used for drug discovery research, so accuracy is critical.

## ENTITY TYPES (15 types across 5 domains)

### Ethnographic Domain
- **Culture**: Ethnic groups, indigenous communities (e.g., "San people", "Khoisan")
- **TraditionalUse**: Traditional medicinal applications (e.g., "chewing for mood elevation")
- **Preparation**: Methods of preparing plant material (e.g., "fermentation", "decoction")

### Botanical Domain
- **Taxon**: Species, genus, or family names (e.g., "Sceletium tortuosum", "Zingiberaceae")
- **PlantPart**: Specific plant parts used (e.g., "roots", "leaves", "bark", "rhizome")
- **RawMaterial**: Processed plant material (e.g., "dried leaf extract", "ethanolic extract")

### Chemical Domain
- **CompoundClass**: Chemical compound categories (e.g., "alkaloids", "flavonoids", "terpenes")
- **Compound**: Specific molecules (e.g., "mesembrine", "curcumin", "quercetin")
- **Concentration**: Quantitative amounts (e.g., "0.3% mesembrine", "IC50 = 2.5 μM")

### Pharmacological Domain
- **Target**: Biological targets (e.g., "SERT", "5-HT2A receptor", "PDE4 enzyme", "COX-2")
- **Mechanism**: Molecular mechanisms (e.g., "serotonin reuptake inhibition", "enzyme inhibition")
- **PharmEffect**: Pharmacological effects (e.g., "anxiolytic", "anti-inflammatory", "analgesic")

### Clinical Domain
- **Indication**: Diseases or conditions (e.g., "anxiety", "depression", "type 2 diabetes")
- **Evidence**: Study evidence type (e.g., "clinical trial", "in vitro", "in vivo", "traditional use")
- **Study**: Study metadata (e.g., "double-blind RCT", "n=45 participants")

## RELATIONSHIP TYPES (6 types)
- **TRANSFORMS**: Preparation → RawMaterial (how preparation creates material)
- **CONTAINS**: Taxon/PlantPart/RawMaterial → Compound (what contains what)
- **ACTS_ON**: Compound → Target (molecular interactions)
- **PRODUCES**: Mechanism → PharmEffect (how mechanisms lead to effects)
- **TREATS**: PharmEffect/Compound → Indication (therapeutic relationships)
- **SUGGESTS**: TraditionalUse/Evidence → Indication (evidence supporting use)

## OUTPUT FORMAT
Return ONLY a JSON object with this exact structure:
```json
{{
  "entities": [
    {{
      "id": "ent_001",
      "type": "Taxon",
      "name": "Sceletium tortuosum",
      "attributes": {{"family": "Aizoaceae", "common_name": "Kanna"}}
    }},
    {{
      "id": "ent_002",
      "type": "Compound",
      "name": "mesembrine",
      "attributes": {{"compound_class": "alkaloid"}}
    }}
  ],
  "relationships": [
    {{
      "id": "rel_001",
      "type": "CONTAINS",
      "source_entity_id": "ent_001",
      "target_entity_id": "ent_002",
      "attributes": {{"notes": "major alkaloid"}}
    }}
  ]
}}
```

## EXTRACTION RULES
1. Extract ALL entities mentioned, even if no relationships exist
2. Use lowercase for entity names except proper nouns and scientific names
3. For Taxon, always use scientific binomial when available
4. For Compound, include CAS numbers or molecular formulas in attributes if mentioned
5. Create relationships ONLY when the text explicitly states the connection
6. If no entities found, return: {{"entities": [], "relationships": []}}
7. Output ONLY the JSON object. Start with {{ and end with }}. No extra text.

## TEXT TO EXTRACT FROM
{text}
"""
