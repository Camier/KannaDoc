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

    def create_knowledge_base(self, kb_name: str) -> Optional[str]:
        try:
            payload = {"username": self.username, "knowledge_base_name": kb_name}
            resp = self.session.post(
                f"{self.base_url}/base/knowledge_base", json=payload
            )
            if resp.status_code == 200:
                return self.get_knowledge_base_id(kb_name)
            else:
                print(f"✗ KB creation failed: {resp.status_code} - {resp.text}")
                return None
        except Exception as e:
            print(f"✗ KB creation error: {e}")
            return None

    def get_knowledge_base_id(self, kb_name: str) -> Optional[str]:
        try:
            resp = self.session.get(f"{self.base_url}/base/knowledge_bases")
            if resp.status_code == 200:
                kbs = resp.json()
                kbs.sort(key=lambda x: x["created_at"], reverse=True)
                for kb in kbs:
                    if kb["knowledge_base_name"] == kb_name:
                        print(f"✓ Found knowledge base: {kb['knowledge_base_id']}")
                        return kb["knowledge_base_id"]
            return None
        except Exception as e:
            print(f"✗ Get KB error: {e}")
            return None

    def upload_file(self, kb_id: str, file_path: str) -> bool:
        try:
            with open(file_path, "rb") as f:
                files = {"files": (file_path.split("/")[-1], f, "application/pdf")}
                print(f"📤 Uploading {file_path} to {kb_id}...")
                resp = self.session.post(
                    f"{self.base_url}/base/upload/{kb_id}", files=files
                )
                if resp.status_code == 200:
                    print(
                        f"✓ Uploaded successfully. Task ID: {resp.json().get('task_id')}"
                    )
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
        kb_id: Optional[str] = None,
    ) -> bool:
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

        if kb_id:
            model_config["base_used"] = [{"baseId": kb_id, "name": "Thesis KB"}]

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
        self,
        query: str,
        conversation_id: str,
        kb_id: Optional[str] = None,
        parent_id: str = "0",
    ) -> str:
        payload = {
            "conversation_id": conversation_id,
            "parent_id": parent_id,
            "user_message": query,
            "temp_db": kb_id if kb_id else "",
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
                                if "data" in data:
                                    content = data["data"]
                                    msg_type = data.get("type")

                                    if msg_type == "thinking":
                                        print(
                                            f"\033[90m{content}\033[0m",
                                            end="",
                                            flush=True,
                                        )
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

    kb_name = "Test KB"
    print(f"\n📚 Creating knowledge base '{kb_name}'...")
    kb_id = client.create_knowledge_base(kb_name)
    if not kb_id:
        print("Failed to create KB. Exiting.")
        return

    import glob
    import os
    from pathlib import Path

    # Avoid hardcoded machine-specific paths; canonical corpus location is
    # layra/backend/data/pdfs (see AGENTS.md + thesis/debug endpoints).
    backend_dir = Path(__file__).resolve().parents[1]
    pdf_files = [str(p) for p in sorted((backend_dir / "data" / "pdfs").glob("*.pdf"))]
    if not pdf_files:
        print("No PDF files found in backend/data/pdfs.")
        return

    file_to_upload = pdf_files[0]
    print(f"\n📄 Uploading file: {os.path.basename(file_to_upload)}")
    if not client.upload_file(kb_id, file_to_upload):
        print("Failed to upload file.")
        return

    conversation_id = f"{client.username}_test_conv1"

    print(f"\n💬 Creating conversation '{conversation_id}'...")
    if not client.create_conversation(
        conversation_id=conversation_id,
        conversation_name="Thesis Test Conversation",
        kb_id=kb_id,
    ):
        print("⚠️  Conversation creation failed (might already exist).")

    print("\n🔍 Testing RAG pipeline with thesis knowledge base...")

    test_queries = [
        "What is the main topic of the uploaded document?",
        "Summarize the key findings.",
    ]

    for i, query in enumerate(test_queries):
        print(f"\n{'=' * 60}")
        print(f"Query {i + 1}/{len(test_queries)}")
        response = client.chat_stream(query, conversation_id, kb_id=kb_id)
        if not response:
            print("No response received.")
            break

    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
