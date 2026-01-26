#!/usr/bin/env python3
"""
Test adapter loading with PeftModel
"""

import os
import sys
import traceback

# Add huggingface token to environment
os.environ['HF_TOKEN'] = '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'

model_path = "/model_weights/colqwen2.5-v0.2"
base_model_path = "/model_weights/colqwen2.5-base"

print(f"Testing adapter loading...")
print(f"Adapter path: {model_path}")
print(f"Base model path: {base_model_path}")

# Try to load as PeftModel
try:
    from peft import PeftModel, PeftConfig
    import torch
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    
    print("\n1. Loading adapter config...")
    config = PeftConfig.from_pretrained(model_path)
    print(f"   Adapter config: {config.base_model_name_or_path}")
    print(f"   Adapter type: {config.peft_type}")
    
    print("\n2. Loading base model...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=torch.bfloat16,
        quantization_config=bnb_config,
        device_map="auto",
        attn_implementation="sdpa",
    )
    print("   Base model loaded")
    
    print("\n3. Applying adapter...")
    model = PeftModel.from_pretrained(base_model, model_path)
    print("   ✅ Adapter applied successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc()
    
# Try to load with colpali_engine directly
print("\n" + "="*60)
print("Testing colpali_engine loading...")
try:
    from colpali_engine.models import ColQwen2_5
    import torch
    from transformers import BitsAndBytesConfig
    
    print("Loading ColQwen2_5 directly...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    
    # Try with local_files_only=False to allow download
    model = ColQwen2_5.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        quantization_config=bnb_config,
        device_map="auto",
        attn_implementation="sdpa",
        local_files_only=False,  # Allow download
        token=os.environ['HF_TOKEN']
    )
    print("✅ ColQwen2_5 loaded with adapter!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    traceback.print_exc()