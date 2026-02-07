"""
Thesis RAG References (UI) — Source-Of-Truth Note

This document explains how "References" are produced (backend) and rendered (frontend)
for the thesis RAG flow, and captures the fixes that made references reliably visible.

Scope:
- Thesis AI chat UI ("View references" toggle and reference cards)
- SSE `file_used` payloads emitted by the backend

Non-goals:
- Milvus migration (host -> docker) and broader SSOT docs; handled elsewhere.
"""

# Thesis RAG References (UI)

## Overview

In the thesis stack, retrieval evidence is surfaced to the UI as a list of **page-level**
references (grouped by `(file_id, page_number)`), even though the underlying Milvus patch
collection is patch-level (ColPali/ColQwen) where `image_id` is patch-level.

End-to-end shape:

1. Backend runs retrieval (`MilvusManager.search()`).
2. Backend streams SSE events for chat:
   - emits `file_used` early (before provider LLM generation)
   - then streams assistant content tokens
3. Frontend converts `file_used[]` entries into `Message{type:"baseFile"}` items and renders:
   - a single toggle ("View references") to show/hide the reference list
   - a list of reference cards (preview image, filename, score, base name)

## Backend: `file_used` Emission

Backend output contract:
- SSE chat endpoint returns a `file_used` event containing a list of references.
- Each reference should contain:
  - `knowledge_db_id`
  - `file_name`
  - `file_url` (PDF link)
  - `image_url` (page preview link)
  - `score`
  - and (thesis) optionally `file_id`, `page_number`, `text_preview`

Notes:
- Thesis uses page-level grouping by `(file_id, page_number)`; `image_id` is patch-level and
  must not be used as a page identity.
- To avoid "2 sources only" accidents from legacy UI defaults, thesis retrieval modes
  `sparse_then_rerank` / `dual_then_rerank` normalize `top_K` with a conservative minimum
  (see `backend/app/core/rag/retrieval_params.py`).

Related commits:
- `dc1af75` restores reference emission even when Mongo metadata is missing by using thesis-only
  `thesis/page-image` and `thesis/pdf` URLs when necessary.
- `e9b14c3` consolidates retrieval param normalization and thesis URL building.

## Frontend: Stable "View References" Toggle

Previous behavior (fragile):
- The UI only rendered the toggle when:
  - `message.type === "baseFile"`
  - and `message.content === "image_0"`
  - and `message.messageId` existed
- This implicitly assumed the first reference always had `content="image_0"`.
  If ordering/content changed, the toggle disappeared even though references existed.

Current behavior (explicit and stable):
- When mapping `file_used[] -> baseFile` messages, the first entry gets:
  - `isFirstReference: index === 0`
- The UI renders the toggle when:
  - `message.type === "baseFile"`
  - and `message.messageId` exists
  - and `message.isFirstReference === true`
  - (with a fallback to the legacy `content === "image_0"` for older stored histories)

Related commit:
- `a2f7917 fix(ai-chat): make references toggle stable (no more image_0 sentinel)`

Files:
- `frontend/src/app/[locale]/ai-chat/page.tsx`
- `frontend/src/components/AiChat/ChatMessage.tsx`
- `frontend/src/components/Workflow/ChatflowHistory.tsx`
- `frontend/src/types/types.ts`

## Validation (No Mocks)

This stack is validated with **live integration smoke tests** (real services, no simulated
Milvus/Mongo/embeddings):
- `backend/tests/integration/test_thesis_rag_pipeline_live.py`
- `backend/scripts/smoke_test_thesis_rag.py`

Expected signals for a broad query:
- `search-preview` returns `top_k` results (thesis default: 50) and many distinct `file_id`
- SSE chat returns `file_used len ~= top_k` (e.g. 50) and many distinct files
- UI shows a single "View references" toggle and renders the reference cards correctly

