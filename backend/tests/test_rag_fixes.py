"""Regression tests for RAG pipeline fixes (P1-P7)."""
import pytest
import inspect

pytestmark = pytest.mark.unit


# P1: Eval runner applies normalize + downsample
def test_p1_eval_runner_normalizes_query_vectors():
    """Verify eval runner source contains normalize_multivector and downsample_multivector calls."""
    from app.eval import runner
    source = inspect.getsource(runner)
    assert "normalize_multivector" in source
    assert "downsample_multivector" in source
    assert "settings.rag_max_query_vecs" in source


# P2: Chat service uses run_in_executor for search
def test_p2_chat_service_no_bare_sync_search():
    """Verify no bare vector_db_client.search() calls in chat_service.py."""
    from app.core.llm.chat_service import ChatService
    source = inspect.getsource(ChatService.create_chat_stream)
    assert "run_in_executor" in source
    assert "= vector_db_client.search(" not in source


# P3: No hardcoded model server URL
def test_p3_no_hardcoded_model_server_url():
    """Verify rag/utils.py uses settings.model_server_url."""
    from app.rag import utils
    source = inspect.getsource(utils)
    assert "model-server:8005" not in source
    assert "settings.model_server_url" in source


# P4: Sparse vectors not replicated per patch
def test_p4_sparse_not_replicated():
    """Verify insert_to_milvus doesn't replicate sparse dict per patch."""
    from app.rag.utils import insert_to_milvus
    source = inspect.getsource(insert_to_milvus)
    assert "dict(sparse_page_vecs" not in source


# P5: Sidecar creation method exists
def test_p5_sidecar_creation_method_exists():
    """Verify MilvusManager has ensure_pages_sparse_collection method."""
    from app.db.milvus import MilvusManager
    assert hasattr(MilvusManager, "ensure_pages_sparse_collection")


# P6: Canonical collection name used
def test_p6_no_manual_collection_name():
    """Verify rag/utils.py uses to_milvus_collection_name."""
    from app.rag import utils
    source = inspect.getsource(utils)
    assert 'f"colqwen{' not in source
    assert "to_milvus_collection_name" in source


# P7: No circuit breaker on streaming generator
def test_p7_no_circuit_breaker_on_stream():
    """Verify create_chat_stream is not decorated with llm_service_circuit."""
    from app.core.llm.chat_service import ChatService
    source = inspect.getsource(ChatService)
    lines = source.split('\n')
    for i, line in enumerate(lines):
        if 'def create_chat_stream' in line:
            preceding = '\n'.join(lines[max(0, i-3):i])
            assert 'llm_service_circuit' not in preceding
            break


# P1 supplementary: normalize_multivector correctness
def test_p1_normalize_multivector_unwraps():
    """Verify normalize_multivector handles triple-nested embedding output."""
    from app.core.embeddings import normalize_multivector
    raw = [[[1.0, 0.0], [0.0, 1.0], [3.0, 4.0]]]
    result = normalize_multivector(raw)
    assert len(result) == 3
    assert result[0] == [1.0, 0.0]
    assert result[1] == [0.0, 1.0]
    assert result[2] == [3.0, 4.0]


# P1 supplementary: downsample_multivector caps tokens
def test_p1_downsample_caps_at_max():
    """Verify downsample_multivector limits token count."""
    from app.core.embeddings import downsample_multivector
    vecs = [[float(i)] * 128 for i in range(100)]
    result = downsample_multivector(vecs, 48)
    assert len(result) == 48
