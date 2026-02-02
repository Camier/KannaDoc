# /// script
# dependencies = [
#     "colpali-engine==0.3.10",
#     "torch",
#     "transformers",
#     "bitsandbytes",
#     "pillow",
#     "numpy",
#     "pdf2image",
#     "psutil"
# ]
# ///

import torch
import os
import time
import psutil
from PIL import Image
from pdf2image import convert_from_path
from colpali_engine.models import ColQwen2_5, ColQwen2_5_Processor
from transformers import BitsAndBytesConfig
import subprocess

# --- CONFIG ---
# Search for a valid PDF in the directory
CORPUS_DIR = "literature/corpus"
try:
    TEST_PDF = next(os.path.join(CORPUS_DIR, f) for f in os.listdir(CORPUS_DIR) if f.endswith(".pdf"))
except StopIteration:
    print("❌ No PDF found in literature/corpus")
    exit(1)

DPI = 200
MODEL_ID = "vidore/colqwen2.5-v0.2"

def get_gpu_memory():
    """Returns used memory in MB"""
    try:
        result = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,nounits,noheader"], 
            encoding='utf-8'
        )
        return int(result.strip().split('\n')[0])
    except:
        return 0

def benchmark():
    print(f"🔬 STARTING GPU BENCHMARK | GPU: {torch.cuda.get_device_name(0)}")
    print(f"📄 Test File: {TEST_PDF}")
    print(f"🎯 Target DPI: {DPI}")

    # 1. Load Model
    print("\n1️⃣  Loading Model (4-bit)...")
    torch.cuda.empty_cache()
    mem_before = get_gpu_memory()
    
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    model = ColQwen2_5.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
    ).eval()
    processor = ColQwen2_5_Processor.from_pretrained(MODEL_ID)
    
    mem_after_load = get_gpu_memory()
    print(f"✅ Model Loaded. VRAM used by weights: {mem_after_load - mem_before} MB (Total: {mem_after_load} MB)")

    # 2. Prepare Images
    print("\n2️⃣  Rasterizing PDF...")
    images = convert_from_path(TEST_PDF, dpi=DPI)
    if len(images) < 4:
        # Duplicate to have enough for batch testing
        images = (images * 4)[:4]
    else:
        images = images[:4]
    print(f"✅ Ready with {len(images)} test images (Avg size: {images[0].size})")

    # 3. Stress Test
    batch_sizes = [1, 2, 4]
    
    for bs in batch_sizes:
        print(f"\n🧪 Testing BATCH SIZE = {bs}...")
        torch.cuda.empty_cache()
        start_mem = get_gpu_memory()
        
        try:
            batch_imgs = images[:bs]
            
            # Start timer
            t0 = time.time()
            
            # Forward pass
            with torch.no_grad():
                batch_inputs = processor.process_images(batch_imgs).to(model.device)
                _ = model(**batch_inputs)
            
            t1 = time.time()
            peak_mem = get_gpu_memory()
            
            print(f"   ✅ SUCCESS")
            print(f"   ⏱️  Time: {t1-t0:.2f}s ({(t1-t0)/bs:.2f}s per page)")
            print(f"   💾 Peak VRAM Delta: +{peak_mem - start_mem} MB")
            print(f"   🚨 Total VRAM: {peak_mem} MB / 16384 MB")
            
            if peak_mem > 15000:
                print("   ⚠️  WARNING: Very close to OOM limit!")
                
        except torch.cuda.OutOfMemoryError:
            print(f"   ❌ FAILED: Out Of Memory (OOM)")
            print("   ⛔ STOPPING BENCHMARK")
            break
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            break

if __name__ == "__main__":
    benchmark()
