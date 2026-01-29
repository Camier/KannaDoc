from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.mongo import mongodb
from .model_config import ModelConfigRepository
from .file import FileRepository
from .knowledge_base import KnowledgeBaseRepository
from .conversation import ConversationRepository
from .chatflow import ChatflowRepository
from .workflow import WorkflowRepository, NodeRepository

class RepositoryManager:
    """Manages all repositories and their dependencies."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self._model_config: Optional[ModelConfigRepository] = None
        self._file: Optional[FileRepository] = None
        self._knowledge_base: Optional[KnowledgeBaseRepository] = None
        self._conversation: Optional[ConversationRepository] = None
        self._chatflow: Optional[ChatflowRepository] = None
        self._workflow: Optional[WorkflowRepository] = None
        self._node: Optional[NodeRepository] = None

    @property
    def model_config(self) -> ModelConfigRepository:
        if not self._model_config:
            self._model_config = ModelConfigRepository(self.db)
        return self._model_config

    @property
    def file(self) -> FileRepository:
        if not self._file:
            self._file = FileRepository(self.db)
        return self._file

    @property
    def knowledge_base(self) -> KnowledgeBaseRepository:
        if not self._knowledge_base:
            # Inject file_repo for cascade delete
            self._knowledge_base = KnowledgeBaseRepository(
                self.db,
                file_repo=self.file
            )
        return self._knowledge_base

    @property
    def conversation(self) -> ConversationRepository:
        if not self._conversation:
            # Inject knowledge_base_repo for cascade delete
            self._conversation = ConversationRepository(
                self.db,
                knowledge_base_repo=self.knowledge_base
            )
        return self._conversation

    @property
    def chatflow(self) -> ChatflowRepository:
        if not self._chatflow:
            # Inject knowledge_base_repo for cascade delete
            self._chatflow = ChatflowRepository(
                self.db,
                knowledge_base_repo=self.knowledge_base
            )
        return self._chatflow

    @property
    def workflow(self) -> WorkflowRepository:
        if not self._workflow:
            # Inject chatflow_repo for cascade delete
            self._workflow = WorkflowRepository(
                self.db,
                chatflow_repo=self.chatflow
            )
        return self._workflow

    @property
    def node(self) -> NodeRepository:
        if not self._node:
            self._node = NodeRepository(self.db)
        return self._node

async def get_repository_manager() -> RepositoryManager:
    """Dependency provider for RepositoryManager"""
    if mongodb.db is None:
        await mongodb.connect()
    return RepositoryManager(mongodb.db)
