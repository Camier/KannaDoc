"""
Quality assessment engine for workflow outputs.

Provides multi-dimensional scoring for quality gates, enabling intelligent
routing based on content quality metrics.
"""

from typing import Dict, Optional


class QualityAssessmentEngine:
    """
    Assesses workflow output quality for conditional routing.
    Provides multi-dimensional scoring for quality gates.
    """

    def __init__(self, global_variables: dict):
        self.global_variables = global_variables
        self.assessments = []

    def assess_content_quality(
        self,
        content: str,
        node_id: str,
        criteria: dict = None,
    ) -> dict:
        """
        Assess content quality across multiple dimensions.

        Args:
            content: The content to assess
            node_id: Node identifier for tracking
            criteria: Optional custom criteria weights

        Returns:
            Dict with quality scores and pass/fail decision
        """
        criteria = criteria or {
            "completeness": 0.3,
            "coherence": 0.3,
            "relevance": 0.2,
            "length": 0.2,
        }

        scores = {}

        # Completeness: Has substantial content
        word_count = len(content.split())
        scores["completeness"] = min(1.0, word_count / 100)  # 100 words = complete

        # Coherence: Has structured elements (paragraphs, lists)
        has_paragraphs = "\n\n" in content or len(content.split("\n")) > 3
        has_structure = any(marker in content for marker in ["#", "-", "*", "1.", "•"])
        scores["coherence"] = (
            0.5 + (0.3 if has_paragraphs else 0) + (0.2 if has_structure else 0)
        )

        # Relevance: Contains keywords from global context
        topic = self.global_variables.get("thesis_topic", "")
        if topic:
            topic_words = set(topic.lower().split())
            content_words = set(content.lower().split())
            relevance = len(topic_words & content_words) / max(len(topic_words), 1)
            scores["relevance"] = min(1.0, relevance * 2)
        else:
            scores["relevance"] = 0.8  # Default if no topic

        # Length: Appropriate length (not too short, not too long)
        target_length = self.global_variables.get("target_length_pages", 10) * 300
        length_ratio = word_count / max(target_length, 100)
        scores["length"] = 1.0 - abs(1.0 - min(length_ratio, 2.0)) / 2.0

        # Calculate weighted score
        total_score = sum(scores.get(k, 0) * v for k, v in criteria.items())

        # Determine pass/fail (threshold = 0.6)
        passed = total_score >= 0.6

        assessment = {
            "node_id": node_id,
            "scores": scores,
            "total_score": total_score,
            "passed": passed,
            "weighted_by": criteria,
        }

        self.assessments.append(assessment)

        return assessment

    def get_assessment_summary(self) -> dict:
        """
        Get summary of all assessments.

        Returns:
            Dict with statistics about all quality assessments
        """
        if not self.assessments:
            return {"count": 0, "average_score": 0, "pass_rate": 0}

        total_score = sum(a["total_score"] for a in self.assessments)
        pass_count = sum(1 for a in self.assessments if a["passed"])

        return {
            "count": len(self.assessments),
            "average_score": total_score / len(self.assessments),
            "pass_rate": pass_count / len(self.assessments),
            "assessments": self.assessments,
        }
