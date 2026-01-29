# workflow/quality_assessment.py
"""
Quality assessment utilities for the workflow engine.
Provides comprehensive quality scoring for academic content.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
import re


class QualityDimension(Enum):
    COVERAGE = "coverage"
    COHERENCE = "coherence"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    STRUCTURAL = "structural"


@dataclass
class QualityMetrics:
    """Container for quality metrics"""
    coverage_score: float = 0.0
    coherence_score: float = 0.0
    relevance_score: float = 0.0
    completeness_score: float = 0.0
    structural_score: float = 0.0
    overall_score: float = 0.0
    issues: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


class QualityAssessmentEngine:
    """
    Engine for assessing academic content quality
    """

    def __init__(self):
        self.dimension_weights = {
            QualityDimension.COVERAGE: 0.3,
            QualityDimension.COHERENCE: 0.3,
            QualityDimension.RELEVANCE: 0.2,
            QualityDimension.COMPLETENESS: 0.1,
            QualityDimension.STRUCTURAL: 0.1
        }

    def assess_outline_quality(
        self,
        outline: Dict[str, Any],
        requirements: Dict[str, Any],
        coverage_report: Optional[Dict] = None
    ) -> QualityMetrics:
        """
        Assess the quality of a thesis outline
        """
        metrics = QualityMetrics()

        # Assess each dimension
        metrics.coverage_score = self._assess_coverage(outline, requirements, coverage_report)
        metrics.coherence_score = self._assess_coherence(outline)
        metrics.relevance_score = self._assess_relevance(outline, requirements)
        metrics.completeness_score = self._assess_completeness(outline)
        metrics.structural_score = self._assess_structure(outline)

        # Calculate overall score
        metrics.overall_score = self._calculate_overall_score(metrics)

        # Generate issues list
        metrics.issues = self._generate_quality_issues(metrics, outline)

        return metrics

    def _assess_coverage(
        self,
        outline: Dict[str, Any],
        requirements: Dict[str, Any],
        coverage_report: Optional[Dict] = None
    ) -> float:
        """
        Assess coverage quality
        """
        if coverage_report:
            # Use existing coverage report
            gaps = coverage_report.get("gaps", [])
            total_subsections = sum(
                len(s.get("subsections", []))
                for c in outline.get("chapters", [])
                for s in c.get("sections", [])
            )

            if total_subsections == 0:
                return 0.0

            gap_ratio = len(gaps) / total_subsections
            return max(0.0, 1.0 - gap_ratio)

        # Fallback: check source requirements
        min_sources = requirements.get("quality_gates", {}).get("min_sources_per_subsection", 3)
        source_check = 0.0  # Would need implementation to check actual sources

        return source_check

    def _assess_coherence(self, outline: Dict[str, Any]) -> float:
        """
        Assess logical coherence and flow
        """
        coherence_score = 1.0
        issues = []

        chapters = outline.get("chapters", [])

        # Check chapter progression
        for i in range(len(chapters) - 1):
            current = chapters[i]
            next_chapter = chapters[i + 1]

            # Check logical flow between chapters
            if not self._check_chapter_flow(current, next_chapter):
                coherence_score -= 0.1
                issues.append({
                    "dimension": "coherence",
                    "severity": "medium",
                    "description": f"Poor flow between chapters {i+1} and {i+2}",
                    "location": f"chapter_{i+1}_to_{i+2}"
                })

        # Check internal chapter structure
        for i, chapter in enumerate(chapters):
            chapter_issues = self._check_chapter_coherence(chapter)
            coherence_score -= chapter_issues * 0.05
            issues.extend(chapter_issues)

        return max(0.0, coherence_score)

    def _assess_relevance(self, outline: Dict[str, Any], requirements: Dict[str, Any]) -> float:
        """
        Assess topic relevance and alignment
        """
        relevance_score = 1.0

        # Check research question alignment
        research_area = requirements.get("research_area", "")
        if research_area:
            # Would need NLP analysis to check alignment
            # Placeholder implementation
            pass

        # Check scope compliance
        scope = requirements.get("scope", {})
        in_scope = set(scope.get("in_scope", []))
        out_of_scope = set(scope.get("out_of_scope", []))

        # Extract topics from outline
        outline_topics = self._extract_outline_topics(outline)

        # Check for out-of-scope topics
        out_of_scope_found = outline_topics.intersection(out_of_scope)
        if out_of_scope_found:
            relevance_score -= len(out_of_scope_found) * 0.2

        # Check for required topics
        missing_required = in_scope - outline_topics
        if missing_required:
            relevance_score -= len(missing_required) * 0.1

        return max(0.0, relevance_score)

    def _assess_completeness(self, outline: Dict[str, Any]) -> float:
        """
        Assess content completeness
        """
        completeness_score = 1.0
        chapters = outline.get("chapters", [])

        # Check minimum chapter count
        if len(chapters) < 3:  # Typical minimum: intro, methods, conclusion
            completeness_score -= 0.3

        # Check section completeness
        for chapter in chapters:
            sections = chapter.get("sections", [])
            if len(sections) < 1:
                completeness_score -= 0.1

            # Check subsection completeness
            for section in sections:
                subsections = section.get("subsections", [])
                if len(subsections) < 2:  # Minimum 2 subsections per section
                    completeness_score -= 0.05

        return max(0.0, completeness_score)

    def _assess_structure(self, outline: Dict[str, Any]) -> float:
        """
        Assess structural quality
        """
        structure_score = 1.0
        chapters = outline.get("chapters", [])

        # Check chapter ordering
        expected_order = ["introduction", "literature review", "methodology",
                         "results", "discussion", "conclusion"]

        chapter_names = [c.get("name", "").lower() for c in chapters]

        # Check for standard structure
        standard_found = 0
        for expected in expected_order:
            if any(expected in name for name in chapter_names):
                standard_found += 1

        structure_score = standard_found / len(expected_order)

        # Check balance (no overly large/small chapters)
        section_counts = [len(c.get("sections", [])) for c in chapters]
        if section_counts:
            avg_sections = sum(section_counts) / len(section_counts)
            max_sections = max(section_counts)
            if max_sections > avg_sections * 2:  # More than 2x average
                structure_score -= 0.1

        return max(0.0, structure_score)

    def _calculate_overall_score(self, metrics: QualityMetrics) -> float:
        """
        Calculate weighted overall quality score
        """
        overall = 0.0
        for dimension, score in metrics.__dict__.items():
            if dimension.endswith("_score"):
                weight = self.dimension_weights.get(
                    QualityDimension(dimension.replace("_score", "")), 0.0
                )
                overall += score * weight

        return overall

    def _generate_quality_issues(
        self,
        metrics: QualityMetrics,
        outline: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate list of quality issues
        """
        issues = []

        # Coverage issues
        if metrics.coverage_score < 0.7:
            issues.append({
                "dimension": "coverage",
                "severity": "high" if metrics.coverage_score < 0.5 else "medium",
                "description": "Insufficient source coverage",
                "score": metrics.coverage_score,
                "recommendation": "Add more sources to uncovered sections"
            })

        # Coherence issues
        if metrics.coherence_score < 0.8:
            issues.append({
                "dimension": "coherence",
                "severity": "medium",
                "description": "Logical flow needs improvement",
                "score": metrics.coherence_score,
                "recommendation": "Improve transitions between chapters"
            })

        # Relevance issues
        if metrics.relevance_score < 0.8:
            issues.append({
                "dimension": "relevance",
                "severity": "high",
                "description": "Content deviates from research scope",
                "score": metrics.relevance_score,
                "recommendation": "Realign content with research objectives"
            })

        # Completeness issues
        if metrics.completeness_score < 0.8:
            issues.append({
                "dimension": "completeness",
                "severity": "medium",
                "description": "Outline appears incomplete",
                "score": metrics.completeness_score,
                "recommendation": "Add missing chapters or sections"
            })

        # Structural issues
        if metrics.structural_score < 0.7:
            issues.append({
                "dimension": "structural",
                "severity": "low",
                "description": "Structure needs improvement",
                "score": metrics.structural_score,
                "recommendation": "Reorganize chapters for better flow"
            })

        return issues

    def _check_chapter_flow(self, current: Dict, next_chapter: Dict) -> bool:
        """
        Check logical flow between chapters
        """
        current_name = current.get("name", "").lower()
        next_name = next_chapter.get("name", "").lower()

        # Basic flow checks
        flow_rules = {
            "introduction": ["literature review", "methodology"],
            "literature review": ["methodology"],
            "methodology": ["results"],
            "results": ["discussion", "conclusion"],
            "discussion": ["conclusion"]
        }

        if current_name in flow_rules:
            return any(target in next_name for target in flow_rules[current_name])

        return True  # Default to valid flow

    def _check_chapter_coherence(self, chapter: Dict) -> int:
        """
        Check internal chapter coherence
        """
        issues = 0
        sections = chapter.get("sections", [])

        # Check section progression
        for i in range(len(sections) - 1):
            current = sections[i]
            next_section = sections[i + 1]

            # Simple coherence check - would need more sophisticated analysis
            if len(current.get("subsections", [])) == 0:
                issues += 1

        return issues

    def _extract_outline_topics(self, outline: Dict[str, Any]) -> set:
        """
        Extract topics from outline
        """
        topics = set()

        def extract_from_section(section):
            name = section.get("name", "").lower()
            topics.update(name.split())
            for subsection in section.get("subsections", []):
                extract_from_section(subsection)

        for chapter in outline.get("chapters", []):
            for section in chapter.get("sections", []):
                extract_from_section(section)

        return topics


def create_quality_assessment_engine() -> QualityAssessmentEngine:
    """Factory function to create quality assessment engine"""
    return QualityAssessmentEngine()