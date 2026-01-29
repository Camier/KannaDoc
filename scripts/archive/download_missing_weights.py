#!/usr/bin/env python3
"""
Download missing adapter weights (adapter_model.safetensors) and tokenizer.json
"""

import os
import sys
from huggingface_hub import hf_hub_download, list_repo_files
import shutil

# Target directory in Docker volume
VOLUME_PATH = "/var/lib/docker/volumes/layra_model_weights/_data"
ADAPTER_DIR = os.path.join(VOLUME_PATH, "colqwen2.5-v0.2")
REPO_ID = "vidore/colqwen2.5-v0.2"

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def download_missing_files():
    print(f"Checking missing files in {ADAPTER_DIR}")
    
    # List remote files
    print(f"Listing files in {REPO_ID}...")
    remote_files = list_repo_files(REPO_ID)
    print(f"Found {len(remote_files)} remote files")
    
    # Filter for files we likely need
    important_patterns = ['.safetensors', 'tokenizer.json']
    important_files = [f for f in remote_files if any(p in f for p in important_patterns)]
    
    for remote_file in important_files:
        local_path = os.path.join(ADAPTER_DIR, remote_file)
        if os.path.exists(local_path):
            print(f"✓ {remote_file} already exists ({os.path.getsize(local_path):,} bytes)")
            continue
        
        print(f"⬇️ Downloading {remote_file}...")
        try:
            # Download to a temporary location first
            tmp_path = hf_hub_download(
                repo_id=REPO_ID,
                filename=remote_file,
                cache_dir=None,
                local_dir=ADAPTER_DIR,
                local_dir_use_symlinks=False,
                resume_download=True
            )
            print(f"✅ Downloaded {remote_file} to {tmp_path}")
        except Exception as e:
            print(f"❌ Failed to download {remote_file}: {e}")
            import traceback
            traceback.print_exc()
    
    # Verify downloaded files
    print("\n📁 Verifying adapter directory contents:")
    for f in sorted(os.listdir(ADAPTER_DIR)):
        if f.startswith('.'):
            continue
        path = os.path.join(ADAPTER_DIR, f)
        size = os.path.getsize(path)
        print(f"   - {f} ({size:,} bytes)")

if __name__ == "__main__":
    # Check if volume path exists
    if not os.path.exists(VOLUME_PATH):
        print(f"Error: Volume path {VOLUME_PATH} does not exist")
        sys.exit(1)
    
    # Ensure adapter directory exists
    ensure_dir(ADAPTER_DIR)
    
    download_missing_files()