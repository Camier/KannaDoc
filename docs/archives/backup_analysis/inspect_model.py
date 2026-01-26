#!/usr/bin/env python3
"""
Inspect ColQwen2_5 class attributes
"""

import os
import sys

try:
    from colpali_engine.models import ColQwen2_5
    print("✅ Successfully imported ColQwen2_5")
    print(f"Class: {ColQwen2_5}")
    print(f"Module: {ColQwen2_5.__module__}")
    
    # Check config_class
    if hasattr(ColQwen2_5, 'config_class'):
        print(f"config_class: {ColQwen2_5.config_class}")
        print(f"config_class.__name__: {ColQwen2_5.config_class.__name__}")
    
    # Check _auto_class
    if hasattr(ColQwen2_5, '_auto_class'):
        print(f"_auto_class: {ColQwen2_5._auto_class}")
    
    # Check __bases__
    print(f"Bases: {ColQwen2_5.__bases__}")
    
    # Try to find where repo ID is defined
    import inspect
    try:
        source = inspect.getsourcefile(ColQwen2_5)
        print(f"Source file: {source}")
    except:
        pass
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Also check transformers auto mapping
print("\n🔍 Checking transformers auto mapping...")
try:
    from transformers import AutoConfig
    config = AutoConfig.from_pretrained("/model_weights/colqwen2.5-v0.2", local_files_only=True)
    print(f"AutoConfig loaded: {config}")
    print(f"Config _name_or_path: {getattr(config, '_name_or_path', 'N/A')}")
except Exception as e:
    print(f"AutoConfig error: {e}")