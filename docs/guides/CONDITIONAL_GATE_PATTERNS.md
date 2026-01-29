# Conditional Gate and Branch Patterns in Workflow Engines

## Executive Summary

This document analyzes conditional routing patterns in workflow engines and provides design recommendations for the Layra workflow's "Refine Gate" (n12_gate). Current implementation passes both conditions to n13_coh, but needs intelligent quality-based routing.

## 1. Current State Analysis

### Layra's n12_gate Implementation
```json
{
  "id": "n12_gate",
  "type": "condition",
  "data": {
    "name": "Refine Gate",
    "conditions": {
      "0": "gaps_found == True",   // Route to refinement
      "1": "gaps_found == False"   // Skip refinement
    }
  }
}
```

### Current Problem
- Both condition outputs route to `n13_coh` (Coherence check)
- No intelligent skipping based on quality metrics
- Missing multi-dimensional quality assessment

## 2. Workflow Engine Conditional Patterns

### 2.1 Temporal Patterns
**Temporal** uses Activity Task timeouts and results for routing:

```python
# Temporal: Result-based routing
@workflow.defn
class ThesesWorkflow:
    @workflow.run
    async def run(self, thesis_topic: str) -> ThesisBlueprint:
        # Activity with timeout and result-based routing
        axes = await workflow.execute_activity(
            generate_seed_axes,
            thesis_topic,
            start_to_close_timeout=timedelta(minutes=5)
        )

        # Conditional routing based on activity result
        if axes.quality_score > 0.8:
            return workflow.execute_activity(
                fast_coherence_check,
                axes
            )
        else:
            return workflow.execute_activity(
                full_refinement,
                axes
            )
```

### 2.2 Prefect Patterns
**Prefect** uses parameter-based routing with if/else logic:

```python
# Prefect: Conditional task routing
from prefect import flow, task

@task
def assess_coverage(coverage_report: dict) -> str:
    gaps = coverage_report.get("gaps", [])
    if len(gaps) > 5:
        return "needs_refinement"
    return "sufficient"

@flow
def thesis_workflow():
    coverage = assess_coverage()

    if coverage == "needs_refinement":
        refined = refine_outline(micro_outline)
        return coherence_check(refined)
    else:
        return coherence_check(micro_outline)
```

### 2.3 Apache Airflow Patterns
**Airflow** uses BranchPythonOperator for complex routing:

```python
# Airflow: Branch-based routing
from airflow.operators.python import BranchPythonOperator

def decide_refinement(**context):
    coverage_report = context['task_instance'].xcom_pull(task_ids='coverage_scoring')
    gaps = coverage_report.get('gaps', [])

    # Multi-dimensional decision
    if len(gaps) > 10 or coverage_report.get('completeness_score', 0) < 0.6:
        return 'full_refinement_path'
    elif len(gaps) > 3:
        return 'light_refinement_path'
    else:
        return 'skip_refinement_path'

branch_task = BranchPythonOperator(
    task_id='refine_decision',
    python_callable=decide_refinement
)
```

## 3. Quality Gate Patterns

### 3.1 Multi-Dimensional Quality Gates
```python
# Pattern: Multi-dimensional quality assessment
def quality_gate_assessment(coverage_report: dict, outline_metrics: dict) -> dict:
    assessment = {
        "decision": "refine",  # default
        "reason": [],
        "confidence": 0.0,
        "path": "default"
    }

    # Coverage-based thresholds
    gaps = coverage_report.get("gaps", [])
    total_subsections = sum(len(s.get("subsections", [])) for c in outline_metrics.get("chapters", []) for s in c.get("sections", []))

    # Calculate gap ratio
    gap_ratio = len(gaps) / total_subsections if total_subsections > 0 else 1.0

    # Quality thresholds
    CRITICAL_THRESHOLD = 0.3   # 30% gaps
    MODERATE_THRESHOLD = 0.15  # 15% gaps
    MINOR_THRESHOLD = 0.05     # 5% gaps

    # Decision logic
    if gap_ratio > CRITICAL_THRESHOLD:
        assessment.update({
            "decision": "critical_refine",
            "reason": [f"High gap ratio: {gap_ratio:.2%}"],
            "confidence": 0.95,
            "path": "critical_refinement"
        })
    elif gap_ratio > MODERATE_THRESHOLD:
        assessment.update({
            "decision": "moderate_refine",
            "reason": [f"Moderate gaps: {len(gaps)} sections"],
            "confidence": 0.7,
            "path": "moderate_refinement"
        })
    elif gap_ratio > MINOR_THRESHOLD:
        assessment.update({
            "decision": "minor_refine",
            "reason": [f"Minor coverage issues: {len(gaps)} sections"],
            "confidence": 0.4,
            "path": "minor_refinement"
        })
    else:
        assessment.update({
            "decision": "skip",
            "reason": ["Coverage adequate"],
            "confidence": 0.9,
            "path": "direct_coherence"
        })

    return assessment
```

