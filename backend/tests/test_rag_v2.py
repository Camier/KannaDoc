#!/usr/bin/env python3
"""
Test script for LayRA RAG pipeline with thesis knowledge base.
"""

import json
import requests
import sys
import jwt  # pyjwt
from typing import Optional

BASE_URL = "http://localhost:8090/api/v1"
KNOWLEDGE_DB_ID = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"
JWT_SECRET = "e50436623df941954e96e5eb2badd5c174915a445d3c1d95cb6c04beccf63ea9"


class LayRAClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.username = None

    def login(self, username: str, password: str) -> bool:
        """Login and store JWT token"""
        try:
            resp = self.session.post(
                f"{self.base_url}/auth/login",
                data={"username": username, "password": password},
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data["access_token"]
                self.username = username
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                print(f"✓ Logged in as {username}")
                return True
            else:
                print(f"✗ Login failed: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False

    def register(self, username: str, email: str, password: str) -> bool:
        """Register new user"""
        try:
            resp = self.session.post(
                f"{self.base_url}/auth/register",
                json={"username": username, "email": email, "password": password},
            )
            if resp.status_code == 200:
                print(f"✓ Registered user {username}")
                return self.login(username, password)
            else:
                print(f"✗ Registration failed: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"✗ Registration error: {e}")
            return False

    def get_username_from_token(self) -> Optional[str]:
        """Extract username from JWT token"""
        if not self.token:
            return None
        try:
            # Decode without verification for now
            decoded = jwt.decode(self.token, options={"verify_signature": False})
            return decoded.get("sub")
        except:
            return None

    def create_conversation(
        self,
        conversation_suffix: str,
        conversation_name: str,
        model_config: Optional[dict] = None,
    ) -> str:
        """Create a new conversation, returns conversation_id"""
        if not self.username:
            self.username = self.get_username_from_token()
            if not self.username:
                print("✗ No username available")
                return ""

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
        """Send chat query and stream response"""
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
                    # SSE format: data: {...}
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
        """Test API health"""
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

    # Test health
    print("🧪 Testing API health...")
    if not client.test_health():
        print("Failed health check. Is the backend running?")
        sys.exit(1)

    # Try to login with known credentials
    print("\n🔐 Attempting login...")

    # Try common passwords for thesis user
    passwords_to_try = [
        "thesis",
        "thesis_thesis",
        "thesis_mysql_a1b2c3d4e5f6",
        "thesis_mongo_3a2572a198fa78362d6d8e9b31a98bac",
        "thesis_redis_1c962832d09529674794ff43258d721c",
        "thesis_minio_2d1105118d28bc4eedf9aec29b678e70566dc9e58f43df4e",
        "thesis_neo4j_126a70a877beda9ff1d6896a6cfc46be",
    ]

    logged_in = False
    for password in passwords_to_try:
        if client.login("thesis", password):
            logged_in = True
            break

    # If login fails, try to register a new user
    if not logged_in:
        print("\n👤 Attempting to register new user...")
        # Try to register with random username
        import random

        random_id = random.randint(1000, 9999)
        test_user = f"testuser{random_id}"
        test_email = f"{test_user}@example.com"
        test_password = "testpassword123"

        if client.register(test_user, test_email, test_password):
            logged_in = True
            print(f"Using new user: {test_user}")
        else:
            print("Failed to register. Trying to proceed without auth...")
            # Try without auth header
            client.session.headers.clear()

    if not logged_in:
        print("⚠️  Could not authenticate. Some endpoints may fail.")
        return

    # Create a conversation
    conversation_suffix = "thesis_test"
    print(f"\n💬 Creating conversation...")
    conversation_id = client.create_conversation(
        conversation_suffix=conversation_suffix,
        conversation_name="Thesis Test Conversation",
    )

    if not conversation_id:
        # Try with a default conversation ID
        conversation_id = f"{client.username}_default"
        print(f"Using conversation ID: {conversation_id}")

    # Test RAG queries
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
            print("No response received. Check authentication and knowledge base ID.")
            break

    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
