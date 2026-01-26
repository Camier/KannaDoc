#!/usr/bin/env python3
"""
Debug script to trace model loading errors
"""

import os
import sys
import traceback

# Monkey patch to debug
import transformers.utils.hub
original_cached_file = transformers.utils.hub.cached_file
original_cached_files = transformers.utils.hub.cached_files

def debug_cached_file(path_or_repo_id, filename, **kwargs):
    print(f"🔍 cached_file called: path_or_repo_id={path_or_repo_id}, filename={filename}")
    print(f"   kwargs: {kwargs}")
    try:
        result = original_cached_file(path_or_repo_id, filename, **kwargs)
        print(f"✅ cached_file success: {result}")
        return result
    except Exception as e:
        print(f"❌ cached_file error: {e}")
        raise

def debug_cached_files(path_or_repo_id, filenames, **kwargs):
    print(f"🔍 cached_files called: path_or_repo_id={path_or_repo_id}, filenames={filenames}")
    print(f"   kwargs: {kwargs}")
    try:
        result = original_cached_files(path_or_repo_id, filenames, **kwargs)
        print(f"✅ cached_files success: {len(result)} files")
        return result
    except Exception as e:
        print(f"❌ cached_files error: {e}")
        raise

# Apply patches
transformers.utils.hub.cached_file = debug_cached_file
transformers.utils.hub.cached_files = debug_cached_files

# Also patch configuration_utils (they import from utils.hub)
import transformers.configuration_utils
transformers.configuration_utils.cached_file = debug_cached_file
transformers.configuration_utils.cached_files = debug_cached_files

print("Patched cached_file/cached_files functions")

# Now try to load the model
model_path = "/model_weights/colqwen2.5-v0.2"
print(f"\n🚀 Attempting to load model from {model_path}")
print(f"Path exists: {os.path.exists(model_path)}")

try:
    from colpali_engine.models import ColQwen2_5
    import torch
    from transformers import BitsAndBytesConfig
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    
    print("Calling ColQwen2_5.from_pretrained...")
    model = ColQwen2_5.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        quantization_config=bnb_config,
        device_map="auto",
        attn_implementation="sdpa",
        local_files_only=True,
    )
    print("✅ Model loaded successfully!")
    
except Exception as e:
    print(f"❌ Model loading failed: {e}")
    traceback.print_exc()
    
    # List directory contents
    print(f"\n📁 Contents of {model_path}:")
    for f in sorted(os.listdir(model_path)):
        if f.startswith('.'):
            continue
        full = os.path.join(model_path, f)
        size = os.path.getsize(full)
        print(f"   - {f} ({size:,} bytes)")