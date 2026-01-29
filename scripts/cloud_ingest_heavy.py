# /// script
# dependencies = [
#     "colpali-engine==0.3.10",
#     "torch",
#     "transformers",
#     "bitsandbytes",
#     "pillow",
#     "numpy",
#     "datasets",
#     "pdf2image",
#     "huggingface_hub",
#     "einops",
#     "accelerate"
# ]
# ///

import torch
import os
import numpy as np
from PIL import Image
from pdf2image import convert_from_path
from datasets import load_dataset, Dataset
from colpali_engine.models import ColQwen2_5, ColQwen2_5_Processor
from transformers import BitsAndBytesConfig
from huggingface_hub import snapshot_download, HfApi, login
import shutil

# --- CONFIGURATION ---
INPUT_LOCAL_PATH = "literature/corpus"
OUTPUT_DIR = "embeddings_output"  # Local storage for incremental saves
MODEL_ID = "vidore/colqwen2.5-v0.2"
DPI = 200  # THE REQUESTED DPI
BATCH_SIZE = 4 # Turbo Mode: 4 images at a time
HF_TOKEN = os.environ.get("HF_TOKEN")

def main():
    if HF_TOKEN:
        login(token=HF_TOKEN)
        
    print(f"🚀 STARTING LOCAL INGESTION JOB | DPI={DPI}", flush=True)
    
    # Ensure output dir exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if torch.cuda.is_available():
        print(f"✅ GPU: {torch.cuda.get_device_name(0)}", flush=True)
    else:
        print("⚠️ No GPU detected! This will be slow.", flush=True)

    # 1. Use Local Corpus
    print(f"📂 Scanning local corpus at {INPUT_LOCAL_PATH}...", flush=True)
    local_dir = os.path.abspath(INPUT_LOCAL_PATH)
    
    # List PDFs
    pdf_files = []
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))
    
    # Sort for consistent processing order
    pdf_files.sort()
    print(f"📄 Found {len(pdf_files)} PDF files.", flush=True)

    # 2. Load Model (4-bit)
    print("🔧 Loading Model...", flush=True)
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

    # 3. Processing Loop
    total_pages_processed = 0
    
    for i, pdf_path in enumerate(pdf_files):
        filename = os.path.basename(pdf_path)
        # Check if already processed
        output_file = os.path.join(OUTPUT_DIR, f"{filename}.json")
        if os.path.exists(output_file):
            print(f"⏭️  Skipping {filename} (Already processed)", flush=True)
            continue
            
        print(f"Processing [{i+1}/{len(pdf_files)}]: {filename}", flush=True)
        pdf_results = []
        
        try:
            # Convert PDF to Images @ 200 DPI
            images = convert_from_path(pdf_path, dpi=DPI, thread_count=2) # Reduced threads to save RAM
            
            # Batch embedding
            for j in range(0, len(images), BATCH_SIZE):
                batch_imgs = images[j : j + BATCH_SIZE]
                
                # Process batch
                with torch.no_grad():
                    batch_inputs = processor.process_images(batch_imgs).to(model.device)
                    batch_emb = model(**batch_inputs)
                    
                # Move to CPU and store
                batch_emb_cpu = batch_emb.cpu().to(torch.float16)
                for k in range(len(batch_imgs)):
                    emb_list = batch_emb_cpu[k].numpy().tolist()
                    pdf_results.append({
                        "filename": filename,
                        "page_number": j + k + 1,
                        "embedding": emb_list,
                        "dpi": DPI
                    })
                
                # Explicit garbage collection to free VRAM/RAM
                del batch_inputs, batch_emb, batch_emb_cpu
                torch.cuda.empty_cache()

            # Save INCREMENTALLY to local JSON
            import json
            with open(output_file, 'w') as f:
                json.dump(pdf_results, f)
            
            total_pages_processed += len(images)
            print(f"   ✅ Saved {len(images)} pages to {output_file}", flush=True)
            
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}", flush=True)

    print(f"✅ Processing Complete. Total Pages: {total_pages_processed}", flush=True)
    print(f"📁 Results are in {OUTPUT_DIR}/. You can now upload them to HF or ingest to Milvus.", flush=True)

if __name__ == "__main__":
    main()