### 3.2 A/B Testing Gates
```python
# Pattern: A/B testing for refinement strategies
def ab_testing_gate(experiment_config: dict, metrics: dict) -> str:
    """
    A/B test for different refinement approaches
    """
    if experiment_config.get("enable_ab_test"):
        # Random assignment with stratification
        test_group = hash(str(metrics.get("outline_hash"))) % 100

        if test_group < experiment_config.get("test_ratio", 30):
            return "experimental_refinement"
        else:
            return "standard_refinement"

    # Fallback to quality-based routing
    return quality_based_routing(metrics)
```

### 3.3 Human Approval Gates
```python
# Pattern: Human-in-the-loop approval
def human_approval_gate(assessment: dict, workflow_context: dict) -> str:
    """
    Human approval for critical decisions
    """
    # Automatic approval for low-risk decisions
    if assessment["confidence"] > 0.8 and assessment["decision"] == "skip":
        return "auto_approved"

    # Require approval for high-risk decisions
    if assessment["decision"] in ["critical_refine"]:
        workflow_context["pending_approval"] = {
            "type": "critical_refinement",
            "reason": assessment["reason"],
            "confidence": assessment["confidence"]
        }
        return "awaiting_approval"

    # Default to approved for moderate decisions
    return "approved"
```

## 4. Dynamic Workflow Modification

### 4.1 Runtime Workflow Adaptation
```python
# Pattern: Dynamic workflow modification based on intermediate results
async def dynamic_workflow_routing(context: dict) -> List[str]:
    """
    Dynamically modifies workflow path based on execution results
    """
    # Analyze coverage and quality metrics
    coverage_score = calculate_coverage(context)
    coherence_score = calculate_coherence(context)
    relevance_score = calculate_relevance(context)

    # Adaptive routing decisions
    if coverage_score < 0.5:
        # Low coverage - need comprehensive refinement
        return ["refine_coverage", "validate_sources", "coherence_check"]
    elif coherence_score < 0.7:
        # Low coherence - focus on structural refinement
        return ["structural_refinement", "coherence_check"]
    elif relevance_score < 0.6:
        # Low relevance - focus on content enhancement
        return ["content_enhancement", "coherence_check"]
    else:
        # All metrics good - direct to final validation
        return ["final_validation"]
```

### 4.2 Circuit Breaker Pattern
```python
# Pattern: Circuit breaker for failed refinement attempts
class RefinementCircuitBreaker:
    def __init__(self, max_failures=3, reset_timeout=300):
        self.failures = 0
        self.last_failure_time = None
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout

    def should_attempt_refinement(self) -> bool:
        """Check if refinement should be attempted"""
        if self.failures >= self.max_failures:
            if time.time() - self.last_failure_time > self.reset_timeout:
                # Reset circuit breaker
                self.failures = 0
                return True
            else:
                # Circuit is open
                return False
        return True

    def record_attempt(self, success: bool):
        """Record the outcome of a refinement attempt"""
        if success:
            self.failures = 0  # Reset on success
        else:
            self.failures += 1
            self.last_failure_time = time.time()
```

## 5. Implementation Recommendations for n12_gate

### 5.1 Enhanced Quality Assessment
```python
# Enhanced n12_gate with multi-dimensional assessment
def enhanced_refine_gate(context: dict) -> str:
    """
    Enhanced refine gate with intelligent routing
    """
    coverage_report = context.get("coverage", {})
    outline_metrics = context.get("outline_metrics", {})
    quality_history = context.get("quality_history", [])

    # Calculate comprehensive quality score
    quality_score = calculate_quality_score({
        "coverage": coverage_report,
        "outline": outline_metrics,
        "history": quality_history
    })

    # Configure thresholds
    THRESHOLDS = {
        "skip": 0.85,      # Skip if score > 85%
        "minor": 0.70,     # Minor refinement if 70-85%
        "moderate": 0.50,  # Moderate refinement if 50-70%
        "critical": 0.0    # Critical refinement if < 50%
    }

    # Route based on quality score
    if quality_score > THRESHOLDS["skip"]:
        return "skip_to_coherence"
    elif quality_score > THRESHOLDS["moderate"]:
        return "light_refinement"
    elif quality_score > THRESHOLDS["critical"]:
        return "moderate_refinement"
    else:
        return "critical_refinement"
```

