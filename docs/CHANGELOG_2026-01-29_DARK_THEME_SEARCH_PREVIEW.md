# LAYRA Session: Dark Theme + Search Preview Feature

**Date**: 2026-01-29
**Session Focus**: UI/UX improvements and RAG debugging tools

---

## Changes Summary

### 1. Dark Theme Implementation

**Problem**: White backgrounds with white text caused readability issues.

**Solution**: Replaced `bg-white` with `bg-gray-800` across 36 TSX files (63 occurrences).

**Files Modified**:
- `frontend/src/components/AiChat/*.tsx` - Chat interface components
- `frontend/src/components/KnowledgeBase/*.tsx` - KB management
- `frontend/src/components/Workflow/*.tsx` - Workflow editor
- `frontend/src/components/NavbarComponents/*.tsx` - Navigation
- `frontend/src/components/shared/*.tsx` - Shared components
- `frontend/src/app/[locale]/*.tsx` - Page components

**Color Mapping**:
| Original | Replacement | Usage |
|----------|-------------|-------|
| `bg-white` | `bg-gray-800` | Main containers |
| `bg-white/10` | `bg-gray-900/80` | Semi-transparent overlays |
| `bg-white/30` | `bg-gray-800/50` | Light overlays |
| `text-gray-700` | `text-gray-300` | Body text |
| `text-black` | `text-white` | High contrast text |
| `border-gray-200` | `border-gray-600` | Borders |

**Preserved**:
- `after:bg-white` / `before:bg-white` in CustomNode.tsx (decorative elements)

---

### 2. Search Preview Feature

**Purpose**: Debug RAG quality by viewing raw Milvus search results without LLM generation.

#### Backend Endpoint

**File**: `backend/app/api/endpoints/knowledge_base.py` (NEW)

**Endpoint**: `POST /api/v1/kb/knowledge-base/{kb_id}/search-preview`

**Request**:
```json
{
  "query": "string",
  "top_k": 5
}
```

**Response**:
```json
{
  "query": "string",
  "results": [
    {
      "score": 0.85,
      "page_number": 3,
      "file_id": "uuid",
      "file_name": "document.pdf",
      "minio_url": "http://..."
    }
  ],
  "total": 5
}
```

**Dependencies Added**:
- `backend/app/db/repositories/file.py`: Added `get_files_by_ids()` method
- `backend/app/api/__init__.py`: Router registration

#### Frontend Component

**File**: `frontend/src/components/KnowledgeBase/SearchPreviewPanel.tsx` (NEW)

**Features**:
- Query input with Enter key support
- Top K selector (5/10/20)
- Results table with score color coding:
  - Green: score > 0.8
  - Yellow: score > 0.6
  - Red: score <= 0.6
- Image viewer modal for page previews
- Dark theme styling

**Integration**: Button added to `KnowledgeBaseDetails.tsx` header.

**API Client**: Extended `frontend/src/lib/api/knowledgeBaseApi.ts` with:
- `searchPreview()` function
- `SearchPreviewResult` interface
- `SearchPreviewResponse` interface

---

### 3. Infrastructure Fixes

**Problem**: System minio service occupies port 9000, preventing layra-minio startup.

**Solution**: Changed docker port mapping for layra-minio.

**Files Modified**:
- `docker-compose.yml`: Port mapping `9000:9000` → `9080:9000`
- `.env`: `MINIO_PUBLIC_URL=http://localhost:9080`

**Note**: Internal container port remains 9000; only host mapping changed.

---

## Testing

### Backend Endpoint
```bash
# Health check
curl http://localhost:8090/api/v1/health/check
# Returns: {"status":"UP","details":"All systems operational"}

# Search preview (requires auth)
curl -X POST "http://localhost:8090/api/v1/kb/knowledge-base/{kb_id}/search-preview" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"query": "methodology", "top_k": 5}'
```

### Frontend
1. Navigate to http://localhost:8090/knowledge-base
2. Select a knowledge base
3. Click "Search Preview" button
4. Enter query and view results

---

## Service Status

All services running after changes:
- `layra-backend` - Healthy (port 8000 internal)
- `layra-frontend` - Running (Next.js)
- `layra-nginx` - Running (port 8090)
- `layra-minio` - Healthy (port 9080 host → 9000 container)

---

## Next Steps

1. Add i18n translations for SearchPreview component
2. Add min_score filter to search preview
3. Export search results to CSV
4. Performance benchmarking for large KBs
