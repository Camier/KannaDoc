import requests
import uuid
import json
import os

# Configuration
API_BASE = "http://localhost:8090/api/v1"
USERNAME = "thesis"
PASSWORD = os.environ.get("THESIS_PASSWORD")
KB_ID = "thesis_e763055d-f707-42bb-86b4-afb373c5f03a"

if not PASSWORD:
    raise SystemExit("Error: THESIS_PASSWORD must be set.")

def get_token():
    url = f"{API_BASE}/auth/login"
    data = {"username": USERNAME, "password": PASSWORD}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"Auth failed: {e}")
        exit(1)

def create_workflow(token):
    headers = {"Authorization": f"Bearer {token}"}
    
    workflow_id = f"{USERNAME}_{uuid.uuid4()}"
    
    # Node IDs
    id_start = "node_start"
    id_input = "node_user_input"
    id_expander = "node_query_expander" # NEW
    id_prep = "node_prep_search"
    id_research = "node_researcher"
    id_plan = "node_planner"
    
    # Global Variables
    global_vars = {
        "topic": "Mesembrine alkaloids",
        "expanded_topic": "",
        "search_query": "",
        "key_findings": "",
        "thesis_plan": ""
    }
    
    nodes = [
        {
            "id": id_start,
            "type": "start",
            "data": {"name": "Start"},
            "position": {"x": 100, "y": 200}
        },
        {
            "id": id_input,
            "type": "llm",
            "data": {
                "name": "User Topic Input",
                "modelConfig": {
                    "model_name": "gpt-4o",
                    "temperature": 0.7,
                    "system_prompt": "You are a research assistant. Ask the user for the thesis topic or research question.",
                    "input_type": "chat", 
                    "set_chatflow_user_input": True,
                    "output_variable": "topic"
                }
            },
            "position": {"x": 400, "y": 200}
        },
        {
            # NEW NODE: Query Expander
            "id": id_expander,
            "type": "llm",
            "data": {
                "name": "Query Expander",
                "modelConfig": {
                    "model_name": "gpt-4o",
                    "temperature": 0.4,
                    "system_prompt": """You are a scientific librarian.
Your task is to expand the user's research topic into a precise academic search query.
1. Identify scientific synonyms (e.g., 'Kanna' -> 'Sceletium tortuosum').
2. Add relevant pharmacological or botanical terms if applicable.
3. Keep it concise but comprehensive.

User Topic: {{topic}}

Output ONLY the expanded keywords string.""",
                    "output_variable": "expanded_topic"
                }
            },
            "position": {"x": 700, "y": 200}
        },
        {
            "id": id_prep,
            "type": "code",
            "data": {
                "name": "Format Search Query",
                "code": "search_query = f\"Query: {expanded_topic} comprehensive review\""
            },
            "position": {"x": 1000, "y": 200}
        },
        {
            "id": id_research,
            "type": "llm",
            "data": {
                "name": "Deep Researcher (RAG)",
                "modelConfig": {
                    "model_name": "gpt-4o",
                    "temperature": 0.2,
                    "system_prompt": """You are an expert academic researcher. 
Analyze the provided documents regarding '{{expanded_topic}}'.
Extract the following:
1. Key Methodologies used in the field.
2. Major Findings and Consensus.
3. Contradictions or Gaps in current literature.
4. Key References (Author, Year).

Output concise bullet points.""",
                    "knowledge_base_id": KB_ID,
                    "rag_use": True,
                    "top_k": 15, # Increased for better recall
                    "score_threshold": 0.35,
                    "output_variable": "key_findings"
                }
            },
            "position": {"x": 1300, "y": 200}
        },
        {
            "id": id_plan,
            "type": "llm",
            "data": {
                "name": "Thesis Planner",
                "modelConfig": {
                    "model_name": "gpt-4o",
                    "temperature": 0.7,
                    "system_prompt": """You are a senior thesis supervisor.
Based on the research findings below, propose a structured outline for a thesis or review paper on '{{topic}}'.
Follow the IMRAD structure or a standard review format.

Research Findings:
{{key_findings}}

Output the plan in Markdown format.""",
                    "set_chatflow_ai_response": True
                }
            },
            "position": {"x": 1600, "y": 200}
        }
    ]
    
    edges = [
        {"source": id_start, "target": id_input},
        {"source": id_input, "target": id_expander},
        {"source": id_expander, "target": id_prep},
        {"source": id_prep, "target": id_research},
        {"source": id_research, "target": id_plan}
    ]
    
    payload = {
        "username": USERNAME,
        "workflow_id": workflow_id,
        "workflow_name": "Thesis Planner V2 (Expanded)",
        "workflow_config": {},
        "start_node": id_start,
        "global_variables": global_vars,
        "nodes": nodes,
        "edges": edges
    }
    
    response = requests.post(f"{API_BASE}/workflow/workflows", json=payload, headers=headers)
    if response.status_code == 200:
        print(f"✅ Workflow created successfully! ID: {workflow_id}")
    else:
        print(f"❌ Failed to create workflow: {response.text}")

if __name__ == "__main__":
    token = get_token()
    create_workflow(token)
