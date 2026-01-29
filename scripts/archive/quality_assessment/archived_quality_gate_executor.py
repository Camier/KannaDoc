# workflow/executors/quality_gate_executor.py
"""
Enhanced Quality Gate Executor for intelligent workflow routing.
Implements multi-dimensional quality assessment and conditional routing.
"""
from typing import Dict, Any, List, Optional
import json
from dataclasses import dataclass
from enum import Enum

from app.workflow.graph import TreeNode
from app.workflow.executors.base_executor import BaseExecutor, NodeResult
from app.workflow.code_scanner import CodeScanner


class Decision(Enum):
    """Routing decisions for quality gates"""
    SKIP = "skip"
    MINOR_REFINE = "minor_refine"
    MODERATE_REFINE = "moderate_refine"
    CRITICAL_REFINE = "critical_refine"
    AUTO_APPROVED = "auto_approved"
    AWAITING_APPROVAL = "awaiting_approval"


@dataclass
class QualityAssessment:
    """Quality assessment result"""
    decision: Decision
    score: float
    confidence: float
    reasons: List[str]
    metrics: Dict[str, float]
    path: str


class QualityGateExecutor(BaseExecutor):
    """Executor for quality gate nodes with intelligent routing"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scanner = CodeScanner()

        # Default quality thresholds
        self.thresholds = {
            "skip": 0.85,
            "minor": 0.70,
            "moderate": 0.50,
            "critical": 0.0
        }

        # Metric weights
        self.weights = {
            "coverage": 0.4,
            "coherence": 0.3,
            "relevance": 0.3
        }

    async def execute(self, node: TreeNode) -> NodeResult:
        """
        Execute quality gate with intelligent routing
        """
        # Get quality thresholds from node config
        thresholds = node.data.get("quality_thresholds", {})
        if thresholds:
            self.thresholds.update(thresholds)

        weights = node.data.get("metrics_weights", {})
        if weights:
            self.weights.update(weights)

        # Perform quality assessment
        assessment = self._assess_quality()

        # Store assessment in context
        self._add_to_context(node.node_id, {
            "assessment": assessment.__dict__,
            "quality_score": assessment.score,
            "decision": assessment.value
        })

        # Determine routing
        matched_conditions = self._determine_routing_conditions(assessment)
        condition_children = self._get_matching_children(node, matched_conditions)

        return NodeResult(
            success=True,
            output={
                "assessment": assessment,
                "matched_children": condition_children,
                "skip_children": [
                    child for child in node.children
                    if child.condition not in matched_conditions
                ]
            }
        )

    def _assess_quality(self) -> QualityAssessment:
        """
        Perform multi-dimensional quality assessment
        """
        # Extract metrics from context
        coverage = self._extract_coverage_metrics()
        coherence = self._extract_coherence_metrics()
        relevance = self._extract_relevance_metrics()

        # Calculate weighted quality score
        quality_score = (
            coverage["score"] * self.weights["coverage"] +
            coherence["score"] * self.weights["coherence"] +
            relevance["score"] * self.weights["relevance"]
        )

        # Determine decision based on thresholds
        decision, confidence, reasons = self._make_routing_decision(
            quality_score, coverage, coherence, relevance
        )

        return QualityAssessment(
            decision=decision,
            score=quality_score,
            confidence=confidence,
            reasons=reasons,
            metrics={
                "coverage": coverage["score"],
                "coherence": coherence["score"],
                "relevance": relevance["score"]
            },
            path=self._determine_workflow_path(decision)
        )

    def _extract_coverage_metrics(self) -> Dict[str, Any]:
        """Extract coverage-based quality metrics"""
        coverage = self.global_variables.get("coverage", {})
        gaps = coverage.get("gaps", [])

        # Calculate gap-based metrics
        micro_outline = self.global_variables.get("micro_outline", {})
        total_subsections = 0
        subsections_with_sources = 0

        for chapter in micro_outline.get("chapters", []):
            for section in chapter.get("sections", []):
                for subsection in section.get("subsections", []):
                    total_subsections += 1
                    if subsection.get("candidate_sources", []):
                        subsections_with_sources += 1

        coverage_ratio = subsections_with_sources / total_subsections if total_subsections > 0 else 0

        # Check minimum sources requirement
        requirements = self.global_variables.get("requirements", {})
        min_sources = requirements.get("quality_gates", {}).get("min_sources_per_subsection", 3)
        sources_compliance = 0

        for gap in gaps:
            # This would need to be implemented based on actual gap analysis
            pass

        return {
            "score": coverage_ratio,
            "total_subsections": total_subsections,
            "covered_subsections": subsections_with_sources,
            "gap_count": len(gaps),
            "compliance_ratio": sources_compliance
        }

    def _extract_coherence_metrics(self) -> Dict[str, Any]:
        """Extract coherence-based quality metrics"""
        # Placeholder for coherence metrics
        # These would come from coherence analysis or historical data
        return {
            "score": 0.75,  # Placeholder
            "structural_issues": 0,
            "logical_gaps": 0,
            "completeness": 0.8
        }

    def _extract_relevance_metrics(self) -> Dict[str, Any]:
        """Extract relevance-based quality metrics"""
        # Placeholder for relevance metrics
        # These would come from topic relevance analysis
        return {
            "score": 0.85,  # Placeholder
            "topic_alignment": 0.9,
            "completeness": 0.8,
            "depth_score": 0.85
        }

    def _make_routing_decision(
        self,
        quality_score: float,
        coverage: Dict,
        coherence: Dict,
        relevance: Dict
    ) -> tuple[Decision, float, List[str]]:
        """
        Make routing decision based on quality metrics
        """
        reasons = []
        confidence = 0.0

        # Coverage-based decision
        gap_ratio = coverage["gap_count"] / coverage["total_subsections"] if coverage["total_subsections"] > 0 else 1.0

        if gap_ratio > 0.3:  # 30% gaps
            return Decision.CRITICAL_REFINE, 0.95, ["Critical gap ratio"]
        elif gap_ratio > 0.15:  # 15% gaps
            return Decision.MODERATE_REFINE, 0.7, ["Moderate coverage gaps"]
        elif gap_ratio > 0.05:  # 5% gaps
            return Decision.MINOR_REFINE, 0.4, ["Minor coverage issues"]

        # Overall quality-based decision
        if quality_score > self.thresholds["skip"]:
            return Decision.SKIP, 0.9, ["Excellent overall quality"]
        elif quality_score > self.thresholds["moderate"]:
            return Decision.MINOR_REFINE, 0.6, ["Good but needs minor refinement"]
        elif quality_score > self.thresholds["critical"]:
            return Decision.MODERATE_REFINE, 0.7, ["Moderate quality needs improvement"]
        else:
            return Decision.CRITICAL_REFINE, 0.85, ["Poor quality requires critical attention"]

    def _determine_workflow_path(self, decision: Decision) -> str:
        """Determine workflow path based on decision"""
        path_map = {
            Decision.SKIP: "direct_coherence",
            Decision.MINOR_REFINE: "minor_refinement",
            Decision.MODERATE_REFINE: "moderate_refinement",
            Decision.CRITICAL_REFINE: "critical_refinement",
            Decision.AUTO_APPROVED: "auto_approved",
            Decision.AWAITING_APPROVAL: "awaiting_approval"
        }
        return path_map.get(decision, "default")

    def _determine_routing_conditions(self, assessment: QualityAssessment) -> List[str]:
        """
        Map assessment decision to condition indices
        """
        decision_map = {
            Decision.CRITICAL_REFINE: "0",
            Decision.MODERATE_REFINE: "1",
            Decision.MINOR_REFINE: "2",
            Decision.SKIP: "3"
        }
        return [decision_map.get(assessment.decision, "0")]

    def _get_matching_children(self, node: TreeNode, condition_indices: List[str]) -> List[TreeNode]:
        """Get children nodes that match the condition indices"""
        matching_children = []
        for child in node.children:
            if str(child.condition) in condition_indices:
                matching_children.append(child)
        return matching_children

    def _safe_eval(self, expr: str, node_name: str, node_id: str) -> bool:
        """
        Safely evaluate condition expression
        """
        # Scan expression code
        scan_result = self.scanner.scan_code(expr)
        if not scan_result["safe"]:
            raise ValueError(
                f"{node_id}:节点{node_name}: 不安全的表达式: {expr}, "
                f"问题: {scan_result['issues']}"
            )

        try:
            # Coerce string values to appropriate types
            def _coerce_value(value):
                if isinstance(value, str):
                    if value == "":
                        return ""
                    try:
                        # Try to evaluate as Python literal
                        return eval(value)
                    except Exception:
                        return value
                return value

            # Prepare variables with coercion
            eval_vars = {
                k: _coerce_value(v) for k, v in self.global_variables.items()
            }

            # Use simpleeval for safe evaluation
            from simpleeval import simple_eval, InvalidExpression
            result = simple_eval(expr, names=eval_vars)
            return bool(result)

        except InvalidExpression as e:
            raise ValueError(
                f"节点{node_name}: 表达式语法错误: {expr}, 错误: {str(e)}"
            )
        except Exception as e:
            raise ValueError(
                f"节点{node_name}: 表达式执行错误: {expr}, 错误: {str(e)}"
            )