import requests
import sys
import os
import json
import time

API_BASE = "http://localhost:8090/api/v1"
USERNAME = "miko"
PASSWORD = os.environ.get("THESIS_PASSWORD", "lol")

if not PASSWORD:
    print("Warning: THESIS_PASSWORD not set, using default 'lol'")
    PASSWORD = 'lol'

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

def check_status(token, task_id):
    import subprocess
    redis_pwd = "thesis_redis_1c962832d09529674794ff43258d721c"
    # Suppress stderr to avoid the password warning in the output
    cmd = f"docker exec layra-redis redis-cli -a {redis_pwd} -n 1 HGETALL workflow:{task_id} 2>/dev/null"
    try:
        result = subprocess.check_output(cmd, shell=True).decode()
        if not result:
            return None
        
        lines = [l.strip() for l in result.strip().split('\n') if l.strip()]
        data = {}
        for i in range(0, len(lines), 2):
            if i+1 < len(lines):
                data[lines[i]] = lines[i+1]
        
        if not data:
            # Try to see if it exists at all
            exists = subprocess.check_output(f"docker exec layra-redis redis-cli -a {redis_pwd} -n 1 EXISTS workflow:{task_id} 2>/dev/null", shell=True).decode().strip()
            if exists == "0":
                return None
            return {"status": "exists_but_empty"}
            
        return data
    except Exception as e:
        print(f"Redis check failed: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_task_status.py <task_id>")
        sys.exit(1)
        
    task_id = sys.argv[1]
    token = get_token()
    
    print(f"Checking status for task {task_id}...")
    
    while True:
        status = check_status(token, task_id)
        if status:
            state = status.get("status", "unknown")
            print(f"Status: {state}")
            
            if state == "completed" or state == "failed" or state == "error":
                print("Final Result:")
                print(json.dumps(status, indent=2))
                break
        else:
            print("Task not found in Redis (expired or invalid ID).")
            break
            
        time.sleep(5)
