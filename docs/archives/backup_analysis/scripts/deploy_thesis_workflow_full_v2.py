import requests
import uuid
import json
import os

# Configuration
API_BASE = "http://localhost:8090/api/v1"
USERNAME = "thesis"
PASSWORD = os.environ.get("THESIS_PASSWORD")
KB_ID = "thesis_e763055d-f707-42bb-86b4-afb373c5f03a"
WORKFLOW_DIR = "/LAB/@thesis/layra/workflows/thesis_blueprint_minutieux"

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

def load_file(path):
    with open(path, "r") as f:
        return f.read()

def create_workflow(token):
    headers = {"Authorization": f"Bearer {token}"}
    workflow_id = f"{USERNAME}_{uuid.uuid4()}"
    
    # --- Load Artefacts ---
    # Prompts
    p_reqs = load_file(f"{WORKFLOW_DIR}/prompts/1_requirements_builder.txt")
    p_seed = load_file(f"{WORKFLOW_DIR}/prompts/2_seed_axes_and_queries.txt")
    p_rag = load_file(f"{WORKFLOW_DIR}/prompts/3_kb_retrieve_extract_axis_map.txt")
    p_macro = load_file(f"{WORKFLOW_DIR}/prompts/4_macro_outline_generator.txt")
    p_micro = load_file(f"{WORKFLOW_DIR}/prompts/5_micro_outline_for_chapter.txt")
    p_source = load_file(f"{WORKFLOW_DIR}/prompts/6_retrieve_sources_for_subsection.txt")
    p_coherence = load_file(f"{WORKFLOW_DIR}/prompts/7_coherence_and_narrative_check.txt")
    p_human = load_file(f"{WORKFLOW_DIR}/prompts/8_human_review_gate.txt")
    
    # Code
    c_parse = load_file(f"{WORKFLOW_DIR}/code_nodes/parse_seed_axes_json.py")
    c_accumulate = load_file(f"{WORKFLOW_DIR}/code_nodes/accumulate_kb_map.py")
    c_normalize = load_file(f"{WORKFLOW_DIR}/code_nodes/normalize_and_dedup_kb_map.py")
    c_coverage = load_file(f"{WORKFLOW_DIR}/code_nodes/coverage_scoring.py")
    c_export = load_file(f"{WORKFLOW_DIR}/code_nodes/export_toc_md_latex.py")
    
    # Helper for loop indexing
    c_init_loop = "loop_idx = 0\nreturn {'loop_idx': 0}"
    c_next_item = """
idx = inputs.get('loop_idx', 0)
axes = inputs.get('seed_axes', [])
if idx < len(axes):
    return {'current_axis': axes[idx], 'current_axis_json': json.dumps(axes[idx])}
return {}
"""
    c_inc_loop = """
idx = inputs.get('loop_idx', 0)
return {'loop_idx': idx + 1}
"""

    nodes = [
        # 1. Start
        {"id": "n_start", "type": "start", "data": {"name": "Start"}, "position": {"x": 0, "y": 0}},
        
        # 2. Input
        {"id": "n_input", "type": "llm", "data": {"name": "Input", "modelConfig": {"model_name": "gpt-4o", "system_prompt": "Topic?", "set_chatflow_user_input": True, "output_variable": "thesis_topic"}}, "position": {"x": 300, "y": 0}},
        
        # 3. Requirements
        {"id": "n_reqs", "type": "llm", "data": {"name": "Requirements", "modelConfig": {"model_name": "gpt-4o", "system_prompt": p_reqs, "output_variable": "requirements"}}, "position": {"x": 600, "y": 0}},
        
        # 4. Seed Axes
        {"id": "n_seed", "type": "llm", "data": {"name": "Seed Axes", "modelConfig": {"model_name": "gpt-4o", "system_prompt": p_seed, "output_variable": "seed_axes_json"}}, "position": {"x": 900, "y": 0}},
        
        # 5. Parse Seeds
        {"id": "n_parse", "type": "code", "data": {"name": "Parse Seeds", "code": c_parse}, "position": {"x": 1200, "y": 0}},
        
        # 6. Init Loop
        {"id": "n_loop_init", "type": "code", "data": {"name": "Init Loop", "code": c_init_loop}, "position": {"x": 1500, "y": 0}},
        
        # 7. Loop Node
        {"id": "n_loop", "type": "loop", "data": {"name": "Mapping Loop", "loopType": "condition", "condition": "loop_idx < axes_count"}, "position": {"x": 1800, "y": 0}},
        
        # --- Inside Loop ---
        # 7.1 Get Item
        {"id": "n_get_item", "type": "code", "data": {"name": "Get Axis", "code": c_next_item}, "position": {"x": 1800, "y": 300}},
        
        # 7.2 RAG Extraction
        {"id": "n_rag", "type": "llm", "data": {"name": "KB Extract", "modelConfig": {"model_name": "gpt-4o", "system_prompt": p_rag, "knowledge_base_id": KB_ID, "rag_use": True, "top_k": 10, "output_variable": "current_axis_result"}}, "position": {"x": 2100, "y": 300}},
        
        # 7.3 Accumulate
        {"id": "n_acc", "type": "code", "data": {"name": "Accumulate", "code": c_accumulate}, "position": {"x": 2400, "y": 300}},
        
        # 7.4 Increment
        {"id": "n_inc", "type": "code", "data": {"name": "Increment", "code": c_inc_loop}, "position": {"x": 2700, "y": 300}}
        # -------------------
        
        # 8. Normalize
        {"id": "n_norm", "type": "code", "data": {"name": "Normalize", "code": c_normalize}, "position": {"x": 2100, "y": 0}},
        
        # 9. Macro Outline
        {"id": "n_macro", "type": "llm", "data": {"name": "Macro Outline", "modelConfig": {"model_name": "gpt-4o", "system_prompt": p_macro, "output_variable": "macro_outline"}}, "position": {"x": 2400, "y": 0}},
        
        # 10. Export (Simplified end for V2 to ensure stability before Micro loops)
        {"id": "n_export", "type": "code", "data": {"name": "Export", "code": c_export}, "position": {"x": 2700, "y": 0}},
        
        # 11. Display
        {"id": "n_display", "type": "llm", "data": {"name": "Display", "modelConfig": {"model_name": "gpt-4o", "system_prompt": "Done.\n{{exports}}", "set_chatflow_ai_response": True}}, "position": {"x": 3000, "y": 0}}
    ]
    
    edges = [
        {"source": "n_start", "target": "n_input"},
        {"source": "n_input", "target": "n_reqs"},
        {"source": "n_reqs", "target": "n_seed"},
        {"source": "n_seed", "target": "n_parse"},
        {"source": "n_parse", "target": "n_loop_init"},
        {"source": "n_loop_init", "target": "n_loop"},
        
        # Loop Edges
        {"source": "n_loop", "sourceHandle": "loop_body", "target": "n_get_item"},
        {"source": "n_get_item", "target": "n_rag"},
        {"source": "n_rag", "target": "n_acc"},
        {"source": "n_acc", "target": "n_inc"},
        {"source": "n_inc", "target": "n_loop"}, # Closing the loop
        
        # Exit Loop
        {"source": "n_loop", "sourceHandle": "loop_next", "target": "n_norm"},
        {"source": "n_norm", "target": "n_macro"},
        {"source": "n_macro", "target": "n_export"},
        {"source": "n_export", "target": "n_display"}
    ]
    
    global_vars = {
        "thesis_topic": "",
        "requirements": {},
        "seed_axes_json": {},
        "seed_axes": [],
        "axes_count": 0,
        "loop_idx": 0,
        "kb_map": {},
        "macro_outline": {},
        "micro_outline": {}, # Placeholder
        "exports": {}
    }
    
    payload = {
        "username": USERNAME,
        "workflow_id": workflow_id,
        "workflow_name": "Thesis Blueprint (Minutieux V2 - Looped)",
        "workflow_config": {},
        "start_node": "n_start",
        "global_variables": global_vars,
        "nodes": nodes,
        "edges": edges
    }
    
    print(f"Deploying workflow with {len(nodes)} nodes...")
    response = requests.post(f"{API_BASE}/workflow/workflows", json=payload, headers=headers)
    if response.status_code == 200:
        print(f"✅ Workflow deployed! ID: {workflow_id}")
    else:
        print(f"❌ Failed: {response.text}")

if __name__ == "__main__":
    token = get_token()
    create_workflow(token)
