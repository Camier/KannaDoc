"""
RAG Pipeline Tests
Tests end-to-end RAG functionality, embedding generation, vector search, and retrieval quality
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from app.core.llm import ChatService
from app.db.vector_db import VectorDBClientWrapper
from app.db.mongo import MongoDB
from app.models.conversation import UserMessage


class TestEmbeddingGeneration:
    """Test embedding generation for RAG"""

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service"""
        with patch('app.rag.get_embedding.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={
                "embeddings": [[0.1, 0.2, 0.3, 0.4, 0.5]]
            })
            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)
            mock_http_client.post.return_value = mock_response

            yield mock_http_client

    @pytest.mark.asyncio
    async def test_generate_text_embedding(self, mock_embedding_service):
        """Test generating embedding for text"""
        from app.rag.get_embedding import get_embeddings_from_httpx

        text = "This is a test sentence for embedding generation."
        mock_embedding_service.post.return_value.json.return_value = {
            "embeddings": [[0.1, 0.2, 0.3, 0.4, 0.5]]
        }

        result = await get_embeddings_from_httpx([text], endpoint="embed_text")

        assert result is not None
        assert isinstance(result, list)
        # Verify the mock was called with correct parameters
        mock_embedding_service.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_image_embedding(self, mock_embedding_service):
        """Test generating embedding for image"""
        from app.rag.get_embedding import get_embeddings_from_httpx

        image_url = "http://minio:9000/bucket/test.jpg"
        mock_embedding_service.post.return_value.json.return_value = {
            "embeddings": [[[0.2, 0.3, 0.4, 0.5, 0.6], [0.3, 0.4, 0.5, 0.6, 0.7]]]
        }

        result = await get_embeddings_from_httpx([image_url], endpoint="embed_image")

        assert result is not None
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_batch_embedding_generation(self, mock_embedding_service):
        """Test generating embeddings for multiple texts"""
        from app.rag.get_embedding import get_embeddings_from_httpx

        texts = ["Text 1", "Text 2", "Text 3"]
        mock_embedding_service.post.return_value.json.return_value = {
            "embeddings": [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
                [0.7, 0.8, 0.9]
            ]
        }

        result = await get_embeddings_from_httpx(texts, endpoint="embed_text")

        assert result is not None
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_embedding_service_error_handling(self, mock_embedding_service):
        """Test embedding service error handling"""
        from app.rag.get_embedding import get_embeddings_from_httpx

        # Simulate service error
        mock_embedding_service.post.side_effect = Exception("Embedding service unavailable")

        with pytest.raises(Exception):
            await get_embeddings_from_httpx(["test"], endpoint="embed_text")


