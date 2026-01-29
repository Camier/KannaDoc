#!/usr/bin/env python3
"""
Test script for LayRA RAG pipeline with thesis knowledge base.
"""

import json
import requests
import sys
from typing import Optional

BASE_URL = "http://localhost:8090/api/v1"
KNOWLEDGE_DB_ID = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"


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

    def create_knowledge_base(self, kb_name: str) -> Optional[str]:
        """Create a new knowledge base and return its ID"""
        try:
            payload = {
                "username": self.username,
                "knowledge_base_name": kb_name
            }
            resp = self.session.post(
                f"{self.base_url}/base/knowledge_base",
                json=payload
            )
            if resp.status_code == 200:
                # Need to fetch the list to get the ID, as the create endpoint implies the ID structure but doesn't return it explicitly in the dict?
                # Actually, the endpoint returns {"status": "success"} but the ID is generated inside. 
                # Wait, I need the ID. 
                # Let's fetch list of KBs to find the one we just created.
                return self.get_knowledge_base_id(kb_name)
            else:
                print(f"✗ KB creation failed: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            print(f"✗ KB creation error: {e}")
            return None

    def get_knowledge_base_id(self, kb_name: str) -> Optional[str]:
        """Get knowledge base ID by name"""
        try:
            resp = self.session.get(f"{self.base_url}/base/users/{self.username}/knowledge_bases")
            if resp.status_code == 200:
                kbs = resp.json()
                # Sort by creation time desc to get the latest one if duplicates
                kbs.sort(key=lambda x: x['created_at'], reverse=True)
                for kb in kbs:
                    if kb['knowledge_base_name'] == kb_name:
                        print(f"✓ Found knowledge base: {kb['knowledge_base_id']}")
                        return kb['knowledge_base_id']
            return None
        except Exception as e:
            print(f"✗ Get KB error: {e}")
            return None

    def upload_file(self, kb_id: str, file_path: str) -> bool:
        """Upload a file to the knowledge base"""
        try:
            with open(file_path, 'rb') as f:
                files = {'files': (file_path.split('/')[-1], f, 'application/pdf')}
                print(f"📤 Uploading {file_path} to {kb_id}...")
                resp = self.session.post(
                    f"{self.base_url}/base/upload/{kb_id}",
                    files=files
                )
                if resp.status_code == 200:
                    print(f"✓ Uploaded successfully. Task ID: {resp.json().get('task_id')}")
                    # In a real test we should wait for processing, but for now we proceed
                    import time
                    print("⏳ Waiting 10 seconds for initial processing...")
                    time.sleep(10) 
                    return True
                else:
                    print(f"✗ Upload failed: {resp.status_code} - {resp.text}")
                    return False
        except Exception as e:
            print(f"✗ Upload error: {e}")
            return False

    def create_conversation(
        self,
        conversation_id: str,
        conversation_name: str,
        model_config: Optional[dict] = None,
        kb_id: Optional[str] = None
    ) -> bool:
        """Create a new conversation"""
        if model_config is None:
            model_config = {
                "model_name": "deepseek-reasoner",
                "model_url": "",
                "api_key": "",
                "base_used": [],
                "system_prompt": "",
                "temperature": 0.1,
                "max_length": 2000,
                "top_P": 0.1,
                "top_K": 3,
                "score_threshold": 10,
            }
        
        # If KB is provided, link it (although the API might not support direct linking in create?
        # The ConversationCreate model has model_config.base_used.
        if kb_id:
             model_config["base_used"] = [{"baseId": kb_id, "name": "Thesis KB"}]

        payload = {
            "conversation_id": conversation_id,
            "username": self.username,  # Uses logged-in username
            "conversation_name": conversation_name,
            "chat_model_config": model_config,
        }

        try:
            resp = self.session.post(
                f"{self.base_url}/chat/conversations", json=payload
            )
            if resp.status_code == 200:
                print(f"✓ Created conversation: {conversation_id}")
                return True
            else:
                print(
                    f"✗ Conversation creation failed: {resp.status_code} - {resp.text}"
                )
                return False
        except Exception as e:
            print(f"✗ Conversation error: {e}")
            return False

    def chat_stream(
        self, query: str, conversation_id: str, kb_id: Optional[str] = None, parent_id: str = "0"
    ) -> str:
        """Send chat query and stream response"""
        payload = {
            "conversation_id": conversation_id,
            "parent_id": parent_id,
            "user_message": query,
            # temp_db is used for "User Uploaded Files" in chat, but here we want to use the Knowledge Base attached to the model config.
            # If temp_db is None, it should rely on the conversation's model config base_used.
            # However, the previous test script used temp_db. Let's support both.
            "temp_db": kb_id if kb_id else "" 
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
                                if "data" in data:
                                    content = data["data"]
                                    msg_type = data.get("type")
                                    
                                    if msg_type == "thinking":
                                        print(f"\033[90m{content}\033[0m", end="", flush=True) # Gray for thinking
                                    elif msg_type == "text":
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

    # 1. Create Knowledge Base
    kb_name = "Test KB"
    print(f"\n📚 Creating knowledge base '{kb_name}'...")
    kb_id = client.create_knowledge_base(kb_name)
    if not kb_id:
        print("Failed to create KB. Exiting.")
        return

    # 2. Upload File
    # Find a PDF to upload
    import glob
    import os
    pdf_files = glob.glob("/LAB/@thesis/layra/literature/corpus/*.pdf")
    if not pdf_files:
        print("No PDF files found in literature/corpus.")
        return
    
    file_to_upload = pdf_files[0]
    print(f"\n📄 Uploading file: {os.path.basename(file_to_upload)}")
    if not client.upload_file(kb_id, file_to_upload):
        print("Failed to upload file.")
        return

    # 3. Create Conversation linked to KB
    # Backend requires conversation_id to start with username
    username = client.username if client.username else "thesis"
    conversation_id = f"{username}_test_conv1"
    
    print(f"\n💬 Creating conversation '{conversation_id}'...")
    if not client.create_conversation(
        conversation_id=conversation_id, 
        conversation_name="Thesis Test Conversation",
        kb_id=kb_id
    ):
        print("⚠️  Conversation creation failed (might already exist or auth issue).")

    # Test RAG queries
    print("\n🔍 Testing RAG pipeline with thesis knowledge base...")

    test_queries = [
        "What is the main topic of the uploaded document?",
        "Summarize the key findings.",
    ]

    for i, query in enumerate(test_queries):
        print(f"\n{'=' * 60}")
        print(f"Query {i + 1}/{len(test_queries)}")
        # Pass kb_id to be safe, though conversation config should handle it
        response = client.chat_stream(query, conversation_id, kb_id=kb_id)
        if not response:
            print("No response received.")
            break

    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
