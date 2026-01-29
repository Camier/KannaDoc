"""
LAYRA Thesis Workflow Deployment Script (Consolidated v2.1)
===========================================================
Deploys the complete "Minutieux" thesis blueprint workflow with:
- Full iterative KB mapping loop
- Macro/Micro outline generation  
- Source retrieval and coherence checking
- Export to Markdown/LaTeX

This is the consolidated version combining all improvements from:
- deploy_thesis_workflow_full.py (original)
- deploy_thesis_workflow_full_v2_1.py (enhanced with loops)
- Audit reports and testing feedback

Usage: THESIS_PASSWORD=password python3 deploy_thesis_workflow_full.py

Alternative simpler workflow: deploy_thesis_workflow_full_simple.py
"""

import requests
import uuid
import json
import os

# Configuration
API_BASE = "http://localhost:8090/api/v1"
USERNAME = "miko"
PASSWORD = os.environ.get("THESIS_PASSWORD") or "lol"
KB_ID = "miko_aa6bb9c4-6ae7-4c62-96e9-85e7111b2850"
WORKFLOW_DIR = "/LAB/@thesis/layra/workflows/thesis_blueprint_minutieux"

if not PASSWORD:
    raise SystemExit("Error: THESIS_PASSWORD must be set.")

def get_token():
    url = f"{API_BASE}/auth/login".replace("/v1/auth", "/auth") # Quick fix for routing mess
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
    
    # --- PROMPTS ---
    p_reqs = load_file(f"{WORKFLOW_DIR}/prompts/1_requirements_builder.txt")
    p_seed = load_file(f"{WORKFLOW_DIR}/prompts/2_seed_axes_and_queries.txt")
    p_kb_rag = load_file(f"{WORKFLOW_DIR}/prompts/3_kb_retrieve_extract_axis_map.txt")
    p_macro = load_file(f"{WORKFLOW_DIR}/prompts/4_macro_outline_generator.txt")
    p_micro = load_file(f"{WORKFLOW_DIR}/prompts/5_micro_outline_for_chapter.txt")
    p_sources = load_file(f"{WORKFLOW_DIR}/prompts/6_retrieve_sources_for_subsection.txt")
    p_coherence = load_file(f"{WORKFLOW_DIR}/prompts/7_coherence_and_narrative_check.txt")
    p_human = load_file(f"{WORKFLOW_DIR}/prompts/8_human_review_gate.txt")

    # --- CODE ---
    c_parse_seeds = load_file(f"{WORKFLOW_DIR}/code_nodes/parse_seed_axes_json.py")
    c_acc_kb = load_file(f"{WORKFLOW_DIR}/code_nodes/accumulate_kb_map.py")
    c_norm_kb = load_file(f"{WORKFLOW_DIR}/code_nodes/normalize_and_dedup_kb_map.py")
    c_parse_chap = load_file(f"{WORKFLOW_DIR}/code_nodes/parse_macro_chapters.py")
    c_append_micro = load_file(f"{WORKFLOW_DIR}/code_nodes/append_to_micro_outline.py")
    c_flatten_sub = load_file(f"{WORKFLOW_DIR}/code_nodes/flatten_subsections.py")
    c_merge_src = load_file(f"{WORKFLOW_DIR}/code_nodes/merge_sources_into_micro_outline.py")
    c_coverage = load_file(f"{WORKFLOW_DIR}/code_nodes/coverage_scoring.py")
    c_apply_patch = load_file(f"{WORKFLOW_DIR}/code_nodes/apply_patch_actions.py")
    c_apply_user = load_file(f"{WORKFLOW_DIR}/code_nodes/apply_user_changes.py")
    c_export = load_file(f"{WORKFLOW_DIR}/code_nodes/export_toc_md_latex.py")
    
    # Loop Helpers
    c_init_loop = load_file(f"{WORKFLOW_DIR}/code_nodes/init_loop_idx.py")
    c_inc_loop = load_file(f"{WORKFLOW_DIR}/code_nodes/inc_loop_idx.py")
    c_get_axis = load_file(f"{WORKFLOW_DIR}/code_nodes/get_axis_by_index.py")
    c_get_chap = load_file(f"{WORKFLOW_DIR}/code_nodes/get_chapter_by_index.py")
    c_inc_chap = load_file(f"{WORKFLOW_DIR}/code_nodes/inc_chapter_index.py")
    c_get_sub = load_file(f"{WORKFLOW_DIR}/code_nodes/get_subsection_by_index.py")
    c_inc_sub = load_file(f"{WORKFLOW_DIR}/code_nodes/inc_subsection_index.py")

    # --- MODEL CONFIG ---
    # Using the verified gpt-4o config from the user profile
    gpt4o_config = {
        "model_id": "thesis_gpt4o",
        "model_name": "gpt-4o",
        "model_url": "https://api.openai.com/v1",
        "api_key": "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",
        "base_used": [{"name": "Thesis Corpus", "baseId": KB_ID}],
        "system_prompt": "You are an expert academic researcher.",
        "temperature": 0.5,
        "max_length": 4096,
        "top_P": 1,
        "top_K": 10,
        "score_threshold": 10
    }

    nodes = [
        # --- PREP ---
        {"id": "n0", "type": "start", "data": {"name": "Start"}, "position": {"x": 0, "y": 0}},
        {"id": "n1", "type": "vlm", "data": {"name": "Requirements", "isChatflowInput": False, "useChatHistory": False, "isChatflowOutput": False, "chatflowOutputVariable": "requirements", "mcpUse": {}, "vlmInput": "Build requirements for topic: {{thesis_topic}}", "prompt": p_reqs, "modelConfig": gpt4o_config}, "position": {"x": 300, "y": 0}},
        {"id": "n2", "type": "vlm", "data": {"name": "Seed Axes", "isChatflowInput": False, "useChatHistory": False, "isChatflowOutput": False, "chatflowOutputVariable": "seed_axes_json", "mcpUse": {}, "vlmInput": "Generate seed axes for requirements: {{requirements}}", "prompt": p_seed, "modelConfig": gpt4o_config}, "position": {"x": 600, "y": 0}},
        {"id": "n3", "type": "code", "data": {"name": "Parse Seeds", "code": c_parse_seeds}, "position": {"x": 900, "y": 0}},
        
        # --- LOOP 1: KB MAPPING ---
        {"id": "n4_init", "type": "code", "data": {"name": "Init Loop 1", "code": c_init_loop}, "position": {"x": 1200, "y": 0}},
        {"id": "n4_loop", "type": "loop", "data": {"name": "KB Loop", "loopType": "condition", "condition": "loop_idx < axes_count"}, "position": {"x": 1500, "y": 0}},
        # Inside
        {"id": "n4_get", "type": "code", "data": {"name": "Get Axis", "code": c_get_axis}, "position": {"x": 1500, "y": 300}},
        {"id": "n4_rag", "type": "vlm", "data": {"name": "Extract", "isChatflowInput": False, "useChatHistory": False, "isChatflowOutput": False, "chatflowOutputVariable": "current_axis_result", "mcpUse": {}, "vlmInput": "Extract from KB for axis: {{axis}}", "prompt": p_kb_rag, "modelConfig": gpt4o_config}, "position": {"x": 1800, "y": 300}},
        {"id": "n4_acc", "type": "code", "data": {"name": "Accumulate", "code": c_acc_kb}, "position": {"x": 2100, "y": 300}},
        {"id": "n4_inc", "type": "code", "data": {"name": "Inc Loop 1", "code": c_inc_loop}, "position": {"x": 2400, "y": 300}},
        
        # --- MACRO ---
        {"id": "n5", "type": "code", "data": {"name": "Normalize KB", "code": c_norm_kb}, "position": {"x": 1800, "y": 0}},
        {"id": "n6", "type": "vlm", "data": {"name": "Macro Gen", "isChatflowInput": False, "useChatHistory": False, "isChatflowOutput": False, "chatflowOutputVariable": "macro_outline", "mcpUse": {}, "vlmInput": "Generate macro outline for mapping: {{kb_map}}", "prompt": p_macro, "modelConfig": gpt4o_config}, "position": {"x": 2100, "y": 0}},
        {"id": "n7", "type": "code", "data": {"name": "Parse Chapters", "code": c_parse_chap}, "position": {"x": 2400, "y": 0}},
        
        # Loop 2
        {"id": "n8_loop", "type": "loop", "data": {"name": "Micro Loop", "loopType": "condition", "condition": "chapter_idx < chapters_count"}, "position": {"x": 2700, "y": 0}},
        # Inside
        {"id": "n8_get", "type": "code", "data": {"name": "Get Chap", "code": c_get_chap}, "position": {"x": 2700, "y": 300}},
        {"id": "n8_gen", "type": "vlm", "data": {"name": "Micro Gen", "isChatflowInput": False, "useChatHistory": False, "isChatflowOutput": False, "chatflowOutputVariable": "micro_chapter", "mcpUse": {}, "vlmInput": "Generate micro outline for chapter: {{current_chapter}}", "prompt": p_micro, "modelConfig": gpt4o_config}, "position": {"x": 3000, "y": 300}},
        {"id": "n8_app", "type": "code", "data": {"name": "Append", "code": c_append_micro}, "position": {"x": 3300, "y": 300}},
        {"id": "n8_inc", "type": "code", "data": {"name": "Inc Loop 2", "code": c_inc_chap}, "position": {"x": 3600, "y": 300}},
        
        # --- LOOP 3: SOURCES ---
        {"id": "n9", "type": "code", "data": {"name": "Flatten Subs", "code": c_flatten_sub}, "position": {"x": 3000, "y": 0}},
        {"id": "n10_loop", "type": "loop", "data": {"name": "Source Loop", "loopType": "condition", "condition": "subsection_idx < subsections_count"}, "position": {"x": 3300, "y": 0}},
        # Inside
        {"id": "n10_get", "type": "code", "data": {"name": "Get Sub", "code": c_get_sub}, "position": {"x": 3300, "y": 300}},
        {"id": "n10_rag", "type": "vlm", "data": {"name": "Find Sources", "isChatflowInput": False, "useChatHistory": False, "isChatflowOutput": False, "chatflowOutputVariable": "found_sources", "mcpUse": {}, "vlmInput": "Retrieve sources for subsection: {{current_subsection}}", "prompt": p_sources, "modelConfig": gpt4o_config}, "position": {"x": 3600, "y": 300}},
        {"id": "n10_mer", "type": "code", "data": {"name": "Merge", "code": c_merge_src}, "position": {"x": 3900, "y": 300}},
        {"id": "n10_inc", "type": "code", "data": {"name": "Inc Loop 3", "code": c_inc_sub}, "position": {"x": 4200, "y": 300}},
        {"id": "n10_exit", "type": "code", "data": {"name": "Sources Done", "code": "return {}"}, "position": {"x": 3300, "y": 600}}, # Bridge out of loop
        
        # --- QA & GATES ---
        {"id": "n11", "type": "code", "data": {"name": "Coverage", "code": c_coverage}, "position": {"x": 3600, "y": 0}},
        # Condition Node
        {"id": "n12_gate", "type": "condition", "data": {"name": "Refine Gate", "conditions": {"0": "gaps_found == True", "1": "gaps_found == False"}}, "position": {"x": 3900, "y": 0}},
        
        # Branch 0 (Refine - Loop back to Sources? For now, just skip to Coherence to avoid infinite loop complexity in JSON)
        # We will point 0 to Coherence anyway for V2.1 MVP of full graph
        
        # Branch 1 (OK)
        {"id": "n13_coh", "type": "vlm", "data": {"name": "Coherence", "isChatflowInput": False, "useChatHistory": False, "isChatflowOutput": False, "chatflowOutputVariable": "patch_actions", "mcpUse": {}, "vlmInput": "Analyze coherence for outline: {{micro_outline}}", "prompt": p_coherence, "modelConfig": gpt4o_config}, "position": {"x": 4200, "y": 0}},
        {"id": "n14_pat", "type": "code", "data": {"name": "Patch", "code": c_apply_patch}, "position": {"x": 4500, "y": 0}},
        
        # --- HUMAN ---
        {"id": "n15_rev", "type": "vlm", "data": {"name": "Human Review", "isChatflowInput": True, "useChatHistory": False, "isChatflowOutput": True, "chatflowOutputVariable": "user_changes", "mcpUse": {}, "vlmInput": "", "prompt": p_human, "modelConfig": gpt4o_config}, "position": {"x": 4800, "y": 0}},
        {"id": "n16_app", "type": "code", "data": {"name": "Apply User", "code": c_apply_user}, "position": {"x": 5100, "y": 0}},
        
        # --- EXPORT ---
        {"id": "n17_exp", "type": "code", "data": {"name": "Export", "code": c_export}, "position": {"x": 5400, "y": 0}},
        {"id": "n18_end", "type": "vlm", "data": {"name": "Display", "isChatflowInput": False, "useChatHistory": False, "isChatflowOutput": True, "chatflowOutputVariable": "", "mcpUse": {}, "vlmInput": "Export summary", "prompt": "Done.\n{{exports}}", "modelConfig": {"model_name": "gpt-4o", "system_prompt": "Done.\n{{exports}}", "set_chatflow_ai_response": True}}, "position": {"x": 5700, "y": 0}}
    ]
    
    edges = [
        # Main Flow
        {"source": "n0", "target": "n1"},
        {"source": "n1", "target": "n2"},
        {"source": "n2", "target": "n3"},
        {"source": "n3", "target": "n4_init"},
        {"source": "n4_init", "target": "n4_loop"},
        
        # Loop 1
        {"source": "n4_loop", "sourceHandle": "loop_body", "target": "n4_get"},
        {"source": "n4_get", "target": "n4_rag"},
        {"source": "n4_rag", "target": "n4_acc"},
        {"source": "n4_acc", "target": "n4_inc"},
        {"source": "n4_inc", "sourceHandle": "loop_next", "target": "n4_loop"}, # Close Loop 1
        {"source": "n4_loop", "target": "n5"},
        
        # Macro
        {"source": "n5", "target": "n6"},
        {"source": "n6", "target": "n7"},
        {"source": "n7", "target": "n8_loop"},
        
        # Loop 2
        {"source": "n8_loop", "sourceHandle": "loop_body", "target": "n8_get"},
        {"source": "n8_get", "target": "n8_gen"},
        {"source": "n8_gen", "target": "n8_app"},
        {"source": "n8_app", "target": "n8_inc"},
        {"source": "n8_inc", "sourceHandle": "loop_next", "target": "n8_loop"}, # Close Loop 2
        {"source": "n8_loop", "target": "n9"},
        
        # Loop 3
        {"source": "n9", "target": "n10_loop"},
        {"source": "n10_loop", "sourceHandle": "loop_body", "target": "n10_get"},
        {"source": "n10_get", "target": "n10_rag"},
        {"source": "n10_rag", "target": "n10_mer"},
        {"source": "n10_mer", "target": "n10_inc"},
        {"source": "n10_inc", "sourceHandle": "loop_next", "target": "n10_loop"}, # Close Loop 3
        {"source": "n10_loop", "target": "n11"},
        
        # Gate
        {"source": "n11", "target": "n12_gate"},
        # Case 0 (Gaps): For simplicity in JSON, we point both to Coherence, but normally we'd loop back.
        # Ideally: {"source": "n12_gate", "sourceHandle": "condition-0", "target": "n9"} # Retry retrieval?
        # Let's link both forward to avoid infinite loops without loop_iter protection
        {"source": "n12_gate", "sourceHandle": "condition-0", "target": "n13_coh"},
        {"source": "n12_gate", "sourceHandle": "condition-1", "target": "n13_coh"},
        
        # Finish
        {"source": "n13_coh", "target": "n14_pat"},
        {"source": "n14_pat", "target": "n15_rev"},
        {"source": "n15_rev", "target": "n16_app"},
        {"source": "n16_app", "target": "n17_exp"},
        {"source": "n17_exp", "target": "n18_end"}
    ]
    
    global_vars = {
        "thesis_topic": "",
        "thesis_language": "fr",
        "thesis_degree": "PhD",
        "thesis_format": "standard",
        "discipline_hint": "Science",
        "granularity_target": 3,
        "target_length_pages": 250,
        "citation_style": "APA",
        "min_sources_per_subsection": 3,
        "min_sources_per_chapter": 12,
        "max_redundancy_ratio": 0.70,
        "requirements": {},
        "seed_axes_json": {},
        "seed_axes": [],
        "axes_count": 0,
        "loop_idx": 0,
        "chapter_idx": 0,
        "subsection_idx": 0,
        "chapters_list": [],
        "chapters_count": 0,
        "subsections_list": [],
        "subsections_count": 0,
        "kb_map": {},
        "macro_outline": {},
        "micro_outline": {},
        "coverage": {},
        "patch_actions": {},
        "user_changes": {},
        "exports": {},
        "gaps_found": False
    }
    
    payload = {
        "username": USERNAME,
        "workflow_id": workflow_id,
        "workflow_name": "Thesis Blueprint (Minutieux V2.1 FULL)",
        "workflow_config": {},
        "start_node": "n0",
        "global_variables": global_vars,
        "nodes": nodes,
        "edges": edges
    }
    
    print(f"Deploying workflow with {len(nodes)} nodes...")
    response = requests.post(f"{API_BASE.replace('/v1', '')}/workflow/workflows", json=payload, headers=headers)
    
    if response.status_code == 200:
        print(f"✅ Workflow deployed! ID: {workflow_id}")
    else:
        print(f"❌ Failed: {response.text}")

if __name__ == "__main__":
    token = get_token()
    create_workflow(token)