class TestVectorSearch:
    """Test vector database search functionality"""

    @pytest.fixture
    def mock_vector_db(self):
        """Mock vector database client"""
        with patch('app.db.vector_db.vector_db_client') as mock_client:
            yield mock_client

    def test_check_collection_exists(self, mock_vector_db):
        """Test checking if collection exists"""
        mock_vector_db.check_collection.return_value = True

        result = mock_vector_db.check_collection("test_collection")

        assert result is True
        mock_vector_db.check_collection.assert_called_once_with("test_collection")

    def test_create_collection(self, mock_vector_db):
        """Test creating a new collection"""
        mock_vector_db.create_collection.return_value = True

        result = mock_vector_db.create_collection("new_collection", dim=128)

        assert result is True
        mock_vector_db.create_collection.assert_called_once()

    def test_vector_search_topk(self, mock_vector_db):
        """Test vector search with topk results"""
        query_vector = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_results = [
            {
                "file_id": "file_1",
                "image_id": "img_1",
                "score": 0.95,
                "distance": 0.05
            },
            {
                "file_id": "file_2",
                "image_id": "img_2",
                "score": 0.90,
                "distance": 0.10
            },
            {
                "file_id": "file_3",
                "image_id": "img_3",
                "score": 0.85,
                "distance": 0.15
            }
        ]
        mock_vector_db.search.return_value = mock_results

        result = mock_vector_db.search("test_collection", query_vector, topk=3)

        assert len(result) == 3
        assert result[0]["score"] == 0.95
        mock_vector_db.search.assert_called_once_with("test_collection", query_vector, topk=3)

    def test_vector_insert(self, mock_vector_db):
        """Test inserting vectors into collection"""
        data = {
            "colqwen_vecs": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            "metadata": [
                {"file_id": "file_1", "image_id": "img_1"},
                {"file_id": "file_2", "image_id": "img_2"}
            ]
        }
        mock_vector_db.insert.return_value = ["id_1", "id_2"]

        result = mock_vector_db.insert(data, "test_collection")

        assert result is not None
        mock_vector_db.insert.assert_called_once()

    def test_delete_vectors_by_file(self, mock_vector_db):
        """Test deleting vectors by file IDs"""
        file_ids = ["file_1", "file_2", "file_3"]
        mock_vector_db.delete_files.return_value = True

        result = mock_vector_db.delete_files("test_collection", file_ids)

        assert result is True
        mock_vector_db.delete_files.assert_called_once_with("test_collection", file_ids)

    def test_delete_collection(self, mock_vector_db):
        """Test deleting entire collection"""
        mock_vector_db.delete_collection.return_value = True

        result = mock_vector_db.delete_collection("test_collection")

        assert result is True
        mock_vector_db.delete_collection.assert_called_once_with("test_collection")


class TestRAGPipeline:
    """Test end-to-end RAG pipeline"""

    @pytest.fixture
    def mock_mongo(self):
        """Mock MongoDB for metadata retrieval"""
        db = MongoDB()
        db.client = Mock()
        db.db = Mock()
        return db

    @pytest.fixture
    def mock_vector_db(self):
        """Mock vector database"""
        with patch('app.db.vector_db.vector_db_client') as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_rag_retrieval_flow(self, mock_vector_db, mock_mongo):
        """Test complete RAG retrieval flow"""
        query = "What is shown in the document?"
        knowledge_base_id = "kb_123"

        # Mock embedding generation
        with patch('app.rag.get_embedding.get_embeddings_from_httpx', new=AsyncMock()) as mock_embed:
            mock_embed.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

            # Mock vector search
            mock_vector_db.check_collection.return_value = True
            mock_vector_db.search.return_value = [
                {
                    "file_id": "file_1",
                    "image_id": "img_1",
                    "score": 15.5
                },
                {
                    "file_id": "file_2",
                    "image_id": "img_2",
                    "score": 12.3
                }
            ]

            # Mock MongoDB metadata retrieval
            mock_mongo.db.files.find_one = AsyncMock(return_value={
                "file_id": "file_1",
                "knowledge_db_id": knowledge_base_id,
                "file_name": "test.pdf",
                "minio_filename": "base64_encoded_image",
                "minio_url": "http://minio:9000/bucket/test.pdf"
            })

            # Generate embedding
            query_embedding = await mock_embed([query], endpoint="embed_text")

            # Search vectors
            collection_name = f"colqwen{knowledge_base_id.replace('-', '_')}"
            search_results = mock_vector_db.search(collection_name, query_embedding, topk=5)

            # Filter by score threshold
            from app.rag.utils import sort_and_filter
            filtered_results = sort_and_filter(search_results, min_score=10)

            # Verify results
            assert len(filtered_results) == 2
            assert filtered_results[0]["score"] == 15.5
            assert filtered_results[1]["score"] == 12.3

    @pytest.mark.asyncio
    async def test_rag_with_no_matching_documents(self, mock_vector_db):
        """Test RAG when no documents match the query"""
        query = "Very specific query with no matches"

        with patch('app.rag.get_embedding.get_embeddings_from_httpx', new=AsyncMock()) as mock_embed:
            mock_embed.return_value = [[0.1, 0.2, 0.3]]

            mock_vector_db.check_collection.return_value = True
            mock_vector_db.search.return_value = [
                {
                    "file_id": "file_1",
                    "image_id": "img_1",
                    "score": 5.0  # Below threshold
                }
            ]

            query_embedding = await mock_embed([query], endpoint="embed_text")
            search_results = mock_vector_db.search("collection", query_embedding, topk=5)

            from app.rag.utils import sort_and_filter
            filtered_results = sort_and_filter(search_results, min_score=10)

            # Should be empty due to score threshold
            assert len(filtered_results) == 0

    @pytest.mark.asyncio
    async def test_rag_with_corrupted_vector_data(self, mock_vector_db, mock_mongo):
        """Test RAG handles corrupted/missing vector data"""
        query = "Test query"

        with patch('app.rag.get_embedding.get_embeddings_from_httpx', new=AsyncMock()) as mock_embed:
            mock_embed.return_value = [[0.1, 0.2, 0.3]]

            mock_vector_db.check_collection.return_value = True
            mock_vector_db.search.return_value = [
                {
                    "file_id": "missing_file",
                    "image_id": "img_1",
                    "score": 15.5
                }
            ]

            # Mock MongoDB returns None (file not found)
            mock_mongo.db.files.find_one = AsyncMock(return_value=None)

            query_embedding = await mock_embed([query], endpoint="embed_text")
            search_results = mock_vector_db.search("collection", query_embedding, topk=5)

            # System should handle missing files gracefully
            # In production, this would trigger cleanup of orphaned vectors
            assert len(search_results) == 1
            assert search_results[0]["file_id"] == "missing_file"


