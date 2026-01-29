# Quality Assessment - Archived Files

**Date Archived:** 2026-01-28
**Reason:** Code was using fake hardcoded scores and was not production-ready

## Archived Files

| Original Location | Archived Name | Lines | Reason |
|-------------------|---------------|-------|--------|
| `backend/app/workflow/quality_assessment.py` | `quality_assessment.py` | ~363 | Main quality assessment module |
| `backend/app/workflow/quality_assessment_utils.py` | `quality_assessment_utils.py` | ~155 | Utility functions |
| `backend/app/workflow/components/quality_assessment.py` | `archived_components_quality_assessment.py` | ~109 | Component version |
| `backend/app/workflow/nodes/refine_gate_node.py` | `archived_refine_gate_node.py` | ~90 | Node implementation |
| `backend/app/workflow/executors/quality_gate_executor.py` | `archived_quality_gate_executor.py` | ~296 | Executor with fake scores |

## Why Was This Archived?

The quality assessment system had critical issues:

1. **Hardcoded Placeholder Scores**: Values like `0.75` and `0.85` were hardcoded instead of being calculated
2. **Not Used in Production**: The quality assessment engine was instantiated but never actually called
3. **Fake Metrics**: Source compliance always returned 0 (loop did nothing)
4. **Missing NLP Analysis**: No actual topic alignment verification
5. **Inconsistent Implementations**: 3 separate modules with different algorithms

## What About workflow_engine.py?

The `workflow_engine.py` file contains its own local `QualityAssessmentEngine` class (lines 38-130+). This class:
- IS instantiated (line 454)
- Is NOT actually called anywhere
- Should be removed or implemented properly

## Restoration

If you want to restore this functionality:

1. Implement real quality metrics (not hardcoded values)
2. Add actual NLP analysis for topic alignment
3. Implement source coverage verification
4. Integrate properly with workflow_engine.py
5. Add tests

See `docs/plans/2026-01-28-codebase-remediation.md` for context.

## Alternative: Remove Entirely

Given the complexity and lack of production readiness, consider removing the quality assessment system entirely:
1. Delete the local `QualityAssessmentEngine` class from `workflow_engine.py`
2. Remove the `self.quality_assessor` instantiation
3. Focus on simpler conditional routing (direct property checks)
