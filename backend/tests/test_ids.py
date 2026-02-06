from app.utils.ids import to_milvus_collection_name


def test_to_milvus_collection_name_preserves_colpali_collection_names():
    assert to_milvus_collection_name("colpali_kanna_128") == "colpali_kanna_128"
    assert (
        to_milvus_collection_name("default.colpali_kanna_128") == "colpali_kanna_128"
    )
    assert (
        to_milvus_collection_name("colpali_kanna_128_pages_sparse")
        == "colpali_kanna_128_pages_sparse"
    )


def test_to_milvus_collection_name_preserves_colqwen_collection_names():
    # Already-converted KB collection names should not be double-prefixed.
    assert to_milvus_collection_name("colqwenkb_123") == "colqwenkb_123"


def test_to_milvus_collection_name_converts_kb_ids():
    assert (
        to_milvus_collection_name("kb_550e8400-e29b-41d4-a716-446655440000")
        == "colqwenkb_550e8400_e29b_41d4_a716_446655440000"
    )

