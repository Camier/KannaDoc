#!/usr/bin/env python3
"""
Test script for LayRA RAG pipeline with thesis knowledge base.
Note: Authentication has been removed for research-only deployment.
"""

import json
import requests
import sys
from typing import Optional

BASE_URL = "http://localhost:8090/api/v1"
KNOWLEDGE_DB_ID = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"
DEFAULT_USERNAME = "miko"


class LayRAClient:
    def __init__(self, base_url: str = BASE_URL, username: str = DEFAULT_USERNAME):
        self.base_url = base_url
        self.session = requests.Session()
        self.username = username

    def create_conversation(
        self,
        conversation_suffix: str,
        conversation_name: str,
        model_config: Optional[dict] = None,
    ) -> str:
        conversation_id = f"{self.username}_{conversation_suffix}"

        if model_config is None:
            model_config = {
                "provider": "deepseek",
                "model": "deepseek-reasoner",
                "temperature": 0.1,
                "max_tokens": 2000,
            }

        payload = {
            "conversation_id": conversation_id,
            "username": self.username,
            "conversation_name": conversation_name,
            "chat_model_config": model_config,
        }

        try:
            resp = self.session.post(
                f"{self.base_url}/chat/conversations", json=payload
            )
            if resp.status_code == 200:
                print(f"✓ Created conversation: {conversation_id}")
                return conversation_id
            else:
                print(
                    f"✗ Conversation creation failed: {resp.status_code} - {resp.text}"
                )
                return ""
        except Exception as e:
            print(f"✗ Conversation error: {e}")
            return ""

    def chat_stream(
        self, query: str, conversation_id: str, parent_id: str = "0"
    ) -> str:
        payload = {
            "conversation_id": conversation_id,
            "parent_id": parent_id,
            "user_message": query,
            "temp_db": KNOWLEDGE_DB_ID,
        }

        print(f"\n📝 Query: {query}")
        print("📖 Response:")

        try:
            resp = self.session.post(
                f"{self.base_url}/sse/chat", json=payload, stream=True
            )

            if resp.status_code != 200:
                print(f"✗ Chat request failed: {resp.status_code} - {resp.text}")
                return ""

            full_response = ""
            for line in resp.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str:
                            try:
                                data = json.loads(data_str)
                                if "content" in data:
                                    content = data["content"]
                                    print(content, end="", flush=True)
                                    full_response += content
                            except json.JSONDecodeError:
                                pass

            print("\n")
            return full_response

        except Exception as e:
            print(f"✗ Chat error: {e}")
            return ""

    def test_health(self) -> bool:
        try:
            resp = self.session.get(f"{self.base_url}/health/check")
            if resp.status_code == 200:
                print(f"✓ API health: {resp.json()}")
                return True
            else:
                print(f"✗ Health check failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"✗ Health check error: {e}")
            return False


def main():
    client = LayRAClient()

    print("🧪 Testing API health...")
    if not client.test_health():
        print("Failed health check. Is the backend running?")
        sys.exit(1)

    conversation_suffix = "thesis_test"
    print(f"\n💬 Creating conversation...")
    conversation_id = client.create_conversation(
        conversation_suffix=conversation_suffix,
        conversation_name="Thesis Test Conversation",
    )

    if not conversation_id:
        conversation_id = f"{client.username}_default"
        print(f"Using conversation ID: {conversation_id}")

    print("\n🔍 Testing RAG pipeline with thesis knowledge base...")

    test_queries = [
        "What is Sceletium tortuosum and what are its traditional uses?",
        "What are the main alkaloids found in Sceletium tortuosum?",
        "What pharmacological effects have been reported for Sceletium tortuosum extracts?",
        "How does Sceletium tortuosum affect anxiety and depression?",
    ]

    for i, query in enumerate(test_queries):
        print(f"\n{'=' * 60}")
        print(f"Query {i + 1}/{len(test_queries)}")
        response = client.chat_stream(query, conversation_id)
        if not response:
            print("No response received. Check knowledge base ID.")
            break

    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
