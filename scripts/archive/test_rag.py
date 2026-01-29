import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "miko"
PASSWORD = "lol"

# 1. Login to get token
login_url = f"{BASE_URL}/auth/login"
response = requests.post(login_url, data={"username": USERNAME, "password": PASSWORD})
if response.status_code != 200:
    print(f"Login failed: {response.status_code} - {response.text}")
    exit(1)

token = response.json()["access_token"]
print(f"Token obtained: {token[:20]}...")

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 2. Test chat with RAG
chat_url = f"{BASE_URL}/chat"
payload = {
    "message": "What is Sceletium tortuosum?",
    "stream": False,
    "knowledge_base_id": None,  # Let system choose default
    "model": "local_colqwen"
}

response = requests.post(chat_url, headers=headers, json=payload)
print(f"Chat response status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print("Response:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print(f"Error: {response.text}")

# 3. Try search endpoint (if exists)
search_url = f"{BASE_URL}/search"
search_payload = {
    "query": "Sceletium tortuosum",
    "top_k": 5
}
response = requests.post(search_url, headers=headers, json=search_payload)
print(f"\nSearch response status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print("Search results:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    print(f"Search error: {response.text}")