### 5.2 Implementation Strategy

#### Phase 1: Basic Quality Routing (Week 1)
1. Add quality score calculation
2. Implement simple thresholds
3. Update workflow JSON configuration
4. Add unit tests

#### Phase 2: Multi-Dimensional Assessment (Week 2)
1. Add coverage completeness metric
2. Add structural coherence metric
3. Add relevance metric
4. Implement weighted scoring

#### Phase 3: Advanced Features (Week 3)
1. Add A/B testing capability
2. Implement circuit breaker
3. Add human approval workflow
4. Create dashboard for monitoring

### 5.3 Updated Workflow JSON Structure
```json
{
  "id": "n12_gate",
  "type": "condition",
  "data": {
    "name": "Enhanced Refine Gate",
    "conditions": {
      "0": "quality_assessment.decision == 'critical_refinement'",
      "1": "quality_assessment.decision == 'moderate_refinement'",
      "2": "quality_assessment.decision == 'minor_refinement'",
      "3": "quality_assessment.decision == 'skip'"
    },
    "quality_thresholds": {
      "critical": 0.5,
      "moderate": 0.7,
      "minor": 0.85,
      "skip": 0.9
    },
    "metrics_weights": {
      "coverage": 0.4,
      "coherence": 0.3,
      "relevance": 0.3
    }
  }
}
```

## 6. Performance and Monitoring

### 6.1 Quality Metrics Tracking
```python
class QualityMetrics:
    def __init__(self):
        self.metrics = {
            "coverage_completeness": 0.0,
            "structural_coherence": 0.0,
            "content_relevance": 0.0,
            "overall_score": 0.0,
            "refinement_attempts": 0,
            "success_rate": 0.0
        }

    def calculate_weighted_score(self, weights: dict) -> float:
        """Calculate weighted quality score"""
        return (
            self.metrics["coverage_completeness"] * weights["coverage"] +
            self.metrics["structural_coherence"] * weights["coherence"] +
            self.metrics["content_relevance"] * weights["relevance"]
        )
```

### 6.2 Monitoring Dashboard
```python
# Monitor quality gate performance
def monitor_quality_gates():
    metrics = {
        "total_executions": 1000,
        "skipped_refinements": 350,  # 35%
        "minor_refinements": 400,     # 40%
        "moderate_refinements": 200,  # 20%
        "critical_refinements": 50,   # 5%
        "average_quality_score": 0.75,
        "refinement_success_rate": 0.88
    }

    # Alert on anomalies
    if metrics["critical_refinements"] > 100:
        alert("High rate of critical refinements")

    if metrics["skipped_refinements"] > 500:
        alert("Too many refinements being skipped")
```

## 7. Testing Strategy

### 7.1 Unit Tests
```python
# Test quality assessment logic
def test_quality_assessment():
    # Test with perfect coverage
    context = {"coverage": {"gaps": []}, "outline_metrics": {"completeness": 1.0}}
    result = enhanced_refine_gate(context)
    assert result == "skip_to_coherence"

    # Test with critical gaps
    context = {"coverage": {"gaps": ["s1", "s2", "s3", "s4", "s5"]}}
    result = enhanced_refine_gate(context)
    assert result == "critical_refinement"
```

### 7.2 Integration Tests
```python
# Test end-to-end workflow with quality routing
@pytest.mark.asyncio
async def test_refine_gate_integration():
    workflow = WorkflowEngine(...)
    await workflow.start()

    # Verify correct routing based on quality
    assert "n13_coh" in execution_path
    if quality_score > 0.85:
        assert "refinement_nodes" not in execution_path
    else:
        assert "refinement_nodes" in execution_path
```

## 8. Conclusion

The enhanced Refine Gate should implement:

1. **Multi-dimensional quality assessment** - Coverage, coherence, relevance
2. **Configurable thresholds** - Allow adjustment based on project needs
3. **Adaptive routing** - Skip refinement when quality is excellent
4. **Monitoring and feedback** - Track effectiveness and refine thresholds
5. **Fail-safe mechanisms** - Circuit breaker for failed refinements

This approach will significantly improve workflow efficiency by avoiding unnecessary refinement when quality metrics are met, while ensuring adequate refinement when needed.