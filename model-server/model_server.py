# app/core/model_server.py
from io import BytesIO
from typing import List
from fastapi import FastAPI, File, UploadFile, status
from fastapi.responses import JSONResponse
from colbert_service import colbert
import uvicorn
from pydantic import BaseModel
from PIL import Image
from contextlib import asynccontextmanager
import hashlib
import redis
import json
import torch
import os

from config import settings

# --- CONFIG ---
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = getattr(settings, "redis_password", os.getenv("REDIS_PASSWORD"))

redis_client = None

def get_redis():
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=REDIS_HOST, 
                port=REDIS_PORT, 
                password=REDIS_PASSWORD, 
                decode_responses=True
            )
            redis_client.ping()
            print("✅ Redis Cache Connected")
        except Exception as e:
            print(f"⚠️ Redis Cache Connection Failed: {e}")
            redis_client = None
    return redis_client

def compute_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def log_gpu_stats():
    try:
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        print(f"📊 GPU Mem: Allocated={allocated:.2f}GB, Reserved={reserved:.2f}GB")
    except:
        pass

# Lifecycle Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Server starting... Triggering Warmup.")
    get_redis() # Init Redis
    try:
        colbert.warmup()
        app.state.ready = True
    except Exception as e:
        print(f"❌ Warmup failed: {e}")
        app.state.ready = False
    
    yield
    
    # Shutdown
    print("🛑 Server shutting down.")

app = FastAPI(lifespan=lifespan)
app.state.ready = False # Default state
service = colbert  # 单实例加载

class TextRequest(BaseModel):
    queries: list  # 显式定义字段

@app.post("/embed_text")
async def embed_text(request: TextRequest):
    r = get_redis()
    results = [None] * len(request.queries)
    indices_to_compute = []
    queries_to_compute = []

    # 1. Check Cache
    if r:
        for i, query in enumerate(request.queries):
            key = f"cache:embed:text:{compute_hash(query.encode('utf-8'))}"
            cached = r.get(key)
            if cached:
                results[i] = json.loads(cached)
            else:
                indices_to_compute.append(i)
                queries_to_compute.append(query)
    else:
        indices_to_compute = list(range(len(request.queries)))
        queries_to_compute = request.queries

    # 2. Compute Missing
    if queries_to_compute:
        print(f"Computing {len(queries_to_compute)} text embeddings...")
        computed_embeddings = service.process_query(queries_to_compute)
        
        # 3. Fill results and Cache
        for local_idx, global_idx in enumerate(indices_to_compute):
            emb = computed_embeddings[local_idx]
            results[global_idx] = emb
            if r:
                key = f"cache:embed:text:{compute_hash(queries_to_compute[local_idx].encode('utf-8'))}"
                r.setex(key, 86400, json.dumps(emb)) # Cache for 24h

    log_gpu_stats()
    return {"embeddings": results}

@app.post("/embed_image")
async def embed_image(images: List[UploadFile] = File(...)):
    r = get_redis()
    results = [None] * len(images)
    indices_to_compute = []
    pil_images_to_compute = []
    cache_keys_to_set = []

    for i, image_file in enumerate(images):
        content = await image_file.read()
        
        if r:
            file_hash = compute_hash(content)
            key = f"cache:embed:image:{file_hash}"
            cached = r.get(key)
            if cached:
                results[i] = json.loads(cached)
                await image_file.close()
                continue
            cache_keys_to_set.append(key)
        
        # If not cached or no redis, prepare for computation
        buffer = BytesIO(content)
        image = Image.open(buffer).convert("RGB") # Ensure RGB
        indices_to_compute.append(i)
        pil_images_to_compute.append(image)
        await image_file.close()

    if pil_images_to_compute:
        print(f"Computing {len(pil_images_to_compute)} image embeddings (Cached: {len(images) - len(pil_images_to_compute)})...")
        computed_embeddings = service.process_image(pil_images_to_compute)
        
        for local_idx, global_idx in enumerate(indices_to_compute):
            emb = computed_embeddings[local_idx]
            results[global_idx] = emb
            
            if r and local_idx < len(cache_keys_to_set):
                # Cache the result
                r.setex(cache_keys_to_set[local_idx], 86400, json.dumps(emb))

    log_gpu_stats()
    return {"embeddings": results}

# Liveness Probe
@app.get("/health/live", response_model=dict)
async def health_live():
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ALIVE"})

# Readiness Probe
@app.get("/health/ready", response_model=dict)
async def health_ready():
    if app.state.ready:
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "READY"})
    else:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "NOT_READY"})

@app.get("/healthy-check", response_model=dict)
async def healthy_check():
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "UP"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
