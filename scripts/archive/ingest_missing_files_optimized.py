import os
import sys
import requests
import time

# Configuration
API_BASE = os.environ.get("LAYRA_API_BASE", "http://localhost:8090/api")
USERNAME = os.environ.get("THESIS_USERNAME", "thesis")
PASSWORD = os.environ.get("THESIS_PASSWORD")
KB_ID = os.environ.get("KB_ID", "thesis_e763055d-f707-42bb-86b4-afb373c5f03a")
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

def get_existing_files(session, token, kb_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE}/base/knowledge_bases/{kb_id}/files"
    
    existing_files = set()
    page = 1
    page_size = 100
    
    print("Fetching existing files from Knowledge Base...")
    
    while True:
        try:
            payload = {
                "page": page,
                "page_size": page_size,
                "keyword": ""
            }
            response = session.post(
                url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            if not items:
                break
                
            for item in items:
                # The API returns 'file_name' or similar, let's verify if needed. 
                # Usually it's 'file_name' or 'filename'
                filename = item.get("file_name") or item.get("filename")
                if filename:
                    existing_files.add(filename)
            
            if page >= data.get("pages", 1):
                break
                
            page += 1
            
        except Exception as e:
            print(f"Error fetching files page {page}: {e}")
            break
            
    print(f"Found {len(existing_files)} existing files in KB.")
    return existing_files

def upload_files(session, token, kb_id, directory, existing_files):
    headers = {"Authorization": f"Bearer {token}"}
    upload_url = f"{API_BASE}/base/upload/{kb_id}"
    
    # STRICTLY PDF ONLY
    all_pdfs = [
        f
        for f in os.listdir(directory)
        if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(directory, f))
    ]
    files_to_upload = [os.path.join(directory, f) for f in all_pdfs if f not in existing_files]
    files_to_upload.sort()
    
    total = len(files_to_upload)
    skipped = len(all_pdfs) - total
    
    if total == 0:
        print(f"🎉 No new files to upload. {skipped} files already exist.")
        return

    print(f"🚀 OPTIMIZED INGESTION: Found {total} new files to upload (Skipped {skipped}).")
    print(f"   Processing in batches of {BATCH_SIZE} with {PAUSE}s pause...")
    
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
                    upload_url, headers=headers, files=files_payload, timeout=REQUEST_TIMEOUT
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
    existing_files = get_existing_files(session, token, KB_ID)
    upload_files(session, token, KB_ID, CORPUS_DIR, existing_files)
    print("\n🎉 Bulk ingestion process completed.")