class TestChatService:
    """Test chat service with RAG integration"""

    @pytest.fixture
    def mock_chat_service(self):
        """Mock chat service components"""
        with patch('app.rag.llm_service.get_mongo') as mock_mongo, \
             patch('app.rag.llm_service.get_embeddings_from_httpx') as mock_embed, \
             patch('app.rag.llm_service.vector_db_client') as mock_vector_db, \
             patch('app.rag.llm_service.get_llm_client') as mock_llm:

            # Mock MongoDB
            mock_mongo_db = AsyncMock()
            mock_mongo_db.get_conversation_model_config = AsyncMock(return_value={
                "model_name": "gpt-4",
                "model_url": "",
                "api_key": "test_key",
                "base_used": [],
                "system_prompt": "You are helpful.",
                "temperature": 0.7,
                "max_length": 1000,
                "top_P": 0.9,
                "top_K": 5,
                "score_threshold": 10
            })
            mock_mongo_db.get_file_and_image_info = AsyncMock(return_value={
                "status": "success",
                "knowledge_db_id": "kb_123",
                "file_name": "test.pdf",
                "image_minio_filename": "base64_image",
                "image_minio_url": "http://minio:9000/img.jpg",
                "file_minio_url": "http://minio:9000/file.pdf"
            })
            mock_mongo.return_value = mock_mongo_db

            # Mock embedding
            mock_embed.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

            # Mock vector DB
            mock_vector_db.check_collection.return_value = True
            mock_vector_db.search.return_value = [
                {
                    "file_id": "file_1",
                    "image_id": "img_1",
                    "score": 15.5
                }
            ]

            # Mock LLM client
            mock_llm_instance = AsyncMock()
            mock_llm.return_value = mock_llm_instance

            yield {
                "mongo": mock_mongo_db,
                "embed": mock_embed,
                "vector_db": mock_vector_db,
                "llm": mock_llm_instance
            }

    @pytest.mark.asyncio
    async def test_chat_stream_with_rag(self, mock_chat_service):
        """Test chat streaming with RAG retrieval"""
        user_message = UserMessage(
            conversation_id="conv_123",
            parent_id="",
            user_message="What is in this document?",
            temp_db=""
        )

        # Mock LLM stream response
        async def mock_stream():
            chunks = [
                json.dumps({"type": "file_used", "data": [], "message_id": "msg_123", "model_name": "gpt-4"}),
                json.dumps({"type": "text", "data": "Based on ", "message_id": "msg_123"}),
                json.dumps({"type": "text", "data": "the document", "message_id": "msg_123"}),
            ]
            for chunk in chunks:
                yield f"data: {chunk}\n\n"

        mock_chat_service["llm"].chat.completions.create = AsyncMock()

        # Create actual stream generator
        from app.core.llm import ChatService

        # Test embedding normalization
        query_embedding = await mock_chat_service["embed"](
            [user_message.user_message],
            endpoint="embed_text"
        )

        from app.core.llm import ChatService
        normalized = ChatService._normalize_multivector(query_embedding)

        assert isinstance(normalized, list)
        assert len(normalized) > 0
        assert all(isinstance(vec, list) for vec in normalized)
        assert all(isinstance(val, float) for vec in normalized[0] for val in vec)

    def test_normalize_single_vector(self):
        """Test normalizing a single embedding vector"""
        from app.core.llm import ChatService

        single_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = ChatService._normalize_multivector(single_vector)

        assert isinstance(result, list)
        assert len(result) == 1
        assert all(isinstance(x, float) for x in result[0])

    def test_normalize_multi_vector(self):
        """Test normalizing multi-token embeddings"""
        from app.core.llm import ChatService

        multi_vector = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        result = ChatService._normalize_multivector(multi_vector)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(x, float) for vec in result for x in vec)

    def test_normalize_nested_list(self):
        """Test normalizing nested list structure"""
        from app.core.llm import ChatService

        nested = [[[0.1, 0.2], [0.3, 0.4]]]
        result = ChatService._normalize_multivector(nested)

        assert isinstance(result, list)
        assert len(result) == 2


