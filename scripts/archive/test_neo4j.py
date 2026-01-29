import requests
import json

# Neo4j configuration
NEO4J_URL = "http://localhost:7474"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j"

# Session authentication
auth = (NEO4J_USER, NEO4J_PASSWORD)
headers = {"Content-Type": "application/json", "Accept": "application/json"}

# Start a transaction (or use simple endpoint)
# Get database info
try:
    response = requests.get(f"{NEO4J_URL}/db/neo4j", auth=auth, headers=headers)
    print(f"Database info: {response.status_code}")
    if response.status_code == 200:
        print(response.json())
except Exception as e:
    print(f"Error: {e}")

# Run a simple query to count nodes
query = {"statements": [{"statement": "MATCH (n) RETURN count(n) AS node_count"}]}
try:
    response = requests.post(
        f"{NEO4J_URL}/db/neo4j/tx/commit",
        auth=auth,
        headers=headers,
        json=query
    )
    if response.status_code == 200:
        data = response.json()
        print(f"Query result: {json.dumps(data, indent=2)}")
    else:
        print(f"Query failed: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Query error: {e}")

# List node labels
query = {"statements": [{"statement": "CALL db.labels() YIELD label RETURN label"}]}
try:
    response = requests.post(
        f"{NEO4J_URL}/db/neo4j/tx/commit",
        auth=auth,
        headers=headers,
        json=query
    )
    if response.status_code == 200:
        data = response.json()
        print(f"Labels: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"Labels error: {e}")