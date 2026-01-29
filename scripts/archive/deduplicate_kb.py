import os
import sys
import requests
import pymongo
from collections import defaultdict
import datetime

# Configuration for running INSIDE the container
API_BASE = "http://localhost:8000/api/v1"
USERNAME = "thesis"
PASSWORD = os.environ.get("THESIS_PASSWORD")
KB_ID = "thesis_e763055d-f707-42bb-86b4-afb373c5f03a"

# Mongo Config (Internal Docker Service)
MONGO_USER = os.environ.get("MONGODB_ROOT_USERNAME", "root")
MONGO_PASS = os.environ.get("MONGODB_ROOT_PASSWORD", "password")
MONGO_HOST = "mongodb"  # Service name in docker-compose
MONGO_PORT = "27017"

if not PASSWORD:
    print("Error: THESIS_PASSWORD must be set.")
    sys.exit(1)

def get_token():
    url = f"{API_BASE}/auth/login"
    data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"Error logging in: {e}")
        sys.exit(1)

def get_duplicates_from_mongo():
    # Connect to MongoDB
    # Since we are running on host, we need the mapped port.
    # Assuming standard port 27017 is mapped.
    # The user environment says: "docker-compose.thesis.yml"
    # Let's assume the script will be run with access to mongo.
    # Or I can use 'docker exec' to run python inside a container that has access?
    # No, I'll assume I can connect to localhost:27017 if mapped.
    # If not, I'll fail.
    
    # Wait, I don't know the password from here easily without parsing .env again.
    # But I can pass it as env var when running.
    
    client = pymongo.MongoClient(
        f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/"
    )
    db = client["chat_mongodb"]
    kb_collection = db["knowledge_bases"]
    
    kb = kb_collection.find_one({"knowledge_base_id": KB_ID})
    if not kb:
        print(f"KB {KB_ID} not found in MongoDB.")
        return {}
    
    files = kb.get("files", [])
    print(f"Total files in KB (raw Mongo): {len(files)}")
    
    # Group by filename
    grouped = defaultdict(list)
    for f in files:
        filename = f.get("filename")
        if filename:
            grouped[filename].append(f)
            
    duplicates = {}
    for filename, file_list in grouped.items():
        if len(file_list) > 1:
            # Sort by created_at descending (latest first)
            # created_at might be datetime or string. Mongo driver usually returns datetime.
            try:
                file_list.sort(key=lambda x: x.get("created_at", datetime.datetime.min), reverse=True)
            except Exception as e:
                print(f"Error sorting files for {filename}: {e}")
                # Fallback: keep the one appearing last in list (usually latest appended)
                file_list.reverse() 
                
            duplicates[filename] = file_list
            
    return duplicates

def delete_duplicates(token, duplicates):
    delete_list = []
    
    print(f"Found duplicates for {len(duplicates)} files.")
    
    for filename, file_list in duplicates.items():
        keep = file_list[0]
        remove = file_list[1:]
        print(f"File: {filename}")
        print(f"  Keep: {keep.get('file_id')} ({keep.get('created_at')})")
        for f in remove:
            print(f"  Remove: {f.get('file_id')} ({f.get('created_at')})")
            delete_list.append({
                "knowledge_id": KB_ID,
                "file_id": f.get("file_id")
            })
            
    if not delete_list:
        print("No files to delete.")
        return

    print(f"\nDeleting {len(delete_list)} duplicate files...")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE}/base/files/bulk-delete"
    
    # Batch requests if too large? 
    # API bulk delete processes items.
    
    try:
        response = requests.delete(url, json=delete_list, headers=headers)
        if response.status_code == 200:
            print("✅ Bulk delete successful.")
            print(response.json())
        else:
            print(f"❌ Error deleting files: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error sending delete request: {e}")

if __name__ == "__main__":
    token = get_token()
    duplicates = get_duplicates_from_mongo()
    if duplicates:
        delete_duplicates(token, duplicates)
    else:
        print("No duplicates found.")
