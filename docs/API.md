# LAYRA API Documentation

**Version**: 2.0.0  
**Base URL**: `http://localhost:8090/api/v1`  
**Last Updated**: 2026-01-23  

---

## Table of Contents

1. [Authentication](#authentication)
2. [Chat & Conversations](#chat--conversations)
3. [File Management](#file-management)
4. [Workflows](#workflows)
5. [Model Configuration](#model-configuration)
6. [Chatflows](#chatflows)
7. [Server-Sent Events (SSE)](#server-sent-events-sse)
8. [Health Check](#health-check)

---

## Authentication

All endpoints (except `/auth/login` and `/auth/register`) require a valid JWT token in the `Authorization` header:

```bash
Authorization: Bearer <your_jwt_token>
```

### Login

**Endpoint**: `POST /auth/login`

**Description**: Authenticate user with credentials

**Request**:
```json
{
  "username": "john_doe",
  "password": "secure_password"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 11520
}
```

**Error** (401 Unauthorized):
```json
{
  "detail": "Invalid credentials"
}
```

---

### Register

**Endpoint**: `POST /auth/register`

**Description**: Create a new user account

**Request**:
```json
{
  "username": "jane_doe",
  "email": "jane@example.com",
  "password": "secure_password"
}
```

**Response** (200 OK):
```json
{
  "id": "usr_123456",
  "username": "jane_doe",
  "email": "jane@example.com",
  "password_migration_required": false
}
```

**Error** (400 Bad Request):
```json
{
  "detail": "User already exists"
}
```

---

### Verify Token

**Endpoint**: `GET /auth/verify-token`

**Description**: Verify JWT token validity

**Headers**:
```
Authorization: Bearer <your_jwt_token>
```

**Response** (200 OK):
```json
{
  "username": "john_doe",
  "exp": 1674259200,
  "iat": 1674172800
}
```

**Error** (401 Unauthorized):
```json
{
  "detail": "Invalid or expired token"
}
```

---

### Logout

**Endpoint**: `POST /auth/logout`

**Description**: Invalidate current JWT token

**Headers**:
```
Authorization: Bearer <your_jwt_token>
```

**Response** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

---

## Chat & Conversations

### Create Conversation

**Endpoint**: `POST /chat/conversations`

**Description**: Create a new conversation for RAG queries

**Request**:
```json
{
  "conversation_id": "conv_user123_abc",
  "username": "user123",
  "conversation_name": "Project Q Discussion",
  "chat_model_config": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "conversation_id": "conv_user123_abc"
}
```

---

### Rename Conversation

**Endpoint**: `POST /chat/conversations/rename`

**Description**: Rename an existing conversation

**Request**:
```json
{
  "conversation_id": "conv_user123_abc",
  "conversation_new_name": "Updated Topic"
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Conversation renamed"
}
```

---

### Get Conversation

**Endpoint**: `GET /chat/conversations/{conversation_id}`

**Description**: Retrieve full conversation with all turns

**Parameters**:
- `conversation_id` (string, path): Conversation identifier

**Response** (200 OK):
```json
{
  "conversation_id": "conv_user123_abc",
  "conversation_name": "Project Q Discussion",
  "username": "user123",
  "chat_model_config": {
    "model": "gpt-4",
    "temperature": 0.7
  },
  "turns": [
    {
      "message_id": "msg_1",
      "parent_message_id": null,
      "sender_role": "user",
      "message": "What is the project scope?",
      "created_time": "2026-01-23T10:00:00Z",
      "file_ids": ["file_1", "file_2"]
    },
    {
      "message_id": "msg_2",
      "parent_message_id": "msg_1",
      "sender_role": "assistant",
      "message": "Based on the documents...",
      "created_time": "2026-01-23T10:01:00Z"
    }
  ]
}
```

---

### List User Conversations

**Endpoint**: `GET /chat/users/{username}/conversations`

**Description**: Get all conversations for a user

**Parameters**:
- `username` (string, path): Username

**Response** (200 OK):
```json
{
  "total": 5,
  "conversations": [
    {
      "conversation_id": "conv_user123_abc",
      "conversation_name": "Project Q Discussion",
      "created_at": "2026-01-20T10:00:00Z",
      "last_modified": "2026-01-23T15:30:00Z",
      "turn_count": 12
    }
  ]
}
```

---

### Update Conversation Config

**Endpoint**: `POST /chat/conversations/config`

**Description**: Update model configuration for a conversation

**Request**:
```json
{
  "conversation_id": "conv_user123_abc",
  "chat_model_config": {
    "model": "gpt-4",
    "temperature": 0.5,
    "max_tokens": 3000
  }
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Configuration updated"
}
```

---

### Send Chat Message (SSE Stream)

**Endpoint**: `POST /sse/chat`

**Description**: Send a message and receive streamed response via Server-Sent Events

**Request**:
```json
{
  "conversation_id": "conv_user123_abc",
  "message": "Summarize the key findings from the documents",
  "knowledge_db_ids": ["kdb_123"],
  "parent_message_id": "msg_2"
}
```

**Response** (200 OK - Server-Sent Events):
```
data: {"type":"thinking","content":"Analyzing documents..."}
data: {"type":"chunk","content":"The key findings are:"}
data: {"type":"chunk","content":" 1. Performance improved by 20%"}
data: {"type":"complete","message_id":"msg_3"}
```

---

### Delete Conversation

**Endpoint**: `DELETE /chat/conversations/{conversation_id}`

**Description**: Delete a conversation and all associated data

**Parameters**:
- `conversation_id` (string, path): Conversation ID to delete

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Conversation deleted"
}
```

---

### Delete All User Conversations

**Endpoint**: `DELETE /chat/users/{username}/conversations`

**Description**: Delete all conversations for a user

**Parameters**:
- `username` (string, path): Username

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "All conversations deleted"
}
```

---

## File Management

### Upload Files to Conversation

**Endpoint**: `POST /chat/upload/{username}/{conversation_id}`

**Description**: Upload files (PDF, DOCX, TXT, images) for RAG processing

**Parameters**:
- `username` (string, path): Username
- `conversation_id` (string, path): Target conversation
- `files` (file array, form-data): Files to upload

**Response** (200 OK):
```json
{
  "task_id": "task_user123_xyz",
  "knowledge_db_id": "kdb_conv_abc_123",
  "files": [
    {
      "file_id": "file_1",
      "filename": "document.pdf",
      "size": 1024576
    }
  ]
}
```

**cURL Example**:
```bash
curl -X POST \
  "http://localhost:8090/api/v1/chat/upload/user123/conv_abc" \
  -H "Authorization: Bearer <token>" \
  -F "files=@document.pdf" \
  -F "files=@presentation.pptx"
```

---

### Create Knowledge Base

**Endpoint**: `POST /base/knowledge_base`

**Description**: Create a new knowledge base (document collection)

**Request**:
```json
{
  "username": "user123",
  "knowledge_base_name": "Project Documentation",
  "description": "All project-related documents"
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "knowledge_base_id": "kdb_user123_doc",
  "knowledge_base_name": "Project Documentation"
}
```

---

### Rename Knowledge Base

**Endpoint**: `POST /base/knowledge_base/rename`

**Request**:
```json
{
  "knowledge_base_id": "kdb_user123_doc",
  "knowledge_base_new_name": "Updated Project Docs"
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Knowledge base renamed"
}
```

---

### List Knowledge Base Files

**Endpoint**: `POST /base/knowledge_bases/{knowledge_base_id}/files`

**Description**: Get paginated list of files in a knowledge base

**Parameters**:
- `knowledge_base_id` (string, path): Knowledge base ID
- `page` (integer, query, optional): Page number (default: 1)
- `page_size` (integer, query, optional): Items per page (default: 20)

**Response** (200 OK):
```json
{
  "total": 5,
  "page": 1,
  "page_size": 20,
  "files": [
    {
      "file_id": "file_1",
      "filename": "document.pdf",
      "size": 1024576,
      "created_at": "2026-01-20T10:00:00Z",
      "status": "processed"
    }
  ]
}
```

---

### Delete File

**Endpoint**: `DELETE /base/file/{knowledge_base_id}/{file_id}`

**Description**: Delete a file from knowledge base

**Parameters**:
- `knowledge_base_id` (string, path): Knowledge base ID
- `file_id` (string, path): File ID to delete

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "File deleted"
}
```

---

### Bulk Delete Files

**Endpoint**: `DELETE /base/files/bulk-delete`

**Description**: Delete multiple files at once

**Request**:
```json
{
  "file_ids": ["file_1", "file_2", "file_3"],
  "knowledge_base_id": "kdb_123"
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "deleted_count": 3
}
```

---

### Download File (Presigned URL)

**Endpoint**: `POST /base/files/download`

**Description**: Get presigned URL for file download

**Request**:
```json
{
  "file_id": "file_1",
  "knowledge_base_id": "kdb_123"
}
```

**Response** (200 OK):
```json
{
  "url": "http://minio:9000/bucket/file_path?X-Amz-Algorithm=AWS4-HMAC-SHA256&...",
  "expires_in": 3600
}
```

---

### Delete Knowledge Base

**Endpoint**: `DELETE /base/knowledge_base/{knowledge_base_id}`

**Description**: Delete entire knowledge base with all files

**Parameters**:
- `knowledge_base_id` (string, path): Knowledge base to delete

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Knowledge base deleted"
}
```

---

## Workflows

### Execute Workflow

**Endpoint**: `POST /workflow/execute`

**Description**: Execute a workflow with given inputs

**Request**:
```json
{
  "username": "user123",
  "workflow_name": "Data Processing",
  "global_variables": {
    "input_file": "data.csv",
    "threshold": 0.8
  },
  "nodes": [
    {
      "id": "node_1",
      "type": "file_input",
      "config": {"path": "data.csv"}
    },
    {
      "id": "node_2",
      "type": "llm",
      "config": {"model": "gpt-4"}
    }
  ],
  "edges": [
    {"from": "node_1", "to": "node_2"}
  ]
}
```

**Response** (200 OK):
```json
{
  "task_id": "task_user123_workflow_1",
  "status": "running"
}
```

---

### Get Workflow Progress (SSE Stream)

**Endpoint**: `GET /sse/workflow/{username}/{task_id}`

**Description**: Stream workflow execution progress via Server-Sent Events

**Parameters**:
- `username` (string, path): Username
- `task_id` (string, path): Workflow task ID

**Response** (200 OK - Server-Sent Events):
```
data: {"node_id":"node_1","status":"running","progress":0}
data: {"node_id":"node_1","status":"completed","output":{"rows":1000}}
data: {"node_id":"node_2","status":"running","progress":50}
data: {"status":"completed","result":{"summary":"Done"}}
```

---

### Create Workflow

**Endpoint**: `POST /workflow/workflows`

**Description**: Save a workflow template for reuse

**Request**:
```json
{
  "username": "user123",
  "workflow_name": "Data Pipeline",
  "nodes": [...],
  "edges": [...]
}
```

**Response** (201 Created):
```json
{
  "status": "success",
  "workflow_id": "wf_user123_pipeline"
}
```

---

### Get Workflow

**Endpoint**: `GET /workflow/workflows/{workflow_id}`

**Description**: Retrieve workflow definition

**Parameters**:
- `workflow_id` (string, path): Workflow ID

**Response** (200 OK):
```json
{
  "workflow_id": "wf_user123_pipeline",
  "workflow_name": "Data Pipeline",
  "created_at": "2026-01-20T10:00:00Z",
  "nodes": [...],
  "edges": [...]
}
```

---

### List User Workflows

**Endpoint**: `GET /workflow/users/{username}/workflows`

**Description**: Get all workflows for a user

**Parameters**:
- `username` (string, path): Username

**Response** (200 OK):
```json
{
  "total": 3,
  "workflows": [
    {
      "workflow_id": "wf_user123_pipeline",
      "workflow_name": "Data Pipeline",
      "created_at": "2026-01-20T10:00:00Z",
      "last_modified": "2026-01-23T15:00:00Z"
    }
  ]
}
```

---

### Delete Workflow

**Endpoint**: `DELETE /workflow/workflows/{workflow_id}`

**Description**: Delete a saved workflow

**Parameters**:
- `workflow_id` (string, path): Workflow to delete

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Workflow deleted"
}
```

---

### Cancel Workflow Execution

**Endpoint**: `GET /workflow/{username}/{task_id}/cancel`

**Description**: Cancel an executing workflow task

**Parameters**:
- `username` (string, path): Username
- `task_id` (string, path): Task ID to cancel

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Task cancelled"
}
```

---

## Model Configuration

### Create Model Config

**Endpoint**: `POST /config/{username}`

**Description**: Create a model configuration profile

**Request**:
```json
{
  "model_name": "gpt-4-config",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2000,
  "top_p": 0.9,
  "api_key": "sk-..."
}
```

**Response** (201 Created):
```json
{
  "status": "success",
  "model_id": "model_config_123",
  "model_name": "gpt-4-config"
}
```

---

### Get Selected Model

**Endpoint**: `GET /config/{username}/selected`

**Description**: Get currently selected model configuration

**Parameters**:
- `username` (string, path): Username

**Response** (200 OK):
```json
{
  "model_id": "model_config_123",
  "model_name": "gpt-4-config",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2000
}
```

---

### Get All Model Configs

**Endpoint**: `GET /config/{username}/all`

**Description**: List all model configurations for user

**Parameters**:
- `username` (string, path): Username

**Response** (200 OK):
```json
{
  "total": 2,
  "configs": [
    {
      "model_id": "model_config_123",
      "model_name": "gpt-4-config",
      "model": "gpt-4"
    }
  ]
}
```

---

### Select Model

**Endpoint**: `PUT /config/{username}/select-model`

**Description**: Set active model configuration

**Parameters**:
- `username` (string, path): Username

**Request**:
```json
{
  "model_id": "model_config_123"
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "selected_model_id": "model_config_123"
}
```

---

### Update Model Config

**Endpoint**: `PATCH /config/{username}/{model_id}`

**Description**: Update existing model configuration

**Parameters**:
- `username` (string, path): Username
- `model_id` (string, path): Model config ID

**Request**:
```json
{
  "temperature": 0.5,
  "max_tokens": 3000
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Configuration updated"
}
```

---

### Delete Model Config

**Endpoint**: `DELETE /config/{username}/{model_id}`

**Description**: Delete a model configuration

**Parameters**:
- `username` (string, path): Username
- `model_id` (string, path): Model config to delete

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Configuration deleted"
}
```

---

## Chatflows

### Create Chatflow

**Endpoint**: `POST /chatflow/chatflows`

**Description**: Create a chatflow (structured conversation template)

**Request**:
```json
{
  "username": "user123",
  "chatflow_name": "Customer Support",
  "workflow_id": "wf_123",
  "config": {
    "max_turns": 10,
    "system_prompt": "You are a helpful support agent"
  }
}
```

**Response** (201 Created):
```json
{
  "status": "success",
  "chatflow_id": "cf_user123_support"
}
```

---

### Get Chatflow

**Endpoint**: `GET /chatflow/chatflows/{chatflow_id}`

**Description**: Retrieve chatflow details

**Parameters**:
- `chatflow_id` (string, path): Chatflow ID

**Response** (200 OK):
```json
{
  "chatflow_id": "cf_user123_support",
  "chatflow_name": "Customer Support",
  "workflow_id": "wf_123",
  "config": {...},
  "created_at": "2026-01-20T10:00:00Z"
}
```

---

### List Chatflows by Workflow

**Endpoint**: `GET /chatflow/workflow/{workflow_id}/chatflows`

**Description**: Get all chatflows for a workflow

**Parameters**:
- `workflow_id` (string, path): Workflow ID

**Response** (200 OK):
```json
{
  "total": 2,
  "chatflows": [
    {
      "chatflow_id": "cf_user123_support",
      "chatflow_name": "Customer Support"
    }
  ]
}
```

---

### Delete Chatflow

**Endpoint**: `DELETE /chatflow/chatflows/{chatflow_id}`

**Description**: Delete a chatflow

**Parameters**:
- `chatflow_id` (string, path): Chatflow to delete

**Response** (200 OK):
```json
{
  "status": "success",
  "message": "Chatflow deleted"
}
```

---

## Server-Sent Events (SSE)

### Get Task Progress

**Endpoint**: `GET /sse/task/{username}/{task_id}`

**Description**: Stream file processing task progress

**Parameters**:
- `username` (string, path): Username
- `task_id` (string, path): Task ID from upload

**Response** (200 OK - Server-Sent Events):
```
data: {"status":"processing","processed":0,"total":3,"message":"Starting file processing..."}
data: {"status":"processing","processed":1,"total":3,"message":"Processed document.pdf (200 pages)"}
data: {"status":"processing","processed":2,"total":3,"message":"Processed presentation.pptx (50 slides)"}
data: {"status":"completed","processed":3,"total":3,"message":"All files processed"}
```

---

### Test Code Execution

**Endpoint**: `POST /workflow/test_code`

**Description**: Test code execution in workflow node

**Request**:
```json
{
  "code": "return input * 2",
  "inputs": {"input": 5}
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "output": 10,
  "execution_time": 0.05
}
```

---

### Test Condition

**Endpoint**: `POST /workflow/test_condition`

**Description**: Test conditional logic

**Request**:
```json
{
  "condition": "input > 100",
  "inputs": {"input": 150}
}
```

**Response** (200 OK):
```json
{
  "status": "success",
  "result": true
}
```

---

### Single LLM Query (No RAG)

**Endpoint**: `POST /sse/llm/once`

**Description**: Send a prompt to LLM without RAG context

**Request**:
```json
{
  "prompt": "Explain quantum computing in simple terms",
  "model_config": {
    "model": "gpt-4",
    "temperature": 0.7
  }
}
```

**Response** (200 OK - Server-Sent Events):
```
data: {"type":"chunk","content":"Quantum computing is..."}
data: {"type":"chunk","content":" a new technology..."}
data: {"type":"complete"}
```

---

## Health Check

### Health Status

**Endpoint**: `GET /health/check`

**Description**: Check API and service health status

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2026-01-23T16:30:00Z",
  "services": {
    "database": "ok",
    "redis": "ok",
    "minio": "ok",
    "milvus": "ok",
    "kafka": "ok"
  }
}
```

---

## Error Handling

All endpoints follow standard HTTP status codes:

| Status | Meaning | Example |
|--------|---------|---------|
| 200 | Success | Request processed successfully |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 500 | Server Error | Internal error |

---

## Authentication Examples

### Using cURL

```bash
# Login
curl -X POST http://localhost:8090/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"john_doe","password":"pass123"}'

# Use token in request
curl -X GET http://localhost:8090/api/v1/chat/users/john_doe/conversations \
  -H "Authorization: Bearer eyJhbGc..."
```

### Using Python Requests

```python
import requests

# Login
response = requests.post(
    "http://localhost:8090/api/v1/auth/login",
    json={"username": "john_doe", "password": "pass123"}
)
token = response.json()["access_token"]

# Make authenticated request
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:8090/api/v1/chat/users/john_doe/conversations",
    headers=headers
)
```

---

## Rate Limiting

- Default: 100 requests per minute per user
- Burst: 200 requests per 10 seconds
- Rate limit headers included in all responses:
  - `X-RateLimit-Limit`: Total requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Timestamp when limit resets

---

## WebSocket Connections

For real-time chat:

```bash
ws://localhost:8090/api/v1/ws/{conversation_id}?token={jwt_token}
```

Send JSON messages:
```json
{"type": "message", "content": "Your question here"}
```

Receive JSON responses:
```json
{"type": "response", "content": "AI response here", "timestamp": "..."}
```

---

**For more information, see:**
- [DATABASE.md](./DATABASE.md) - Database schema
- [CONFIGURATION.md](./CONFIGURATION.md) - Configuration options
