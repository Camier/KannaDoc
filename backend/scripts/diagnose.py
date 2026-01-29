#!/usr/bin/env python3
"""
Diagnose LayRA RAG pipeline issues.
"""

import asyncio
import json
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from pymilvus import MilvusClient


async def test_mongodb():
    """Test MongoDB connection and data"""
    print("🧪 Testing MongoDB...")
    try:
        client = AsyncIOMotorClient(
            "mongodb://thesis:thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac@mongodb:27017/chat_mongodb?authSource=admin"
        )

        # Test connection
        await client.admin.command("ping")
        print("  ✓ MongoDB connection OK")

        # Count files for thesis knowledge base
        count = await client.chat_mongodb.files.count_documents(
            {"knowledge_db_id": "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"}
        )
        print(f"  ✓ Files in knowledge base: {count}")

        # Check conversation
        conv = await client.chat_mongodb.conversations.find_one(
            {"conversation_id": "testuser2291_thesis_test"}
        )
        if conv:
            print(f"  ✓ Conversation found")
            cfg = conv.get("model_config", {})
            print(f"  ✓ Model config keys: {list(cfg.keys())}")
        else:
            print("  ✗ Conversation not found")

        return True
    except Exception as e:
        print(f"  ✗ MongoDB error: {e}")
        return False


def test_milvus():
    """Test Milvus connection and search"""
    print("🧪 Testing Milvus...")
    try:
        client = MilvusClient(uri="http://milvus-standalone:19530")

        # Check collection
        coll_name = "colqwenthesis_fbd5d3a6_3911_4be0_a4b3_864ec91bc3c1"
        exists = client.has_collection(coll_name)
        print(f"  ✓ Collection exists: {exists}")

        if exists:
            stats = client.get_collection_stats(coll_name)
            print(f"  ✓ Vectors: {stats['row_count']:,}")

            # Try a simple search (need embeddings first)
            print(f"  ⚠️  Search test requires embeddings")

        return True
    except Exception as e:
        print(f"  ✗ Milvus error: {e}")
        return False


async def test_embeddings():
    """Test embedding generation"""
    print("🧪 Testing Embedding Model...")
    try:
        import httpx
        from app.rag.get_embedding import get_embeddings_from_httpx

        # Test with a simple query
        query = ["Sceletium tortuosum"]
        embeddings = await get_embeddings_from_httpx(query, endpoint="embed_text")
        print(f"  ✓ Embeddings generated: {len(embeddings)} vectors")
        print(f"  ✓ Vector dimension: {len(embeddings[0])}")
        return True
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Embedding error: {e}")
        return False


def test_deepseek_api():
    """Test DeepSeek API connectivity"""
    print("🧪 Testing DeepSeek API...")
    try:
        import requests

        api_key = "sk-29537d2ba74445f0894e53e48ca1d9ef"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Simple test request
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10,
        }

        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=data,
            timeout=10,
        )

        if response.status_code == 200:
            print(f"  ✓ DeepSeek API accessible")
            return True
        else:
            print(f"  ✗ DeepSeek API error: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  ✗ DeepSeek API test error: {e}")
        return False


async def test_full_rag():
    """Test full RAG pipeline"""
    print("🧪 Testing RAG Pipeline...")
    try:
        from app.rag.get_embedding import get_embeddings_from_httpx
        from pymilvus import MilvusClient

        # Step 1: Generate query embedding
        query = "What is Sceletium tortuosum?"
        print(f"  Query: {query}")

        embeddings = await get_embeddings_from_httpx([query], endpoint="embed_text")
        query_embedding = embeddings[0]
        print(f"  ✓ Query embedding generated")

        # Step 2: Search Milvus
        milvus = MilvusClient(uri="http://milvus-standalone:19530")
        coll_name = "colqwenthesis_fbd5d3a6_3911_4be0_a4b3_864ec91bc3c1"

        results = milvus.search(
            collection_name=coll_name,
            data=[query_embedding],
            limit=5,
            output_fields=["file_id", "image_id", "chunk_text"],
        )

        print(f"  ✓ Vector search returned {len(results)} results")
        for i, hit in enumerate(results[0][:3]):  # Show top 3
            print(
                f"    {i + 1}. Score: {hit['score']:.3f}, File ID: {hit['entity']['file_id']}"
            )
            if "chunk_text" in hit["entity"]:
                text = hit["entity"]["chunk_text"][:100] + "..."
                print(f"       Text: {text}")

        return True
    except Exception as e:
        print(f"  ✗ RAG pipeline error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    print("🔍 Diagnosing LayRA Thesis System")
    print("=" * 60)

    # Run tests
    mongo_ok = await test_mongodb()
    milvus_ok = test_milvus()

    # These tests need to run in backend container context
    print("\n⚠️  Note: Embedding and RAG tests need to run inside backend container")
    print("   Run: docker exec layra-backend python3 /app/diagnose.py")

    print("\n📋 Summary:")
    print(f"  MongoDB: {'✓ OK' if mongo_ok else '✗ Failed'}")
    print(f"  Milvus: {'✓ OK' if milvus_ok else '✗ Failed'}")

    # Manual check suggestions
    print("\n🔧 Manual checks to perform:")
    print("  1. Check model-server is running: docker logs layra-model-server")
    print("  2. Test embedding endpoint: curl http://model-server:8001/embed_text")
    print("  3. Check backend logs: docker logs layra-backend --tail 50")
    print("  4. Verify DeepSeek API key is valid")

    if mongo_ok and milvus_ok:
        print("\n✅ Core database services are functional")
        print("   Issue may be with embedding model or LLM API")
    else:
        print("\n❌ Database issues detected")


if __name__ == "__main__":
    asyncio.run(main())