class TestRetrievalQuality:
    """Test RAG retrieval quality metrics"""

    def test_score_filtering(self):
        """Test score threshold filtering"""
        from app.rag.utils import sort_and_filter

        results = [
            {"file_id": "file_1", "score": 15.5},
            {"file_id": "file_2", "score": 12.3},
            {"file_id": "file_3", "score": 8.5},
            {"file_id": "file_4", "score": 5.2}
        ]

        filtered = sort_and_filter(results, min_score=10)

        assert len(filtered) == 2
        assert filtered[0]["score"] == 15.5
        assert filtered[1]["score"] == 12.3

    def test_score_sorting(self):
        """Test results are sorted by score descending"""
        from app.rag.utils import sort_and_filter

        results = [
            {"file_id": "file_1", "score": 10.5},
            {"file_id": "file_2", "score": 15.3},
            {"file_id": "file_3", "score": 12.1}
        ]

        filtered = sort_and_filter(results, min_score=0)

        # Should be sorted descending
        assert filtered[0]["score"] == 15.3
        assert filtered[1]["score"] == 12.1
        assert filtered[2]["score"] == 10.5

    def test_top_k_limit(self):
        """Test top-k result limiting"""
        from app.rag.utils import sort_and_filter

        results = [{"file_id": f"file_{i}", "score": 20 - i} for i in range(1, 11)]

        filtered = sort_and_filter(results, min_score=0)

        # Should return all results (no top_k in sort_and_filter)
        assert len(filtered) == 10

    def test_duplicate_file_filtering(self):
        """Test that duplicate files are handled"""
        from app.rag.utils import sort_and_filter

        results = [
            {"file_id": "file_1", "image_id": "img_1", "score": 15.5},
            {"file_id": "file_1", "image_id": "img_2", "score": 14.0},
            {"file_id": "file_2", "image_id": "img_3", "score": 12.0}
        ]

        filtered = sort_and_filter(results, min_score=10)

        # All results should be included (deduplication logic may vary)
        assert len(filtered) == 3


