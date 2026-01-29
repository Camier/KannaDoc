# workflow/quality_assessment_utils.py
"""
Utility functions for quality assessment in workflow nodes.
"""
from typing import Dict, Any, List
import json


def calculate_coverage_score(coverage_report: Dict) -> float:
    """
    Calculate coverage score from coverage report
    """
    gaps = coverage_report.get("gaps", [])
    total_subsections = coverage_report.get("total_subsections", 1)

    # Calculate coverage ratio (1 - gap_ratio)
    coverage_ratio = 1.0 - (len(gaps) / total_subsections)
    return max(0.0, min(1.0, coverage_ratio))


def calculate_completeness_score(outline: Dict) -> float:
    """
    Calculate completeness score for outline structure
    """
    chapters = outline.get("chapters", [])
    if not chapters:
        return 0.0

    # Check minimum structure
    min_chapters = 3  # Introduction, main content, conclusion
    chapter_completeness = min(len(chapters) / min_chapters, 1.0)

    # Check section completeness
    total_sections = sum(len(c.get("sections", [])) for c in chapters)
    min_sections_per_chapter = 2
    expected_sections = len(chapters) * min_sections_per_chapter
    section_completeness = min(total_sections / expected_sections, 1.0) if expected_sections > 0 else 0.0

    # Check subsection completeness
    total_subsections = sum(
        len(s.get("subsections", []))
        for c in chapters
        for s in c.get("sections", [])
    )
    expected_subsections = total_sections * 2  # Average 2 subsections per section
    subsection_completeness = min(total_subsections / expected_subsections, 1.0) if expected_subsections > 0 else 0.0

    # Weighted average
    return (
        chapter_completeness * 0.3 +
        section_completeness * 0.3 +
        subsection_completeness * 0.4
    )


def calculate_refinement_needed(
    coverage_score: float,
    completeness_score: float,
    gap_count: int,
    total_subsections: int
) -> Dict[str, Any]:
    """
    Determine if refinement is needed based on quality metrics
    """
    # Calculate gap ratio
    gap_ratio = gap_count / total_subsections if total_subsections > 0 else 1.0

    # Determine refinement decision
    if coverage_score >= 0.85 and completeness_score >= 0.8:
        return {
            "decision": "skip",
            "confidence": 0.9,
            "reason": "Excellent quality metrics",
            "gap_ratio": gap_ratio,
            "coverage_score": coverage_score,
            "completeness_score": completeness_score
        }
    elif coverage_score >= 0.7 and completeness_score >= 0.7:
        return {
            "decision": "minor_refine",
            "confidence": 0.6,
            "reason": "Minor improvements needed",
            "gap_ratio": gap_ratio,
            "coverage_score": coverage_score,
            "completeness_score": completeness_score
        }
    elif coverage_score >= 0.5 and completeness_score >= 0.5:
        return {
            "decision": "moderate_refine",
            "confidence": 0.7,
            "reason": "Moderate quality issues detected",
            "gap_ratio": gap_ratio,
            "coverage_score": coverage_score,
            "completeness_score": completeness_score
        }
    else:
        return {
            "decision": "critical_refine",
            "confidence": 0.9,
            "reason": "Critical quality issues",
            "gap_ratio": gap_ratio,
            "coverage_score": coverage_score,
            "completeness_score": completeness_score
        }


def extract_quality_metrics(context: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract quality metrics from workflow context
    """
    metrics = {}

    # Extract coverage metrics
    coverage = context.get("coverage", {})
    metrics["coverage_score"] = calculate_coverage_score(coverage)
    metrics["gap_count"] = len(coverage.get("gaps", []))
    metrics["total_subsections"] = coverage.get("total_subsections", 1)

    # Extract outline metrics
    outline = context.get("micro_outline", {})
    metrics["completeness_score"] = calculate_completeness_score(outline)

    # Extract requirements metrics
    requirements = context.get("requirements", {})
    min_sources = requirements.get("quality_gates", {}).get("min_sources_per_subsection", 3)
    metrics["min_sources"] = min_sources

    return metrics


def create_quality_context_variables(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create variables for quality assessment in workflow context
    """
    metrics = extract_quality_metrics(context)

    # Calculate refinement decision
    refinement_decision = calculate_refinement_needed(
        metrics["coverage_score"],
        metrics["completeness_score"],
        metrics["gap_count"],
        metrics["total_subsections"]
    )

    # Update global variables with quality assessment
    quality_vars = {
        "quality_metrics": metrics,
        "quality_assessment": refinement_decision,
        "coverage_score": metrics["coverage_score"],
        "completeness_score": metrics["completeness_score"],
        "gaps_found": metrics["gap_count"] > 0,
        "refinement_decision": refinement_decision["decision"],
        "refinement_confidence": refinement_decision["confidence"]
    }

    return quality_vars