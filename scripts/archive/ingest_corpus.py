import os
import sys
import requests
import time

# Configuration
API_BASE = os.environ.get("LAYRA_API_BASE", "http://localhost:8090/api")
USERNAME = os.environ.get("THESIS_USERNAME", "miko")
PASSWORD = os.environ.get("THESIS_PASSWORD", "lol")
KB_NAME = os.environ.get("KB_NAME", "Thesis Corpus Optimized")
CORPUS_DIR = os.environ.get("CORPUS_DIR", "/LAB/@thesis/layra/literature/corpus")
REQUEST_TIMEOUT = int(os.environ.get("INGEST_HTTP_TIMEOUT", "60"))
BATCH_SIZE = int(os.environ.get("INGEST_BATCH_SIZE", "2"))
PAUSE = float(os.environ.get("INGEST_BATCH_PAUSE", "2"))
MAX_RETRIES = int(os.environ.get("INGEST_HTTP_RETRIES", "1"))

if not PASSWORD:
    print("Error: THESIS_PASSWORD must be set.")
    sys.exit(1)
if not os.path.isdir(CORPUS_DIR):
    print(f"Error: CORPUS_DIR not found or not a directory: {CORPUS_DIR}")
    sys.exit(1)

def get_token(session):
    url = f"{API_BASE}/auth/login"
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    try:
        response = session.post(url, data=data, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"Error logging in: {e}")
        sys.exit(1)

def get_or_create_kb(session, token):
    headers = {"Authorization": f"Bearer {token}"}
    list_url = f"{API_BASE}/base/users/{USERNAME}/knowledge_bases"
    response = session.get(list_url, headers=headers, timeout=REQUEST_TIMEOUT)
    
    kb_id = None
    if response.status_code == 200:
        for kb in response.json():
            if kb["knowledge_base_name"] == KB_NAME:
                return kb["knowledge_base_id"]
    
    print(f"Creating Knowledge Base: {KB_NAME}...")
    create_url = f"{API_BASE}/base/knowledge_base"
    session.post(
        create_url,
        json={"username": USERNAME, "knowledge_base_name": KB_NAME},
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )

    response = session.get(list_url, headers=headers, timeout=REQUEST_TIMEOUT)
    for kb in response.json():
        if kb["knowledge_base_name"] == KB_NAME:
            return kb["knowledge_base_id"]
    return None

def upload_files(session, token, kb_id, directory):
    headers = {"Authorization": f"Bearer {token}"}
    upload_url = f"{API_BASE}/base/upload/{kb_id}"
    
    # STRICTLY PDF ONLY
    files_to_upload = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(directory, f))
    ]
    files_to_upload.sort()
    
    total = len(files_to_upload)
    
    print(f"🚀 OPTIMIZED INGESTION: {total} PDFs in batches of {BATCH_SIZE}")
    
    for i in range(0, total, BATCH_SIZE):
        batch = files_to_upload[i:i + BATCH_SIZE]
        files_payload = []
        opened_files = []
        
        batch_names = ", ".join([os.path.basename(f) for f in batch])
        print(f"[{i+len(batch)}/{total}] Batch: {batch_names}...")
        
        try:
            for file_path in batch:
                f = open(file_path, "rb")
                opened_files.append(f)
                files_payload.append(("files", (os.path.basename(file_path), f, "application/pdf")))
            
            response = None
            for attempt in range(1, MAX_RETRIES + 1):
                response = session.post(
                    upload_url,
                    headers=headers,
                    files=files_payload,
                    timeout=REQUEST_TIMEOUT,
                )
                if response.status_code == 200:
                    print("  ✅ Batch sent.")
                    break
                if attempt == MAX_RETRIES:
                    print(f"  ❌ ERROR {response.status_code}: {response.text}")
                    sys.exit(1)
                time.sleep(PAUSE)
                
        except Exception as e:
            print(f"  ⚠️ CONNECTION ERROR: {e}")
            sys.exit(1)
        finally:
            for f in opened_files:
                f.close()
        
        time.sleep(PAUSE)

if __name__ == "__main__":
    session = requests.Session()
    token = get_token(session)
    kb_id = get_or_create_kb(session, token)
    if kb_id:
        upload_files(session, token, kb_id, CORPUS_DIR)
        print("\n🎉 All batches submitted. GPU is now processing...")
