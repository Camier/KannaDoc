import requests
import sys

API_URL = "http://localhost:8090/api/auth/register"
USER_DATA = {
    "username": "miko",
    "email": "miko@thesis.com",
    "password": "lol"
}

try:
    print(f"Registering user 'miko' at {API_URL}...")
    response = requests.post(API_URL, json=USER_DATA)
    
    if response.status_code == 200:
        print("✅ User 'miko' registered successfully!")
        print(f"   Username: {USER_DATA['username']}")
        print(f"   Password: {USER_DATA['password']}")
    elif response.status_code == 400 and "already registered" in response.text:
        print("⚠️ User 'miko' already exists.")
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(response.text)
        sys.exit(1)

except Exception as e:
    print(f"❌ Connection error: {e}")
    sys.exit(1)
