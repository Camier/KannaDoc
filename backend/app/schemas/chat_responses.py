"""Response schemas for chat endpoints."""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any


class ConversationCreateResponse(BaseModel):
    """Response for create conversation endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "conversation_id": "conv_12345"
            }
        }
    )
    status: str
    conversation_id: str


class ConversationRenameResponse(BaseModel):
    """Response for rename conversation endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Conversation renamed"
            }
        }
    )
    status: str
    message: str = "Conversation renamed"


class UploadFileInfo(BaseModel):
    """Information about uploaded file."""
    file_id: str
    filename: str
    size: int


class ConversationUploadResponse(BaseModel):
    """Response for upload files endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "task_123",
                "knowledge_db_id": "kdb_456",
                "files": [
                    {
                        "file_id": "file_1",
                        "filename": "document.pdf",
                        "size": 1024
                    }
                ]
            }
        }
    )
    task_id: str
    knowledge_db_id: str
    files: List[UploadFileInfo]


class MessageResponse(BaseModel):
    """Generic message response."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Operation completed"
            }
        }
    )
    status: str
    message: Optional[str] = None
