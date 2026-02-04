\
"""
LAYRA V3.1 validators.

This module is intentionally "on-demand": it provides utilities to validate
extraction outputs against:
1) relationship type constraints (source/target types, required attributes)
2) minimum subgraph templates (EU/CP/MO/EF/TX/AE/DI)
3) claim completeness tiers (T0–T3), with optional thesis-grade requirements

It does NOT run automatically during extraction unless explicitly called.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Set, Tuple

import yaml

from .schemas import (
    CONFIDENCE_VERIFIED_THRESHOLD,
    ExtractionResult,
    Relationship,
)

Severity = Literal["error", "warning", "info"]
Tier = Literal["T0", "T1", "T2", "T3"]


# -----------------------------------------------------------------------------
# Report structures
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    code: str
    message: str
    entity_id: Optional[str] = None
    relationship_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@dataclass
class ValidationReport:
    issues: List[ValidationIssue]

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    def add(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)

    def extend(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues.extend(list(issues))

    def by_severity(self, severity: Severity) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == severity]


# -----------------------------------------------------------------------------
# Constraints loading
# -----------------------------------------------------------------------------


def load_constraints(path: str | Path) -> Dict[str, Any]:
    """Load constraints.yaml."""
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "relationships" not in data:
        raise ValueError(f"Invalid constraints file: {p}")
    return data


# -----------------------------------------------------------------------------
# Index helpers
# -----------------------------------------------------------------------------


def index_entities(extraction: ExtractionResult) -> Dict[str, Any]:
    """Map entity_id -> entity (Pydantic model)."""
    return {e.id: e for e in extraction.entities}


def index_relationships(extraction: ExtractionResult) -> Dict[str, Relationship]:
    """Map relationship_id -> relationship."""
    return {r.id: r for r in extraction.relationships}


def relationships_by_type(extraction: ExtractionResult) -> Dict[str, List[Relationship]]:
    out: Dict[str, List[Relationship]] = {}
    for r in extraction.relationships:
        out.setdefault(r.type, []).append(r)
    return out


# -----------------------------------------------------------------------------
# Constraint validation
# -----------------------------------------------------------------------------


def validate_constraints(
    extraction: ExtractionResult,
    constraints: Dict[str, Any],
) -> ValidationReport:
    """Validate relationship constraints (types + required attributes)."""
    report = ValidationReport(issues=[])

    rel_specs: Dict[str, Any] = constraints.get("relationships", {}) or {}
    entities = index_entities(extraction)

    for rel in extraction.relationships:
        spec = rel_specs.get(rel.type)
        if spec is None:
            report.add(
                ValidationIssue(
                    severity="error",
                    code="REL_UNKNOWN_TYPE",
                    message=f"Unknown relationship type '{rel.type}' not present in constraints.",
                    relationship_id=rel.id,
                    data={"type": rel.type},
                )
            )
            continue

        src = entities.get(rel.source_entity_id)
        tgt = entities.get(rel.target_entity_id)

        if src is None:
            report.add(
                ValidationIssue(
                    severity="error",
                    code="REL_MISSING_SOURCE_ENTITY",
                    message=f"Relationship source entity not found: {rel.source_entity_id}",
                    relationship_id=rel.id,
                    data={"source_entity_id": rel.source_entity_id},
                )
            )
            continue
        if tgt is None:
            report.add(
                ValidationIssue(
                    severity="error",
                    code="REL_MISSING_TARGET_ENTITY",
                    message=f"Relationship target entity not found: {rel.target_entity_id}",
                    relationship_id=rel.id,
                    data={"target_entity_id": rel.target_entity_id},
                )
            )
            continue

        allowed_src = set(spec.get("source_types", []) or [])
        allowed_tgt = set(spec.get("target_types", []) or [])

        if allowed_src and src.type not in allowed_src:
            report.add(
                ValidationIssue(
                    severity="error",
                    code="REL_SOURCE_TYPE_MISMATCH",
                    message=f"{rel.type} source type mismatch: got {src.type}, expected one of {sorted(allowed_src)}",
                    relationship_id=rel.id,
                    entity_id=src.id,
                    data={"source_type": src.type, "allowed_source_types": sorted(allowed_src)},
                )
            )

        if allowed_tgt and tgt.type not in allowed_tgt:
            report.add(
                ValidationIssue(
                    severity="error",
                    code="REL_TARGET_TYPE_MISMATCH",
                    message=f"{rel.type} target type mismatch: got {tgt.type}, expected one of {sorted(allowed_tgt)}",
                    relationship_id=rel.id,
                    entity_id=tgt.id,
                    data={"target_type": tgt.type, "allowed_target_types": sorted(allowed_tgt)},
                )
            )

        # Required attributes
        required_attrs = spec.get("required_attributes", []) or []
        for key in required_attrs:
            if key not in (rel.attributes or {}):
                report.add(
                    ValidationIssue(
                        severity="error",
                        code="REL_MISSING_REQUIRED_ATTRIBUTE",
                        message=f"{rel.type} missing required attribute '{key}'",
                        relationship_id=rel.id,
                        data={"missing_attribute": key},
                    )
                )

        # INVOLVES role validation (if configured)
        if rel.type == "INVOLVES":
            role = (rel.attributes or {}).get("role")
            role_map = spec.get("role_by_target_type", {}) or {}
            expected_role = role_map.get(tgt.type)
            if expected_role is not None and role != expected_role:
                report.add(
                    ValidationIssue(
                        severity="error",
                        code="INVOLVES_ROLE_MISMATCH",
                        message=f"INVOLVES role mismatch for target type {tgt.type}: got '{role}', expected '{expected_role}'",
                        relationship_id=rel.id,
                        data={"role": role, "expected_role": expected_role, "target_type": tgt.type},
                    )
                )

        # INTERACTS_WITH sanity checks
        if rel.type == "INTERACTS_WITH":
            if rel.source_entity_id == rel.target_entity_id:
                report.add(
                    ValidationIssue(
                        severity="error",
                        code="INTERACTS_WITH_SELF_LOOP",
                        message="INTERACTS_WITH cannot connect an entity to itself.",
                        relationship_id=rel.id,
                    )
                )

    return report


# -----------------------------------------------------------------------------
# Claim tiers (T0–T3)
# -----------------------------------------------------------------------------


def _has_min_provenance(rel: Relationship) -> bool:
    """T1 condition: claim edge has provenance (confidence + evidence + source chunks)."""
    return (
        rel.confidence is not None
        and isinstance(rel.evidence, str)
        and rel.evidence.strip() != ""
        and bool(rel.source_chunk_ids)
    )


def _valid_supporting_studies(rel: Relationship, entities: Dict[str, Any]) -> bool:
    """T2 condition: at least one supporting study exists and is typed Study."""
    if not rel.supporting_study_ids:
        return False
    for sid in rel.supporting_study_ids:
        e = entities.get(sid)
        if e is None or e.type != "Study":
            return False
    return True


def relationship_tier(rel: Relationship, extraction: ExtractionResult) -> Tier:
    """Classify claim completeness tier for a relationship.

    Tier definitions (per earlier spec):
    - T0: edge exists but missing provenance
    - T1: provenance present (source_chunk_ids + evidence + confidence)
    - T2: T1 + linked Study via supporting_study_ids
    - T3: T2 + Study REPORTS + Dosage/Measurement detail (type-dependent)

    Note: T0 is meaningful for "claim-like" edges that you care about; for
    non-claim edges it simply means "not fully evidenced".
    """
    entities = index_entities(extraction)
    rels_by_type = relationships_by_type(extraction)

    if not _has_min_provenance(rel):
        return "T0"

    tier: Tier = "T1"

    if _valid_supporting_studies(rel, entities):
        tier = "T2"
    else:
        return tier

    # T3 conditions are relation-type dependent
    supporting_studies = rel.supporting_study_ids

    # Helper: does any supporting study REPORTS the target?
    reports = rels_by_type.get("REPORTS", [])
    tested_at = rels_by_type.get("TESTED_AT", [])

    def study_reports_target(study_id: str, target_id: str) -> bool:
        return any(r.source_entity_id == study_id and r.target_entity_id == target_id for r in reports)

    def study_has_dosage(study_id: str) -> bool:
        return any(r.source_entity_id == study_id for r in tested_at)

    def edge_has_measurement() -> bool:
        m = (rel.attributes or {}).get("measurement")
        if not isinstance(m, dict):
            return False
        return all(k in m for k in ("value", "unit", "measurement_type"))

    if rel.type in ("TREATS", "CAUSES"):
        has_reports = any(study_reports_target(sid, rel.target_entity_id) for sid in supporting_studies)
        has_detail = any(study_has_dosage(sid) for sid in supporting_studies) or edge_has_measurement()
        if has_reports and has_detail:
            return "T3"
        return tier

    if rel.type in ("ACTS_ON", "CONTAINS"):
        # For mechanistic/composition claims, "detail" is typically a measurement.
        if edge_has_measurement():
            return "T3"
        return tier

    # For other relations, we don't enforce a specific T3 rule.
    return tier


# -----------------------------------------------------------------------------
# Minimum subgraph templates (EU, CP, MO, EF, TX, AE, DI)
# -----------------------------------------------------------------------------


def template_counts(extraction: ExtractionResult) -> Dict[str, int]:
    """Count instances matching each minimum template."""
    entities = index_entities(extraction)
    rels_by_type = relationships_by_type(extraction)

    # EU-Min: Culture --HAS_USE--> UseRecord --INVOLVES(role=taxon)--> Taxon
    #                         \--INVOLVES(role=traditional_use)--> TraditionalUse
    eu_count = 0
    for r in rels_by_type.get("HAS_USE", []):
        cult = entities.get(r.source_entity_id)
        use = entities.get(r.target_entity_id)
        if not cult or not use or cult.type != "Culture" or use.type != "UseRecord":
            continue
        involves = [x for x in rels_by_type.get("INVOLVES", []) if x.source_entity_id == use.id]
        has_taxon = False
        has_trad_use = False
        for inv in involves:
            tgt = entities.get(inv.target_entity_id)
            role = (inv.attributes or {}).get("role")
            if tgt and tgt.type == "Taxon" and role == "taxon":
                has_taxon = True
            if tgt and tgt.type == "TraditionalUse" and role == "traditional_use":
                has_trad_use = True
        if has_taxon and has_trad_use:
            eu_count += 1

    # CP-Min: X --CONTAINS--> Compound
    cp_count = 0
    for r in rels_by_type.get("CONTAINS", []):
        src = entities.get(r.source_entity_id)
        tgt = entities.get(r.target_entity_id)
        if src and tgt and tgt.type == "Compound":
            if src.type in {"Taxon", "PlantPart", "RawMaterial", "Product"}:
                cp_count += 1

    # MO-Min: Compound --ACTS_ON--> Target
    mo_count = 0
    for r in rels_by_type.get("ACTS_ON", []):
        src = entities.get(r.source_entity_id)
        tgt = entities.get(r.target_entity_id)
        if src and tgt and src.type == "Compound" and tgt.type == "Target":
            mo_count += 1

    # EF-Min: (Compound|Effect) --PRODUCES--> Effect
    ef_count = 0
    for r in rels_by_type.get("PRODUCES", []):
        src = entities.get(r.source_entity_id)
        tgt = entities.get(r.target_entity_id)
        if src and tgt and tgt.type == "Effect" and src.type in {"Compound", "Effect"}:
            ef_count += 1

    # TX-Min: TREATS edge with supporting Study (tier >= T2)
    tx_count = 0
    for r in rels_by_type.get("TREATS", []):
        if relationship_tier(r, extraction) in ("T2", "T3"):
            tx_count += 1

    # AE-Min: CAUSES edge with supporting Study (tier >= T2)
    ae_count = 0
    for r in rels_by_type.get("CAUSES", []):
        if relationship_tier(r, extraction) in ("T2", "T3"):
            ae_count += 1

    # DI-Min: Compound INTERACTS_WITH Compound
    di_count = 0
    for r in rels_by_type.get("INTERACTS_WITH", []):
        src = entities.get(r.source_entity_id)
        tgt = entities.get(r.target_entity_id)
        if src and tgt and src.type == "Compound" and tgt.type == "Compound":
            di_count += 1

    return {
        "EU-Min": eu_count,
        "CP-Min": cp_count,
        "MO-Min": mo_count,
        "EF-Min": ef_count,
        "TX-Min": tx_count,
        "AE-Min": ae_count,
        "DI-Min": di_count,
    }


def validate_thesis_grade_claims(
    extraction: ExtractionResult,
    *,
    required_min_tier: Dict[str, Tier] | None = None,
    strict: bool = False,
) -> ValidationReport:
    """Validate claim completeness requirements.

    Default: require T2 for TREATS and CAUSES (thesis-grade assertions).
    - strict=False => missing requirements are warnings (recommended for dev)
    - strict=True  => missing requirements are errors (for gating CI / eval)
    """
    report = ValidationReport(issues=[])
    req = required_min_tier or {"TREATS": "T2", "CAUSES": "T2"}
    rels_by_type = relationships_by_type(extraction)

    for rel_type, min_tier in req.items():
        for rel in rels_by_type.get(rel_type, []):
            tier = relationship_tier(rel, extraction)
            if _tier_lt(tier, min_tier):
                sev: Severity = "error" if strict else "warning"
                report.add(
                    ValidationIssue(
                        severity=sev,
                        code="CLAIM_TIER_TOO_LOW",
                        message=f"{rel_type} relationship tier {tier} is below required minimum {min_tier}.",
                        relationship_id=rel.id,
                        data={"required_min_tier": min_tier, "tier": tier, "type": rel_type},
                    )
                )
    return report


def _tier_lt(a: Tier, b: Tier) -> bool:
    order = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}
    return order[a] < order[b]


# -----------------------------------------------------------------------------
# Convenience: full validation pipeline (on-demand)
# -----------------------------------------------------------------------------


def validate_extraction(
    extraction: ExtractionResult,
    *,
    constraints_path: str | Path,
    strict_thesis_grade: bool = False,
) -> Tuple[ValidationReport, Dict[str, int]]:
    """Run a standard validation suite.

    Returns:
      (report, template_counts)
    """
    constraints = load_constraints(constraints_path)

    report = validate_constraints(extraction, constraints)
    report.extend(validate_thesis_grade_claims(extraction, strict=strict_thesis_grade).issues)

    counts = template_counts(extraction)

    # Informational: which templates appear in this extraction
    for name, n in counts.items():
        if n == 0:
            report.add(
                ValidationIssue(
                    severity="info",
                    code="TEMPLATE_ABSENT",
                    message=f"Template {name} absent in this extraction (count=0).",
                    data={"template": name},
                )
            )
        else:
            report.add(
                ValidationIssue(
                    severity="info",
                    code="TEMPLATE_PRESENT",
                    message=f"Template {name} present (count={n}).",
                    data={"template": name, "count": n},
                )
            )

    return report, counts


__all__ = [
    "ValidationIssue",
    "ValidationReport",
    "load_constraints",
    "validate_constraints",
    "relationship_tier",
    "template_counts",
    "validate_thesis_grade_claims",
    "validate_extraction",
]

