import os
import sys
import json
import requests
import time

# Configuration
API_BASE = "http://localhost:8090/api"
USERNAME = "miko"
PASSWORD = "lol"  # Credentials from state snapshot
KB_NAME = "Thesis Corpus Optimized"
CORPUS_DIR = "literature/corpus"
COMPLETED_LIST_FILE = "completed_files.json"

def get_token(session):
    url = f"{API_BASE}/auth/login"
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    try:
        response = session.post(url, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"Error logging in: {e}")
        sys.exit(1)

def get_kb_id(session, token):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE}/base/users/{USERNAME}/knowledge_bases"
    response = session.get(url, headers=headers)
    response.raise_for_status()
    kbs = response.json() # Response is directly a list, or list under data? Openapi says array of KB Summary.
    # Openapi: content application/json schema type array items $ref KnowledgeBaseSummary
    # So it returns a list directly.
    for kb in kbs:
        if kb["knowledge_base_name"] == KB_NAME:
            return kb["knowledge_base_id"]
    print(f"Error: KB '{KB_NAME}' not found.")
    sys.exit(1)

def main():
    # 1. Load Completed Files
    if not os.path.exists(COMPLETED_LIST_FILE):
        print("Error: completed_files.json not found")
        sys.exit(1)
    
    with open(COMPLETED_LIST_FILE, 'r') as f:
        completed_filenames = set(json.load(f))
    
    print(f"✅ Loaded {len(completed_filenames)} completed files.")

    # 2. Scan Corpus
    if not os.path.exists(CORPUS_DIR):
        print(f"Error: Corpus directory {CORPUS_DIR} not found")
        sys.exit(1)
        
    all_files = [f for f in os.listdir(CORPUS_DIR) if f.lower().endswith(".pdf")]
    print(f"📂 Found {len(all_files)} files in corpus directory.")

    # 3. Identify Missing
    missing_files = [f for f in all_files if f not in completed_filenames]
    print(f"🚨 Missing {len(missing_files)} files.")
    
    if not missing_files:
        print("🎉 No files to ingest! System is up to date.")
        return

    # 4. Upload
    session = requests.Session()
    print("🔑 Logging in...")
    token = get_token(session)
    
    print("🔍 Resolving KB ID...")
    kb_id = get_kb_id(session, token)
    print(f"   Target KB: {kb_id}")

    upload_url = f"{API_BASE}/base/upload/{kb_id}"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"🚀 Starting ingestion of {len(missing_files)} files...")
    
    success_count = 0
    for i, filename in enumerate(missing_files):
        file_path = os.path.join(CORPUS_DIR, filename)
        print(f"[{i+1}/{len(missing_files)}] Uploading: {filename}...")
        
        try:
            with open(file_path, "rb") as f:
                files_payload = [("files", (filename, f, "application/pdf"))]
                response = session.post(upload_url, headers=headers, files=files_payload)
                
                if response.status_code == 200:
                    print("   ✅ Queued")
                    success_count += 1
                else:
                    print(f"   ❌ Failed: {response.text}")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
        
        # Small sleep to prevent API flooding if needed
        # time.sleep(0.1)

    print(f"\n🎉 Finished. Queued {success_count}/{len(missing_files)} files.")

if __name__ == "__main__":
    main()
