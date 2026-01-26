# LAYRA Embeddings Pipeline

**Complete flow from file upload to vector search**

---

## 🏗️ Architecture Overview

```
                    FILE UPLOAD
                        ↓
        ┌───────────────────────────────┐
        │   Document Processing Layer   │
        │  (convert_file.py)            │
        ├───────────────────────────────┤
        │ • PDF → PNG/JPG (200 DPI)    │
        │ • DOCX/PPT → PDF → Images    │
        │ • Raw images → Resize        │
        │ • Batch into chunks          │
        └────────────┬──────────────────┘
                     ↓
        ┌───────────────────────────────┐
        │   Embedding Model Layer       │
        │  (get_embedding.py)           │
        ├───────────────────────────────┤
        │ LOCAL: ColBERT (GPU)          │
        │ • colbert_service.py          │
        │ • 4-bit quantization          │
        │ • Model: ColQwen 2.5          │
        │ • Output: 128-dim vectors     │
        │                               │
        │ CLOUD: Jina Embeddings V4     │
        │ • API-based                   │
        │ • Multi-vector support        │
        └────────────┬──────────────────┘
                     ↓
        ┌───────────────────────────────┐
        │   Vector Database Layer       │
        │  (milvus.py)                  │
        ├───────────────────────────────┤
        │ • HNSW Index (M=32, ef=500)  │
        │ • IP metric (Inner Product)   │
        │ • Metadata stored:            │
        │   - image_id, page_number     │
        │   - file_id, chunk_index      │
        └────────────┬──────────────────┘
                     ↓
        ┌───────────────────────────────┐
        │      Query Processing         │
        │  (RAG Search)                 │
        ├───────────────────────────────┤
        │ • User query → Embedding      │
        │ • Semantic search (top-k)     │
        │ • MaxSim reranking            │
        │ • Context assembly            │
        └────────────┬──────────────────┘
                     ↓
                LLM RESPONSE
```

---

## 📄 Step 1: Document Conversion

**File**: `backend/app/rag/convert_file.py`

### Input Formats Supported
```
PDF → PNG/JPG (pdf2image)
DOCX/PPT/XLS → PDF → PNG/JPG (LibreOffice UNO)
PNG/JPG/GIF/WebP/etc → Resize to A4
```

### DPI Adaptation Strategy
```python
if page_count > 50:
    effective_dpi = 150  # Faster, lower quality
else:
    effective_dpi = 200  # Default, balanced
```

**Output**: List of PIL Images (1 per page)

### Code Flow
```python
# convert_file_to_images() function
1. Detect file type by extension
2. If image → resize to A4 (25.4 x 35.6 cm)
3. If PDF → pdf2image.convert_from_bytes(dpi=effective_dpi)
4. If other → LibreOffice UNO conversion
5. Return List[BytesIO]

# Adaptive DPI: auto-reduces for large PDFs
page_count = get_pdf_page_count(pdf_bytes)
if page_count > 50:  # Large doc
    dpi = 150  # 25% smaller, 2x faster
else:
    dpi = 200  # Default quality
```

---

## 🧠 Step 2: Embedding Generation

**File**: `backend/app/rag/get_embedding.py`

### Two Model Options

#### Option A: Local ColBERT (GPU)
**File**: `model-server/colbert_service.py`

```python
class ColBERTService:
    def __init__(self, model_path="/model_weights/colqwen2.5-v0.2"):
        # GPU Configuration
        torch.backends.cuda.matmul.allow_tf32 = True  # Enable TF32
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        
        # 4-bit Quantization
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )
        
        # Model Loading
        self.model = ColQwen2_5.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            quantization_config=bnb_config,
            device_map="auto",
            attn_implementation="sdpa"
        )
        
        # Processor with size constraints
        self.processor = ColQwen2_5_Processor.from_pretrained(
            model_path,
            size={
                "shortest_edge": 56 * 56,
                "longest_edge": 28 * 28 * 768
            }
        )
```

**Performance**:
- Throughput: 1.67 img/s (RTX 4090)
- Memory: ~23GB (4-bit quantized)
- Latency: ~600ms per image
- Output: 128-dim vectors

**Endpoints**:
- `/embed_text` - Text embeddings
- `/embed_image` - Image embeddings

#### Option B: Jina Embeddings V4 (Cloud)
```python
async def _get_jina_embeddings(
    data: List[str|BytesIO],
    endpoint: "embed_text" | "embed_image",
    api_key: str
):
    # Task mapping
    task = {
        "embed_text": "retrieval.query",
        "embed_image": "retrieval.passage"
    }[endpoint]
    
    # Multi-vector support
    payload = {
        "model": "jina-embeddings-v4",
        "task": task,
        "return_multivector": True,
        "input": data
    }
    
    response = await client.post(
        "https://api.jina.ai/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload
    )
```

**Performance**:
- Throughput: ~0.5 img/s (API latency)
- Cost: Per-image billing
- Latency: 1-2s per batch

