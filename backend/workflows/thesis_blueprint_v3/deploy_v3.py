"""
LAYRA Thesis Blueprint V3 Deployment Script
=============================================
Deploys the V3 thesis blueprint workflow with:
- CLIProxyAPI backend with RAG support
- 3 Human Gates (scope, structure, final)
- Single chapter loop for micro-outline generation
- Coverage scoring and coherence checking
- Export to Markdown/LaTeX

Usage:
    python3 deploy_v3.py

Alternative with custom username:
    THESIS_USERNAME=miko python3 deploy_v3.py

Note: Authentication has been removed for research-only deployment.
"""

import requests
import uuid
import json
import os
from pathlib import Path

# Configuration
API_BASE = "http://localhost:8090/api/v1"
USERNAME = os.environ.get("THESIS_USERNAME", "miko")
KB_ID = "miko_e6643365-8b03_4bea-a69b_7a1df00ec653"  # Active Thesis Corpus KB

# Directory paths
SCRIPT_DIR = Path(__file__).parent
PROMPTS_DIR = SCRIPT_DIR / "prompts"
CODE_NODES_DIR = SCRIPT_DIR / "code_nodes"


def load_file(path):
    """Load file content from path."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: File not found: {path}")
        return ""


def create_workflow():
    """Create and deploy the V3 workflow."""
    headers = {}
    workflow_id = f"{USERNAME}_{uuid.uuid4()}"

    # --- PROMPTS ---
    p_requirements = load_file(PROMPTS_DIR / "01_requirements_builder.txt")
    p_kb_analysis = load_file(PROMPTS_DIR / "02_kb_deep_analysis.txt")
    p_human_scope = load_file(PROMPTS_DIR / "03_human_gate_scope.txt")
    p_macro_gen = load_file(PROMPTS_DIR / "04_macro_outline_generator.txt")
    p_human_structure = load_file(PROMPTS_DIR / "05_human_gate_structure.txt")
    p_micro_chapter = load_file(PROMPTS_DIR / "06_micro_outline_chapter.txt")
    p_sources = load_file(PROMPTS_DIR / "07_sources_retrieval.txt")
    p_coherence = load_file(PROMPTS_DIR / "08_coherence_check.txt")
    p_human_final = load_file(PROMPTS_DIR / "09_human_gate_final.txt")
    p_display = load_file(PROMPTS_DIR / "10_display_result.txt")

    # --- CODE NODES ---
    c_parse_kb = load_file(CODE_NODES_DIR / "parse_kb_analysis.py")
    c_apply_scope = load_file(CODE_NODES_DIR / "apply_scope_changes.py")
    c_parse_macro = load_file(CODE_NODES_DIR / "parse_macro_outline.py")
    c_apply_structure = load_file(CODE_NODES_DIR / "apply_structure_changes.py")
    c_init_loop = load_file(CODE_NODES_DIR / "init_chapter_loop.py")
    c_get_chapter = load_file(CODE_NODES_DIR / "get_current_chapter.py")
    c_merge_micro = load_file(CODE_NODES_DIR / "merge_chapter_micro.py")
    c_inc_chapter = load_file(CODE_NODES_DIR / "inc_chapter_idx.py")
    c_coverage = load_file(CODE_NODES_DIR / "coverage_scoring.py")
    c_apply_patches = load_file(CODE_NODES_DIR / "apply_patches.py")
    c_export = load_file(CODE_NODES_DIR / "export_toc.py")

    # Inline code for apply_final (user changes from final human gate)
    c_apply_final = '''
import ast

def get_val(key, default=None):
    """Safely parse global variable."""
    raw = globals().get(key, default)
    if raw is None:
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return ast.literal_eval(str(raw))
    except:
        return raw if raw else default

# Get user changes from human gate and current outline
user_changes = get_val("user_changes", {})
micro_outline = get_val("micro_outline", {})

if user_changes and isinstance(user_changes, dict):
    # Apply any modifications the user requested
    if "modifications" in user_changes:
        for mod in user_changes["modifications"]:
            chapter_id = mod.get("chapter_id")
            new_content = mod.get("content")
            if chapter_id and new_content:
                for chapter in micro_outline.get("chapters", []):
                    if chapter.get("id") == chapter_id:
                        chapter.update(new_content)
    
    # Apply additions
    if "additions" in user_changes:
        for addition in user_changes["additions"]:
            micro_outline.setdefault("chapters", []).append(addition)
    
    # Apply deletions
    if "deletions" in user_changes:
        del_ids = set(user_changes["deletions"])
        if micro_outline.get("chapters"):
            micro_outline["chapters"] = [
                ch for ch in micro_outline["chapters"]
                if ch.get("id") not in del_ids
            ]

print(f"####Global variable updated####micro_outline####")
print(repr(micro_outline))
return {"status": "final_changes_applied"}
'''

    # --- MODEL CONFIG (CLIProxyAPI with RAG) ---
    model_config = {
        "model_id": "cliproxyapi_sonnet",
        "model_name": "claude-sonnet-4-5",
        "model_url": "http://cliproxyapi:8317/v1",
        "api_key": os.environ.get("CLIPROXYAPI_API_KEY", "layra-cliproxyapi-key"),
        "base_used": [{"name": "Thesis Corpus", "baseId": KB_ID}],
        "temperature": 0.5,
        "max_length": 4096,
        "top_P": 1,
        "top_K": 10,
        "score_threshold": 10,
    }

    # Model config without RAG (for nodes that don't need KB retrieval)
    model_config_no_rag = {
        "model_id": "cliproxyapi_sonnet",
        "model_name": "claude-sonnet-4-5",
        "model_url": "http://cliproxyapi:8317/v1",
        "api_key": os.environ.get("CLIPROXYAPI_API_KEY", "layra-cliproxyapi-key"),
        "base_used": [],
        "temperature": 0.5,
        "max_length": 4096,
        "top_P": 1,
        "top_K": 10,
        "score_threshold": 10,
    }

    # --- NODES ---
    nodes = [
        # === PHASE 1: REQUIREMENTS & KB ANALYSIS ===
        {
            "id": "n0",
            "type": "start",
            "data": {"name": "Start"},
            "position": {"x": 0, "y": 0},
        },
        {
            "id": "n1",
            "type": "vlm",
            "data": {
                "name": "Requirements Builder",
                "isChatflowInput": False,
                "useChatHistory": False,
                "isChatflowOutput": False,
                "chatflowOutputVariable": "requirements",
                "mcpUse": {},
                "vlmInput": "Build requirements for topic: {{thesis_topic}}",
                "prompt": p_requirements,
                "modelConfig": model_config_no_rag,
            },
            "position": {"x": 300, "y": 0},
        },
        {
            "id": "n2",
            "type": "vlm",
            "data": {
                "name": "KB Deep Analysis",
                "isChatflowInput": False,
                "useChatHistory": False,
                "isChatflowOutput": False,
                "chatflowOutputVariable": "kb_analysis",
                "mcpUse": {},
                "vlmInput": "Analyze knowledge base for requirements: {{requirements}}",
                "prompt": p_kb_analysis,
                "modelConfig": model_config,  # RAG enabled
            },
            "position": {"x": 600, "y": 0},
        },
        {
            "id": "n3",
            "type": "code",
            "data": {"name": "Parse KB Analysis", "code": c_parse_kb},
            "position": {"x": 900, "y": 0},
        },
        # === HUMAN GATE 1: SCOPE ===
        {
            "id": "n4",
            "type": "vlm",
            "data": {
                "name": "Human Gate: Scope",
                "isChatflowInput": True,
                "useChatHistory": False,
                "isChatflowOutput": True,
                "chatflowOutputVariable": "scope_changes",
                "mcpUse": {},
                "vlmInput": "",
                "prompt": p_human_scope,
                "modelConfig": model_config_no_rag,
            },
            "position": {"x": 1200, "y": 0},
        },
        {
            "id": "n5",
            "type": "code",
            "data": {"name": "Apply Scope Changes", "code": c_apply_scope},
            "position": {"x": 1500, "y": 0},
        },
        # === PHASE 2: MACRO OUTLINE ===
        {
            "id": "n6",
            "type": "vlm",
            "data": {
                "name": "Macro Outline Generator",
                "isChatflowInput": False,
                "useChatHistory": False,
                "isChatflowOutput": False,
                "chatflowOutputVariable": "macro_outline",
                "mcpUse": {},
                "vlmInput": "Generate macro outline based on KB map: {{kb_map}}",
                "prompt": p_macro_gen,
                "modelConfig": model_config,  # RAG enabled
            },
            "position": {"x": 1800, "y": 0},
        },
        {
            "id": "n7",
            "type": "code",
            "data": {"name": "Parse Macro Outline", "code": c_parse_macro},
            "position": {"x": 2100, "y": 0},
        },
        # === HUMAN GATE 2: STRUCTURE ===
        {
            "id": "n8",
            "type": "vlm",
            "data": {
                "name": "Human Gate: Structure",
                "isChatflowInput": True,
                "useChatHistory": False,
                "isChatflowOutput": True,
                "chatflowOutputVariable": "structure_changes",
                "mcpUse": {},
                "vlmInput": "",
                "prompt": p_human_structure,
                "modelConfig": model_config_no_rag,
            },
            "position": {"x": 2400, "y": 0},
        },
        {
            "id": "n9",
            "type": "code",
            "data": {"name": "Apply Structure Changes", "code": c_apply_structure},
            "position": {"x": 2700, "y": 0},
        },
        # === PHASE 3: CHAPTER LOOP ===
        {
            "id": "n10",
            "type": "code",
            "data": {"name": "Init Chapter Loop", "code": c_init_loop},
            "position": {"x": 3000, "y": 0},
        },
        {
            "id": "n11",
            "type": "loop",
            "data": {
                "name": "Chapter Loop",
                "loopType": "condition",
                "condition": "chapter_idx < chapters_count",
            },
            "position": {"x": 3300, "y": 0},
        },
        # --- Loop Body ---
        {
            "id": "n11a",
            "type": "code",
            "data": {"name": "Get Current Chapter", "code": c_get_chapter},
            "position": {"x": 3300, "y": 300},
        },
        {
            "id": "n11b",
            "type": "vlm",
            "data": {
                "name": "Micro Outline Gen",
                "isChatflowInput": False,
                "useChatHistory": False,
                "isChatflowOutput": False,
                "chatflowOutputVariable": "micro_chapter",
                "mcpUse": {},
                "vlmInput": "Generate micro outline for chapter: {{current_chapter}}",
                "prompt": p_micro_chapter,
                "modelConfig": model_config,  # RAG enabled
            },
            "position": {"x": 3600, "y": 300},
        },
        {
            "id": "n11c",
            "type": "vlm",
            "data": {
                "name": "Sources Retrieval",
                "isChatflowInput": False,
                "useChatHistory": False,
                "isChatflowOutput": False,
                "chatflowOutputVariable": "chapter_sources",
                "mcpUse": {},
                "vlmInput": "Retrieve sources for chapter sections: {{micro_chapter}}",
                "prompt": p_sources,
                "modelConfig": model_config,  # RAG enabled
            },
            "position": {"x": 3900, "y": 300},
        },
        {
            "id": "n11d",
            "type": "code",
            "data": {"name": "Merge Chapter Micro", "code": c_merge_micro},
            "position": {"x": 4200, "y": 300},
        },
        {
            "id": "n11e",
            "type": "code",
            "data": {"name": "Inc Chapter Index", "code": c_inc_chapter},
            "position": {"x": 4500, "y": 300},
        },
        # === PHASE 4: QUALITY ASSURANCE ===
        {
            "id": "n12",
            "type": "code",
            "data": {"name": "Coverage Scoring", "code": c_coverage},
            "position": {"x": 3600, "y": 0},
        },
        {
            "id": "n13",
            "type": "vlm",
            "data": {
                "name": "Coherence Check",
                "isChatflowInput": False,
                "useChatHistory": False,
                "isChatflowOutput": False,
                "chatflowOutputVariable": "coherence_patches",
                "mcpUse": {},
                "vlmInput": "Analyze coherence for outline: {{micro_outline}}",
                "prompt": p_coherence,
                "modelConfig": model_config_no_rag,
            },
            "position": {"x": 3900, "y": 0},
        },
        {
            "id": "n14",
            "type": "code",
            "data": {"name": "Apply Patches", "code": c_apply_patches},
            "position": {"x": 4200, "y": 0},
        },
        # === HUMAN GATE 3: FINAL REVIEW ===
        {
            "id": "n15",
            "type": "vlm",
            "data": {
                "name": "Human Gate: Final",
                "isChatflowInput": True,
                "useChatHistory": False,
                "isChatflowOutput": True,
                "chatflowOutputVariable": "user_changes",
                "mcpUse": {},
                "vlmInput": "",
                "prompt": p_human_final,
                "modelConfig": model_config_no_rag,
            },
            "position": {"x": 4500, "y": 0},
        },
        {
            "id": "n16",
            "type": "code",
            "data": {"name": "Apply Final Changes", "code": c_apply_final},
            "position": {"x": 4800, "y": 0},
        },
        # === PHASE 5: EXPORT ===
        {
            "id": "n17",
            "type": "code",
            "data": {"name": "Export ToC", "code": c_export},
            "position": {"x": 5100, "y": 0},
        },
        {
            "id": "n18",
            "type": "vlm",
            "data": {
                "name": "Display Result",
                "isChatflowInput": False,
                "useChatHistory": False,
                "isChatflowOutput": True,
                "chatflowOutputVariable": "",
                "mcpUse": {},
                "vlmInput": "Present the final thesis blueprint",
                "prompt": p_display,
                "modelConfig": {
                    "model_name": "claude-sonnet-4-5",
                    "system_prompt": "Display the completed thesis blueprint.",
                    "set_chatflow_ai_response": True,
                },
            },
            "position": {"x": 5400, "y": 0},
        },
    ]

    # --- EDGES ---
    edges = [
        # Phase 1: Requirements & KB
        {"source": "n0", "target": "n1"},
        {"source": "n1", "target": "n2"},
        {"source": "n2", "target": "n3"},
        {"source": "n3", "target": "n4"},
        # Human Gate 1 → Macro
        {"source": "n4", "target": "n5"},
        {"source": "n5", "target": "n6"},
        {"source": "n6", "target": "n7"},
        {"source": "n7", "target": "n8"},
        # Human Gate 2 → Loop
        {"source": "n8", "target": "n9"},
        {"source": "n9", "target": "n10"},
        {"source": "n10", "target": "n11"},
        # Loop: Body
        {"source": "n11", "sourceHandle": "loop_body", "target": "n11a"},
        {"source": "n11a", "target": "n11b"},
        {"source": "n11b", "target": "n11c"},
        {"source": "n11c", "target": "n11d"},
        {"source": "n11d", "target": "n11e"},
        {
            "source": "n11e",
            "sourceHandle": "loop_next",
            "target": "n11",
        },  # Back to loop
        # Loop: Exit → QA
        {"source": "n11", "target": "n12"},
        {"source": "n12", "target": "n13"},
        {"source": "n13", "target": "n14"},
        {"source": "n14", "target": "n15"},
        # Human Gate 3 → Export
        {"source": "n15", "target": "n16"},
        {"source": "n16", "target": "n17"},
        {"source": "n17", "target": "n18"},
    ]

    # --- GLOBAL VARIABLES ---
    global_vars = {
        # User inputs
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
        # Pipeline state
        "requirements": {},
        "kb_analysis": {},
        "kb_map": {},
        "scope_changes": {},
        "macro_outline": {},
        "structure_changes": {},
        "micro_outline": {},
        "micro_chapter": {},
        "chapter_sources": {},
        "coherence_patches": {},
        "user_changes": {},
        "coverage": {},
        "exports": {},
        # Loop control
        "chapter_idx": 0,
        "chapters_list": [],
        "chapters_count": 0,
        "current_chapter": {},
    }

    # --- PAYLOAD ---
    payload = {
        "username": USERNAME,
        "workflow_id": workflow_id,
        "workflow_name": "Thesis Blueprint V3 (CLIProxyAPI + Human Gates)",
        "workflow_config": {},
        "start_node": "n0",
        "global_variables": global_vars,
        "nodes": nodes,
        "edges": edges,
    }

    print(f"Deploying Thesis Blueprint V3 with {len(nodes)} nodes...")
    print(f"  - Username: {USERNAME}")
    print(f"  - KB ID: {KB_ID}")
    print(f"  - Workflow ID: {workflow_id}")

    # Deploy via API
    url = f"{API_BASE}/workflow/workflows"
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        print(f"Workflow deployed successfully!")
        print(f"  Workflow ID: {workflow_id}")
        return workflow_id
    else:
        print(f"Deployment failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return None


if __name__ == "__main__":
    workflow_id = create_workflow()

    if workflow_id:
        print("\n" + "=" * 60)
        print("Thesis Blueprint V3 Deployed!")
        print("=" * 60)
        print(f"Access the workflow in the UI or execute via API:")
        print(f"  POST /api/workflow/execute/{workflow_id}")
        print("=" * 60)
