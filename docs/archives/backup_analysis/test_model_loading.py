#!/usr/bin/env python3
"""
Test if we can load the ColQwen2.5 model
"""

import os
import sys

# Add model-server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'model-server'))

try:
    from colpali_engine.models import ColQwen2_5, ColQwen2_5_Processor
    print("✅ colpali_engine imported successfully")
    
    model_path = "/model_weights/colqwen2.5-v0.2"
    print(f"\n🚀 Testing model loading from: {model_path}")
    
    # Check if path exists
    if os.path.exists(model_path):
        print(f"✅ Path exists")
        files = os.listdir(model_path)
        print(f"📁 Files in directory: {len(files)}")
        for f in sorted(files)[:10]:
            print(f"   - {f}")
    else:
        print(f"❌ Path does not exist")
        sys.exit(1)
    
    print("\n🔧 Testing ColQwen2_5.from_pretrained()...")
    try:
        # Try loading without GPU
        import torch
        print(f"Torch device: {torch.device('cpu')}")
        
        model = ColQwen2_5.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map="cpu",  # Force CPU
        )
        print("✅ Model loaded successfully!")
        
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nPlease install required packages:")
    print("pip install colpali-engine transformers torch")