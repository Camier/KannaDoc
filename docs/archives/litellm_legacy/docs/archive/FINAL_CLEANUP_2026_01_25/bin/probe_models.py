#!/usr/bin/env python3
"""
Model Probe: Validates that every model in config.yaml is actually reachable.
Handles Chat, Embedding, and Rerank models appropriately.
"""

import os
import sys
import yaml
import time
import requests
from concurrent.futures import ThreadPoolExecutor

def load_config():
    """Load model list from config.yaml"""
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        return config.get("model_list", [])
    except Exception as e:
        print(f"❌ Error loading config.yaml: {e}")
        sys.exit(1)

def get_model_mode(model_entry):
    """Determine the mode of the model (chat, embedding, rerank)."""
    # Check model_info first
    if "model_info" in model_entry:
        return model_entry["model_info"].get("mode", "chat")
    
    # Fallback heuristics based on name
    name = model_entry.get("model_name", "").lower()
    if "embed" in name:
        return "embedding"
    if "rerank" in name:
        return "rerank"
    return "chat"

def probe_model(model_entry, base_url, api_key):
    """Send a test request to a single model based on its mode."""
    model_name = model_entry.get("model_name")
    if not model_name:
        return None

    mode = get_model_mode(model_entry)
    print(f"🔄 Probing {model_name} ({mode})...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Select endpoint and payload based on mode
    if mode == "embedding":
        endpoint = f"{base_url}/embeddings"
        payload = {
            "model": model_name,
            "input": ["test"]
        }
    elif mode == "rerank":
        endpoint = f"{base_url}/rerank"
        payload = {
            "model": model_name,
            "query": "test",
            "documents": ["doc1", "doc2"]
        }
    else: # Default to chat
        endpoint = f"{base_url}/chat/completions"
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1
        }

    start = time.time()
    try:
        resp = requests.post(
            endpoint, 
            json=payload, 
            headers=headers, 
            timeout=10
        )
        latency = time.time() - start
        
        if resp.status_code == 200:
            return {"name": model_name, "status": "✅", "latency": f"{latency:.2f}s"}
        else:
            return {"name": model_name, "status": "❌", "latency": f"{latency:.2f}s", "error": f"HTTP {resp.status_code}"}
            
    except Exception as e:
        return {"name": model_name, "status": "❌", "latency": "---", "error": str(e)}

def main():
    base_url = "http://127.0.0.1:4000"
    # Use Master Key if available, or try to get it from .env just in case
    api_key = os.environ.get("LITELLM_MASTER_KEY", "sk-safKz-RaebX20rwBBgPuIa7Xln2BTRm-FmMP5jtggAo") 
    
    models = load_config()
    print(f"📋 Found {len(models)} models in config.yaml")
    print(f"🚀 Starting probe against {base_url}")
    print("-" * 60)

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(probe_model, m, base_url, api_key) for m in models]
        for f in futures:
            if res := f.result():
                results.append(res)

    print("-" * 60)
    print(f"{ 'MODEL':<40} | {'STATUS':<5} | {'LATENCY':<10} | {'ERROR'}")
    print("-" * 60)
    
    failures = 0
    for r in results:
        error = r.get("error", "")
        print(f"{r['name']:<40} | {r['status']:<5} | {r['latency']:<10} | {error}")
        if r['status'] == "❌":
            failures += 1

    if failures > 0:
        print(f"\n⚠️  {failures} models failed probe.")
        sys.exit(1)
    else:
        print("\n✨ All models operational.")
        sys.exit(0)

if __name__ == "__main__":
    main()