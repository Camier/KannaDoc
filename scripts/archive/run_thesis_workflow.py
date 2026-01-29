import requests
import json
import os
import time
import sys

# Configuration
API_BASE = "http://localhost:8090/api/v1"
USERNAME = "thesis"
PASSWORD = os.environ.get("THESIS_PASSWORD")
WORKFLOW_ID = "thesis_253ba4cf-305c-4ae5-b6be-03fe704e243e" # Updated ID V2.3 Mix

if not PASSWORD:
    print("Error: THESIS_PASSWORD must be set.")
    sys.exit(1)

def get_token():
    url = f"{API_BASE}/auth/login"
    data = {"username": USERNAME, "password": PASSWORD}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"Auth failed: {e}")
        sys.exit(1)

def get_workflow(token, workflow_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE}/workflow/workflows/{workflow_id}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching workflow: {response.text}")
        sys.exit(1)
    return response.json()

def execute_workflow(token, workflow_data):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE}/workflow/execute"
    
    # Preset variable for CLI test
    workflow_data["global_variables"]["thesis_topic"] = "Ethnopharmacology of Sceletium tortuosum"
    
    response = requests.post(url, json=workflow_data, headers=headers)
    print(f"DEBUG RESPONSE: {response.text}") 
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Execution failed with status {response.status_code}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        WORKFLOW_ID = sys.argv[1]
        
    token = get_token()
    print(f"Fetching workflow {WORKFLOW_ID}...")
    wf_data = get_workflow(token, WORKFLOW_ID)
    
    print("Launching execution with topic: 'Ethnopharmacology of Sceletium tortuosum'...")
    result = execute_workflow(token, wf_data)
    
    if result and result.get("code") == 0:
        task_id = result.get("task_id")
        print(f"✅ Execution started! Task ID: {task_id}")
    else:
        print("❌ Execution failed (Code != 0)")
        sys.exit(1)