### Configuration
```bash
# .env
EMBEDDING_MODEL=local_colqwen  # or jina_embeddings_v4
COLBERT_MODEL_PATH=/model_weights/colqwen2.5-v0.2
JINA_API_KEY=sk-xxx
EMBEDDING_IMAGE_DPI=200

# model-server .env
COLBERT_MODEL_PATH=/model_weights/colqwen2.5-v0.2
CUDA_VISIBLE_DEVICES=0
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

---

## 🔍 Step 3: Vector Storage

**File**: `backend/app/db/milvus.py`

### Collection Schema
```python
schema = {
    "fields": [
        {
            "name": "pk",
            "datatype": INT64,
            "is_primary": True,
            "auto_id": True
        },
        {
            "name": "vector",
            "datatype": FLOAT_VECTOR,
            "dim": 128  # ColBERT dimension
        },
        {
            "name": "image_id",
            "datatype": VARCHAR,
            "max_length": 65535
        },
        {
            "name": "page_number",
            "datatype": INT64
        },
        {
            "name": "file_id",
            "datatype": VARCHAR,
            "max_length": 65535
        },
        {
            "name": "chunk_index",
            "datatype": INT64
        }
    ]
}
```

### Index Configuration (HNSW)
```python
index_params = {
    "index_type": "HNSW",
    "metric_type": "IP",  # Inner Product (ColBERT optimized)
    "params": {
        "M": 32,              # Max connections per node
        "efConstruction": 500 # Build time parameter
    }
}
```

**Why HNSW + IP?**
- HNSW: Hierarchical graph for fast semantic search
- M=32: Balance between speed and accuracy
- efConstruction=500: Higher = better quality, slower build
- IP metric: Optimized for normalized embeddings (ColBERT)

### Insertion Flow
```python
# In kafka_consumer
async def process_embedding_task():
    1. Fetch images from MinIO
    2. Get embeddings via get_embedding.py
    3. Insert into Milvus:
       insert_data = {
           "vector": embeddings,      # [128, 128, ...]
           "image_id": ["img_1", ...],
           "page_number": [1, 2, ...],
           "file_id": ["file_1", ...],
           "chunk_index": [0, 1, ...]
       }
       milvus.insert(collection_name, insert_data)
    4. Update MongoDB metadata
    5. Update Redis progress
```

---

## 🎯 Step 4: Query & Search

**RAG Search Flow**:

### Query Embedding
```python
# User query → embedding
user_query = "What is the project scope?"
query_embeddings = await get_embeddings_from_httpx(
    data=[user_query],
    endpoint="embed_text",
    embedding_model="local_colqwen"
)  # Returns [[0.1, 0.2, ..., -0.3]]
```

### Vector Search
```python
# Search Milvus for top-k similar images
search_results = milvus.search(
    collection_name="colqwen_temp_kdb_123",
    data=query_embeddings,  # [[0.1, 0.2, ...]]
    topk=10,
    output_fields=["image_id", "page_number", "file_id"]
)
# Returns: [
#   {"id": 1, "vector": [...], "image_id": "img_1", "page_number": 1, "file_id": "file_1"},
#   {"id": 2, "vector": [...], "image_id": "img_2", "page_number": 2, "file_id": "file_1"},
#   ...
# ]
```

### Reranking (MaxSim)
```python
# MaxSim: Token-to-token similarity for precision
# Only keep top results after second-stage ranking

def maxsim_rerank(query_emb, doc_embs, topk=5):
    """
    ColBERT MaxSim: max token similarity
    More precise than single vector
    """
    scores = []
    for doc_emb in doc_embs:
        # doc_emb: [128] (final embedding)
        # query_emb: [128]
        maxsim_score = max(
            dot_product(query_token, doc_emb)
            for query_token in query_tokens
        )
        scores.append(maxsim_score)
    
    return argsort(scores)[:topk]
```

### Context Assembly
```python
# Fetch context from MongoDB & MinIO
context_list = []
for search_result in reranked_results[:5]:
    image_id = search_result["image_id"]
    page_number = search_result["page_number"]
    
    # Get image from MinIO
    image_base64 = await async_minio_manager.download_image_and_convert_to_base64(image_id)
    
    # Add to context
    context_list.append({
        "source": f"Page {page_number}",
        "image": image_base64,
        "similarity": search_result["similarity_score"]
    })

# Send to LLM with context
response = await llm.chat(
    messages=[
        {"role": "user", "content": user_query},
        {"role": "context", "images": context_list}
    ]
)
```

---

## 📊 Embedding Pipeline Metrics

### Throughput Benchmarks

| Model | Config | Input | Throughput |
|-------|--------|-------|-----------|
| ColQwen 2.5 | 4-bit, RTX 4090 | Images | 1.67 img/s |
| ColQwen 2.5 | 4-bit, A100 | Images | 3.2 img/s |
| Jina V4 | API | Images | 0.5 img/s |
| Jina V4 | API (batch=32) | Images | 2.0 img/s |

### Memory Usage

| Model | Quantization | Memory |
|-------|--------------|--------|
| ColQwen 2.5 | 4-bit NF4 | 22GB |
| ColQwen 2.5 | FP16 | 42GB |
| ColQwen 2.5 | BF16 | 42GB |
| Jina V4 | N/A (API) | 0 (cloud) |

### Vector Dimensions

| Model | Dimension | Index Size (1M vectors) |
|-------|-----------|------------------------|
| ColQwen 2.5 | 128 | ~500MB (HNSW) |
| Jina V4 | 768 | ~3GB (HNSW) |

### Latency Breakdown (per document)

```
Document Upload
├─ File upload: 100ms (network)
├─ Convert to images: 2-10s (PDF processing)
├─ Embedding generation:
│  ├─ Local ColBERT: 600ms/image
│  └─ Jina API: 1-2s/batch
├─ Vector insertion: 100ms (Milvus)
└─ Metadata update: 50ms (MongoDB)

