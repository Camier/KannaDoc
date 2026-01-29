#!/usr/bin/env python3
import requests
import json
import sys

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlcjIyOTEiLCJleHAiOjE3NzAxMDAwMTd9.V4KJZbgf8cuKAVPDWWuGJw_kyXrQs39wMlpZ3kngAiw"
url = "http://localhost:8090/api/v1/sse/chat"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {
    "conversation_id": "testuser2291_thesis_test",
    "parent_id": "0",
    "user_message": "What is Sceletium tortuosum?",
    "temp_db": "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1",
}

print("Sending request...")
response = requests.post(url, json=payload, headers=headers, stream=True)
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")

if response.status_code == 200:
    for line in response.iter_lines():
        if line:
            line = line.decode("utf-8")
            print(f"RAW: {line}")
            if line.startswith("data:"):
                data = line[5:].strip()
                if data:
                    try:
                        parsed = json.loads(data)
                        print(f"DATA: {parsed}")
                    except:
                        print(f"JSON error: {data}")
else:
    print(f"Error: {response.text}")