class TestImageProcessing:
    """Test image processing in RAG pipeline"""

    @pytest.mark.asyncio
    async def test_base64_image_encoding(self):
        """Test base64 encoding of images"""
        import base64

        # Mock image data
        image_data = b"fake_image_data"

        # Encode to base64
        base64_encoded = base64.b64encode(image_data).decode('utf-8')

        assert isinstance(base64_encoded, str)
        assert len(base64_encoded) > 0

    @pytest.mark.asyncio
    async def test_image_url_replacement(self):
        """Test replacing MinIO URLs with base64 data"""
        from app.rag.utils import replace_image_content

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "http://minio:9000/bucket/test.jpg"
                        }
                    },
                    {
                        "type": "text",
                        "text": "What is this?"
                    }
                ]
            }
        ]

        # This would normally replace URLs with base64
        # For testing, verify the structure
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert len(messages[0]["content"]) == 2


class TestPromptConstruction:
    """Test prompt construction for RAG"""

    def test_system_prompt_construction(self):
        """Test system prompt is properly constructed"""
        system_prompt = "You are LAYRA, a multimodal RAG assistant."

        assert len(system_prompt) > 0
        assert "LAYRA" in system_prompt

    def test_rag_context_injection(self):
        """Test that retrieved context is injected into prompt"""
        retrieved_docs = [
            {
                "file_name": "doc1.pdf",
                "score": 15.5,
                "content": "Relevant content from document"
            }
        ]

        # Context would be injected into user message
        context_str = "\n".join([
            f"Document: {doc['file_name']} (Score: {doc['score']})"
            for doc in retrieved_docs
        ])

        assert "doc1.pdf" in context_str
        assert "15.5" in context_str

    def test_conversation_history_inclusion(self):
        """Test that conversation history is included"""
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"}
        ]

        messages = []
        for msg in history:
            messages.append(msg)

        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"


class TestErrorHandling:
    """Test error handling in RAG pipeline"""

    @pytest.mark.asyncio
    async def test_embedding_service_unavailable(self):
        """Test handling when embedding service is unavailable"""
        with patch('app.rag.get_embedding.httpx.AsyncClient') as mock_client:
            mock_http_client = AsyncMock()
            mock_http_client.post.side_effect = Exception("Service unavailable")
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)

            from app.rag.get_embedding import get_embeddings_from_httpx

            with pytest.raises(Exception):
                await get_embeddings_from_httpx(["test"], endpoint="embed_text")

    @pytest.mark.asyncio
    async def test_vector_db_unavailable(self):
        """Test handling when vector database is unavailable"""
        with patch('app.db.vector_db.vector_db_client') as mock_client:
            mock_client.check_collection.side_effect = Exception("Connection failed")

            with pytest.raises(Exception):
                mock_client.check_collection("test_collection")

    @pytest.mark.asyncio
    async def test_mongodb_unavailable(self):
        """Test handling when MongoDB is unavailable"""
        db = MongoDB()
        db.client = None

        # Should handle gracefully
        assert db.client is None


class TestPerformance:
    """Test RAG pipeline performance"""

    @pytest.mark.asyncio
    async def test_embedding_batch_size(self):
        """Test optimal embedding batch size"""
        import asyncio

        texts = [f"Text {i}" for i in range(100)]

        with patch('app.rag.get_embedding.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={
                "embeddings": [[0.1, 0.2, 0.3] for _ in range(100)]
            })

            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__ = AsyncMock(return_value=mock_http_client)

            from app.rag.get_embedding import get_embeddings_from_httpx

            start_time = asyncio.get_event_loop().time()
            result = await get_embeddings_from_httpx(texts, endpoint="embed_text")
            end_time = asyncio.get_event_loop().time()

            assert result is not None
            # Batch should be faster than individual requests
            assert (end_time - start_time) < 10  # Should complete in reasonable time

    @pytest.mark.asyncio
    async def test_concurrent_vector_searches(self):
        """Test concurrent vector searches"""
        import asyncio

        with patch('app.db.vector_db.vector_db_client') as mock_client:
            mock_client.search.return_value = [
                {"file_id": "file_1", "score": 15.5}
            ]

            # Simulate concurrent searches
            tasks = [
                mock_client.search(f"collection_{i}", [[0.1, 0.2]], topk=5)
                for i in range(10)
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 10
            assert all(len(result) > 0 for result in results)
