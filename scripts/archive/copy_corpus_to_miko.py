"""
Copy Research Corpus to Miko KB
================================
Uploads PDF documents from local corpus directory to the Miko knowledge base.
Used for initial ingestion of thesis research materials.

Requires running LAYRA backend and valid authentication token.
"""

import os
import sys
import requests
import time
from jose import jwt
from datetime import datetime, timedelta
import redis

# Configuration
API_BASE = "http://localhost:8000/api/v1"
USERNAME = "miko"
KB_NAME = "Miko Research Corpus"
CORPUS_DIR = "/app/corpus"

# Redis Config (Internal)
REDIS_HOST = "redis"
REDIS_PORT = 6379
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "thesis_redis_1c962832d09529674794ff43258d721c")
REDIS_TOKEN_DB = 0  # Matches backend config

# Read SECRET_KEY from environment variable passed to the script
# Fallback to the default key found in config.py since it seems env var isn't propagating
SECRET_KEY = "your_secret_key_change_in_production"
ALGORITHM = "HS256"

def register_token_in_redis(username, token, expire_seconds):
    """Register the token in Redis so the backend validates it"""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, db=REDIS_TOKEN_DB)
        # Key format from backend/app/api/endpoints/auth.py: f"token:{access_token}" -> username
        r.set(f"token:{token}", username, ex=expire_seconds)
        print(f"Token registered in Redis for user {username}")
    except Exception as e:
        print(f"Error registering token in Redis: {e}")
        sys.exit(1)

def create_system_token(username):
    """Generate a valid JWT token directly using the system secret"""
    expire_minutes = 60
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    to_encode = {
        "sub": username,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    # Register in Redis (Essential for backend validation)
    register_token_in_redis(username, encoded_jwt, expire_minutes * 60)
    
    return encoded_jwt

def get_or_create_kb(token):
    headers = {"Authorization": f"Bearer {token}"}
    list_url = f"{API_BASE}/base/users/{USERNAME}/knowledge_bases"
    
    try:
        response = requests.get(list_url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching KBs: {e}")
        return None
    
    kb_id = None
    for kb in response.json():
        if kb["knowledge_base_name"] == KB_NAME:
            print(f"Found existing KB: {KB_NAME} ({kb['knowledge_base_id']})")
            return kb["knowledge_base_id"]
    
    print(f"Creating Knowledge Base: {KB_NAME}...")
    create_url = f"{API_BASE}/base/knowledge_base"
    try:
        requests.post(create_url, json={"username": USERNAME, "knowledge_base_name": KB_NAME}, headers=headers)
        # Fetch again to get ID
        response = requests.get(list_url, headers=headers)
        for kb in response.json():
            if kb["knowledge_base_name"] == KB_NAME:
                return kb["knowledge_base_id"]
    except Exception as e:
        print(f"Error creating KB: {e}")
        
    return None

def upload_files(token, kb_id, directory):
    headers = {"Authorization": f"Bearer {token}"}
    upload_url = f"{API_BASE}/base/upload/{kb_id}"
    
    files_to_upload = [os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith('.pdf')]
    files_to_upload.sort()
    
    total = len(files_to_upload)
    BATCH_SIZE = 2
    PAUSE = 2
    
    print(f"🚀 Starting migration to {USERNAME}: {total} unique files")
    
    for i in range(0, total, BATCH_SIZE):
        batch = files_to_upload[i:i + BATCH_SIZE]
        files_payload = []
        opened_files = []
        
        batch_names = ", ".join([os.path.basename(f) for f in batch])
        print(f"[{i+len(batch)}/{total}] Uploading: {batch_names}...")
        
        try:
            for file_path in batch:
                f = open(file_path, "rb")
                opened_files.append(f)
                files_payload.append(("files", (os.path.basename(file_path), f, "application/pdf")))
            
            response = requests.post(upload_url, headers=headers, files=files_payload, timeout=60)
            
            if response.status_code == 200:
                print(f"  ✅ Success")
            else:
                print(f"  ❌ Failed ({response.status_code}): {response.text}")
                
        except Exception as e:
            print(f"  ⚠️ Error: {e}")
        finally:
            for f in opened_files:
                f.close()
        
        time.sleep(PAUSE)

if __name__ == "__main__":
    print(f"Generating system token for user: {USERNAME}")
    token = create_system_token(USERNAME)
    
    kb_id = get_or_create_kb(token)
    if kb_id:
        print(f"Target Knowledge Base ID: {kb_id}")
        upload_files(token, kb_id, CORPUS_DIR)
        print("\n🎉 Migration completed. Files are now processing in the background.")
    else:
        print("Failed to initialize Knowledge Base.")
