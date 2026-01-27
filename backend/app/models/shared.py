"""Shared Pydantic models used across multiple domains."""
from pydantic import BaseModel


class TurnOutput(BaseModel):
    """Output model for a conversation/chatflow turn."""
    message_id: str
    parent_message_id: str
    user_message: dict
    temp_db: str
    ai_message: dict
    file_used: list
    user_file: list
    status: str
    timestamp: str
    total_token: int
    completion_tokens: int
    prompt_tokens: int


class UserMessage(BaseModel):
    """User message in a conversation or workflow.

    BREAKING CHANGE: Field name standardized from 'temp_db' to 'temp_db_id'
    to match workflow.py convention. All database references updated.
    """
    conversation_id: str
    parent_id: str
    user_message: str
    temp_db_id: str  # Standardized field name (was 'temp_db' in conversation.py)
