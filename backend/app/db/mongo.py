from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.logging import logger
import asyncio

class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None

    async def _create_indexes(self):
        """创建所有必要的索引（唯一索引+普通索引）"""
        try:
            # 知识库集合索引
            await self.db.knowledge_bases.create_index(
                [("knowledge_base_id", 1)],
                unique=True,
                name="unique_kb_id",
            )
            await self.db.knowledge_bases.create_index(
                [("username", 1), ("is_delete", 1)],
                name="user_kb_query",
            )
            await self.db.knowledge_bases.create_index(
                [("files.filename", 1)],
                name="kb_files_filename",
            )

            # 模型配置索引
            await self.db.model_config.create_index(
                [("username", 1)],
                unique=True,
                name="unique_config_id",
            )

            # 文件集合索引
            await self.db.files.create_index(
                [("file_id", 1)],
                unique=True,
                name="unique_file_id",
            )
            await self.db.files.create_index(
                [("knowledge_db_id", 1)],
                name="kb_file_query",
            )
            await self.db.files.create_index(
                [("filename", 1)],
                name="filename_search",
            )

            # 对话集合索引
            await self.db.conversations.create_index(
                [("conversation_id", 1)],
                unique=True,
                name="unique_conversation_id",
            )
            await self.db.conversations.create_index(
                [("username", 1), ("last_modify_at", -1)],
                name="user_conversations",
            )

            # chatflow集合索引
            await self.db.chatflows.create_index(
                [("chatflow_id", 1)],
                unique=True,
                name="unique_chatflow_id",
            )
            await self.db.chatflows.create_index(
                [("workflow", 1), ("last_modify_at", -1)],
                name="workflow_chatflows",
            )

            # workflow索引
            await self.db.workflows.create_index(
                [("username", 1), ("workflow_id", 1)],
                unique=True,
                name="username_workflow_id_unique",
            )
            await self.db.workflows.create_index(
                [("username", 1), ("last_modify_at", -1)], 
                name="user_workflows"
            )

            # node索引
            await self.db.nodes.create_index([("username", 1)], unique=True)

            logger.info("MongoDB 索引创建完成")
        except Exception as e:
            logger.error(f"索引创建失败: {str(e)}")
            raise

    async def connect(self):
        self.client = AsyncIOMotorClient(
            f"mongodb://{settings.mongodb_root_username}:{settings.mongodb_root_password}@{settings.mongodb_url}",
            maxPoolSize=settings.mongodb_pool_size,
            minPoolSize=settings.mongodb_min_pool_size,
        )
        self.db = self.client[settings.mongodb_db]
        await self._create_indexes()

    async def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()

mongodb = MongoDB()

async def get_mongo():
    if mongodb.db is None:
        await mongodb.connect()
    return mongodb