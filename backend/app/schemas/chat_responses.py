from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ConversationCreateResponse(BaseModel):
    status: str
    conversation_id: str = None

class ConversationRenameResponse(BaseModel):
    status: str
    message: str = None

class ConversationUploadResponse(BaseModel):
    task_id: str
    knowledge_db_id: str
    files: List[Dict[str, Any]]

class StatusResponse(BaseModel):
    status: str
    message: Optional[str] = None