Total: 2-15 seconds per document (local)
       5-20 seconds per document (cloud API)

Query
├─ Query embedding: 100ms
├─ Vector search: 50ms (HNSW k=10)
├─ Reranking: 200ms (MaxSim)
├─ Context fetch: 300ms (MinIO + MongoDB)
└─ LLM inference: 2-5s

Total: 3-6 seconds end-to-end
```

---

## 🔧 Configuration Examples

### Development (ColBERT Local)
```bash
EMBEDDING_MODEL=local_colqwen
COLBERT_MODEL_PATH=/model_weights/colqwen2.5-v0.2
EMBEDDING_IMAGE_DPI=200
MILVUS_URI=http://localhost:19530
```

### Production (Jina Cloud)
```bash
EMBEDDING_MODEL=jina_embeddings_v4
JINA_API_KEY=sk-xxx
EMBEDDING_IMAGE_DPI=200
MILVUS_URI=http://milvus.prod.internal:19530
```

### High Volume (ColBERT + GPU Farm)
```bash
EMBEDDING_MODEL=local_colqwen
COLBERT_MODEL_PATH=/model_weights/colqwen2.5-v0.2
EMBEDDING_IMAGE_DPI=150  # Lower quality, faster
UNOSERVER_INSTANCES=8
KAFKA_PARTITIONS_NUMBER=16
```

---

## 🎯 Key Implementation Files

| File | Purpose |
|------|---------|
| `backend/app/rag/convert_file.py` | PDF/DOCX → Images conversion |
| `backend/app/rag/get_embedding.py` | Embedding request routing |
| `model-server/colbert_service.py` | ColBERT model service |
| `model-server/model_server.py` | FastAPI wrapper for embeddings |
| `backend/app/db/milvus.py` | Vector DB operations |
| `backend/app/utils/kafka_producer.py` | Async task queuing |
| `backend/app/rag/llm_service.py` | LLM integration with context |

---

## 📈 Performance Tuning

### Speed Optimization
```python
# Reduce DPI for faster processing
EMBEDDING_IMAGE_DPI=150  # vs 200

# Batch processing
UNOSERVER_INSTANCES=4    # Parallel conversion

# Milvus search width
ef_search=32  # Lower = faster, less accurate
```

### Quality Optimization
```python
# Higher DPI for better embeddings
EMBEDDING_IMAGE_DPI=300

# Stricter reranking
topk_initial=50   # Search more
topk_rerank=10    # Rerank stricter

# Milvus index quality
M=64              # More connections
efConstruction=1000  # Better index quality
```

### Memory Optimization
```python
# Streaming instead of batch loading
batch_size=4  # Process fewer images at once

# Reduce pool sizes
MONGODB_POOL_SIZE=10
DB_POOL_SIZE=5

# 8-bit quantization (experimental)
bnb_4bit_quant_type="fp4"
```

---

## 🚀 Scaling Strategy

### Horizontal Scaling (Add Hardware)
1. **Document Processing**: Add UNO instances (UNOSERVER_INSTANCES)
2. **Embedding Generation**: Add GPU workers (multiple model-server replicas)
3. **Vector Storage**: Scale Milvus (cluster mode)
4. **Kafka**: Increase partitions (KAFKA_PARTITIONS_NUMBER)

### Vertical Scaling (Upgrade Hardware)
1. **GPU Upgrade**: RTX 4090 → H100 (3x faster embeddings)
2. **CPU Upgrade**: More cores for parallel document conversion
3. **Memory Upgrade**: Larger batch sizes

### Hybrid Approach
```
High Volume:
├─ Local ColBERT for 80% (cost-effective)
└─ Jina API for 20% (burst capacity)

Fallback:
├─ Primary: Local ColBERT
└─ Fallback: Jina API (if GPU down)
```

---

## 📝 Known Limitations

| Limitation | Impact | Workaround |
|-----------|--------|-----------|
| 128-dim vector | Lower precision | Use Jina (768-dim) |
| Single GPU | Max 1.67 img/s | Add GPU workers |
| DPI <150 | Image quality loss | Use higher DPI for small docs |
| HNSW memory | Linear with dataset | Use product quantization |
| Presearch overhead | 50-200ms per query | Batch queries |

---

**Related**: See [CONFIGURATION.md](./CONFIGURATION.md) for embedding settings
