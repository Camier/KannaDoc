# /// script
# dependencies = [
#     "colpali-engine==0.3.10",
#     "torch",
#     "transformers",
#     "bitsandbytes",
#     "pillow",
#     "numpy"
# ]
# ///

import torch
from colpali_engine.models import ColQwen2_5, ColQwen2_5_Processor
from PIL import Image
import numpy as np
from transformers import BitsAndBytesConfig
import os

def run_job():
    # Use the public model ID since we are on HF Jobs
    model_id = "vidore/colqwen2.5-v0.2"
    print(f"🚀 Starting Job: Loading model {model_id}...")
    
    # Check GPU
    if torch.cuda.is_available():
        print(f"✅ GPU Detected: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ No GPU detected! This might be slow or fail.")

    # 4-bit quantization config (same as local)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    
    try:
        model = ColQwen2_5.from_pretrained(
            model_id,
            quantization_config=bnb_config,
            device_map="auto",
        ).eval()
        print("✅ Model loaded successfully!")
    except Exception as e:
        print(f"❌ Model load failed: {e}")
        # Try without quantization if that fails (though flavor l4x1 supports it)
        print("Retrying without 4-bit config...")
        model = ColQwen2_5.from_pretrained(
            model_id,
            device_map="auto",
        ).eval()

    try:
        processor = ColQwen2_5_Processor.from_pretrained(model_id)
        print("✅ Processor loaded successfully!")
    except Exception as e:
        print(f"❌ Processor load failed: {e}")
        raise
    
    print("🔥 Running Warmup...")
    
    # 1. Text Embedding
    queries = ["Hello from Hugging Face Jobs!", "Visual RAG is cool."]
    batch_query = processor.process_queries(queries).to(model.device)
    with torch.no_grad():
        text_emb = model(**batch_query)
    print(f"✅ Text Embeddings computed. Shape: {text_emb.shape}")
        
    # 2. Image Embedding
    img = Image.fromarray(np.zeros((224, 224, 3), dtype=np.uint8))
    batch_img = processor.process_images([img]).to(model.device)
    with torch.no_grad():
        img_emb = model(**batch_img)
    print(f"✅ Image Embeddings computed. Shape: {img_emb.shape}")
        
    print("🎉 Job Completed Successfully: Layra Model Server Logic Verified on Cloud.")

if __name__ == "__main__":
    run_job()
