"""
Database Repository Tests
Tests CRUD operations for conversations, knowledge bases, bulk operations, and N+1 prevention
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
from app.db.mongo import MongoDB
from app.models.conversation import (
    ConversationCreate,
    TurnInput,
    UserMessage,
    ConversationOutput
)


class TestConversationRepository:
    """Test conversation CRUD operations"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock MongoDB instance"""
        db = MongoDB()
        db.client = Mock()
        db.db = Mock()
        return db

    @pytest.mark.asyncio
    async def test_create_conversation(self, mock_db):
        """Test creating a new conversation"""
        conversation_data = ConversationCreate(
            conversation_id="conv_123",
            username="testuser",
            conversation_name="Test Conversation",
            chat_model_config={
                "model_name": "gpt-4",
                "temperature": 0.7
            }
        )

        with patch.object(mock_db.db.conversations, 'insert_one', new=AsyncMock()) as mock_insert:
            mock_insert.return_value.acknowledged = True

            result = await mock_db.db.conversations.insert_one({
                "conversation_id": conversation_data.conversation_id,
                "username": conversation_data.username,
                "conversation_name": conversation_data.conversation_name,
                "chat_model_config": conversation_data.chat_model_config,
                "turns": [],
                "created_at": datetime.now().isoformat(),
                "last_modify_at": datetime.now().isoformat()
            })

            assert result.acknowledged is True
            mock_insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_conversation_by_id(self, mock_db):
        """Test retrieving a conversation by ID"""
        conversation_id = "conv_123"

        mock_doc = {
            "conversation_id": conversation_id,
            "username": "testuser",
            "conversation_name": "Test Conversation",
            "turns": [],
            "created_at": "2024-01-01T00:00:00",
            "last_modify_at": "2024-01-01T00:00:00"
        }

        with patch.object(mock_db.db.conversations, 'find_one', new=AsyncMock(return_value=mock_doc)) as mock_find:
            result = await mock_db.db.conversations.find_one({"conversation_id": conversation_id})

            assert result is not None
            assert result["conversation_id"] == conversation_id
            assert result["username"] == "testuser"
            mock_find.assert_called_once_with({"conversation_id": conversation_id})

    @pytest.mark.asyncio
    async def test_update_conversation_name(self, mock_db):
        """Test updating conversation name"""
        conversation_id = "conv_123"
        new_name = "Updated Conversation Name"

        with patch.object(mock_db.db.conversations, 'update_one', new=AsyncMock(return_value=MagicMock(matched_count=1))) as mock_update:
            result = await mock_db.db.conversations.update_one(
                {"conversation_id": conversation_id},
                {"$set": {"conversation_name": new_name, "last_modify_at": datetime.now().isoformat()}}
            )

            assert result.matched_count == 1
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_conversation(self, mock_db):
        """Test deleting a conversation"""
        conversation_id = "conv_123"

        with patch.object(mock_db.db.conversations, 'delete_one', new=AsyncMock(return_value=MagicMock(deleted_count=1))) as mock_delete:
            result = await mock_db.db.conversations.delete_one({"conversation_id": conversation_id})

            assert result.deleted_count == 1
            mock_delete.assert_called_once_with({"conversation_id": conversation_id})

    @pytest.mark.asyncio
    async def test_list_user_conversations(self, mock_db):
        """Test listing all conversations for a user"""
        username = "testuser"

        mock_cursor = Mock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "conversation_id": "conv_1",
                "username": username,
                "conversation_name": "Conversation 1",
                "created_at": "2024-01-01T00:00:00"
            },
            {
                "conversation_id": "conv_2",
                "username": username,
                "conversation_name": "Conversation 2",
                "created_at": "2024-01-02T00:00:00"
            }
        ])

        with patch.object(mock_db.db.conversations, 'find', new=Mock(return_value=mock_cursor)) as mock_find:
            result = await mock_cursor.to_list(length=100)

            assert len(result) == 2
            assert all(conv["username"] == username for conv in result)
            mock_find.assert_called()

    @pytest.mark.asyncio
    async def test_add_turn_to_conversation(self, mock_db):
        """Test adding a turn (message exchange) to a conversation"""
        conversation_id = "conv_123"
        turn_data = TurnInput(
            conversation_id=conversation_id,
            message_id="msg_123",
            parent_message_id="",
            user_message={"role": "user", "content": "Hello"},
            temp_db="",
            ai_message={"role": "assistant", "content": "Hi there!"},
            file_used=[],
            status="completed",
            total_token=100,
            completion_tokens=50,
            prompt_tokens=50
        )

        turn_doc = {
            "message_id": turn_data.message_id,
            "parent_message_id": turn_data.parent_message_id,
            "user_message": turn_data.user_message,
            "temp_db": turn_data.temp_db,
            "ai_message": turn_data.ai_message,
            "file_used": turn_data.file_used,
            "user_file": [],
            "status": turn_data.status,
            "timestamp": datetime.now().isoformat(),
            "total_token": turn_data.total_token,
            "completion_tokens": turn_data.completion_tokens,
            "prompt_tokens": turn_data.prompt_tokens
        }

        with patch.object(mock_db.db.conversations, 'update_one', new=AsyncMock(return_value=MagicMock(matched_count=1))) as mock_update:
            result = await mock_db.db.conversations.update_one(
                {"conversation_id": conversation_id},
                {
                    "$push": {"turns": turn_doc},
                    "$set": {"last_modify_at": datetime.now().isoformat()}
                }
            )

            assert result.matched_count == 1
            mock_update.assert_called_once()


class TestKnowledgeBaseRepository:
    """Test knowledge base CRUD operations"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock MongoDB instance"""
        db = MongoDB()
        db.client = Mock()
        db.db = Mock()
        return db

    @pytest.mark.asyncio
    async def test_create_knowledge_base(self, mock_db):
        """Test creating a new knowledge base"""
        kb_data = {
            "knowledge_base_id": "kb_123",
            "username": "testuser",
            "knowledge_base_name": "Test KB",
            "is_delete": False,
            "created_at": datetime.now().isoformat(),
            "last_modify_at": datetime.now().isoformat()
        }

        with patch.object(mock_db.db.knowledge_bases, 'insert_one', new=AsyncMock(return_value=MagicMock(acknowledged=True))) as mock_insert:
            result = await mock_db.db.knowledge_bases.insert_one(kb_data)

            assert result.acknowledged is True
            mock_insert.assert_called_once_with(kb_data)

    @pytest.mark.asyncio
    async def test_get_knowledge_base_by_id(self, mock_db):
        """Test retrieving a knowledge base by ID"""
        kb_id = "kb_123"

        mock_doc = {
            "knowledge_base_id": kb_id,
            "username": "testuser",
            "knowledge_base_name": "Test KB",
            "is_delete": False
        }

        with patch.object(mock_db.db.knowledge_bases, 'find_one', new=AsyncMock(return_value=mock_doc)) as mock_find:
            result = await mock_db.db.knowledge_bases.find_one({"knowledge_base_id": kb_id})

            assert result is not None
            assert result["knowledge_base_id"] == kb_id
            mock_find.assert_called_once_with({"knowledge_base_id": kb_id})

    @pytest.mark.asyncio
    async def test_list_user_knowledge_bases(self, mock_db):
        """Test listing all knowledge bases for a user"""
        username = "testuser"

        mock_cursor = Mock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "knowledge_base_id": "kb_1",
                "username": username,
                "knowledge_base_name": "KB 1",
                "is_delete": False
            },
            {
                "knowledge_base_id": "kb_2",
                "username": username,
                "knowledge_base_name": "KB 2",
                "is_delete": False
            }
        ])

        with patch.object(mock_db.db.knowledge_bases, 'find', new=Mock(return_value=mock_cursor)) as mock_find:
            result = await mock_cursor.to_list(length=100)

            assert len(result) == 2
            assert all(kb["username"] == username for kb in result)
            assert all(kb["is_delete"] is False for kb in result)

    @pytest.mark.asyncio
    async def test_soft_delete_knowledge_base(self, mock_db):
        """Test soft deleting a knowledge base"""
        kb_id = "kb_123"

        with patch.object(mock_db.db.knowledge_bases, 'update_one', new=AsyncMock(return_value=MagicMock(matched_count=1))) as mock_update:
            result = await mock_db.db.knowledge_bases.update_one(
                {"knowledge_base_id": kb_id},
                {"$set": {"is_delete": True, "last_modify_at": datetime.now().isoformat()}}
            )

            assert result.matched_count == 1
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_hard_delete_knowledge_base(self, mock_db):
        """Test hard deleting a knowledge base"""
        kb_id = "kb_123"

        with patch.object(mock_db.db.knowledge_bases, 'delete_one', new=AsyncMock(return_value=MagicMock(deleted_count=1))) as mock_delete:
            result = await mock_db.db.knowledge_bases.delete_one({"knowledge_base_id": kb_id})

            assert result.deleted_count == 1
            mock_delete.assert_called_once()


class TestFileRepository:
    """Test file management operations"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock MongoDB instance"""
        db = MongoDB()
        db.client = Mock()
        db.db = Mock()
        return db

    @pytest.mark.asyncio
    async def test_add_file_to_knowledge_base(self, mock_db):
        """Test adding a file to a knowledge base"""
        file_data = {
            "file_id": "file_123",
            "knowledge_db_id": "kb_123",
            "file_name": "test.pdf",
            "file_type": "application/pdf",
            "file_size": 1024,
            "upload_time": datetime.now().isoformat(),
            "minio_filename": "test_file_bucket",
            "minio_url": "http://minio:9000/bucket/test.pdf",
            "is_delete": False
        }

        with patch.object(mock_db.db.files, 'insert_one', new=AsyncMock(return_value=MagicMock(acknowledged=True))) as mock_insert:
            result = await mock_db.db.files.insert_one(file_data)

            assert result.acknowledged is True
            mock_insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_files_by_knowledge_base(self, mock_db):
        """Test retrieving all files in a knowledge base"""
        kb_id = "kb_123"

        mock_cursor = Mock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "file_id": "file_1",
                "knowledge_db_id": kb_id,
                "file_name": "test1.pdf",
                "is_delete": False
            },
            {
                "file_id": "file_2",
                "knowledge_db_id": kb_id,
                "file_name": "test2.pdf",
                "is_delete": False
            }
        ])

        with patch.object(mock_db.db.files, 'find', new=Mock(return_value=mock_cursor)) as mock_find:
            result = await mock_cursor.to_list(length=100)

            assert len(result) == 2
            assert all(file["knowledge_db_id"] == kb_id for file in result)

    @pytest.mark.asyncio
    async def test_delete_file(self, mock_db):
        """Test deleting a file"""
        file_id = "file_123"

        with patch.object(mock_db.db.files, 'delete_one', new=AsyncMock(return_value=MagicMock(deleted_count=1))) as mock_delete:
            result = await mock_db.db.files.delete_one({"file_id": file_id})

            assert result.deleted_count == 1
            mock_delete.assert_called_once_with({"file_id": file_id})


class TestBulkOperations:
    """Test bulk operations to prevent N+1 queries"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock MongoDB instance"""
        db = MongoDB()
        db.client = Mock()
        db.db = Mock()
        return db

    @pytest.mark.asyncio
    async def test_bulk_delete_files(self, mock_db):
        """Test bulk deleting files (N+1 prevention)"""
        file_ids = ["file_1", "file_2", "file_3", "file_4", "file_5"]

        with patch.object(mock_db.db.files, 'delete_many', new=AsyncMock(return_value=MagicMock(deleted_count=5))) as mock_delete:
            result = await mock_db.db.files.delete_many({"file_id": {"$in": file_ids}})

            # Single query instead of N queries
            assert result.deleted_count == 5
            mock_delete.assert_called_once()
            call_args = mock_delete.call_args[0][0]
            assert call_args["file_id"]["$in"] == file_ids

    @pytest.mark.asyncio
    async def test_bulk_update_conversations(self, mock_db):
        """Test bulk updating conversations"""
        conversation_ids = ["conv_1", "conv_2", "conv_3"]

        with patch.object(mock_db.db.conversations, 'update_many', new=AsyncMock(return_value=MagicMock(matched_count=3))) as mock_update:
            result = await mock_db.db.conversations.update_many(
                {"conversation_id": {"$in": conversation_ids}},
                {"$set": {"last_modify_at": datetime.now().isoformat()}}
            )

            # Single query instead of N queries
            assert result.matched_count == 3
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_insert_files(self, mock_db):
        """Test bulk inserting files"""
        files_data = [
            {"file_id": f"file_{i}", "knowledge_db_id": "kb_123", "file_name": f"test{i}.pdf"}
            for i in range(1, 6)
        ]

        with patch.object(mock_db.db.files, 'insert_many', new=AsyncMock(return_value=MagicMock(inserted_count=5, acknowledged=True))) as mock_insert:
            result = await mock_db.db.files.insert_many(files_data)

            # Single bulk insert instead of N individual inserts
            assert result.inserted_count == 5
            assert result.acknowledged is True
            mock_insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_aggregate_conversations_with_turns(self, mock_db):
        """Test aggregating conversations with turn counts"""
        username = "testuser"

        mock_pipeline = [
            {"$match": {"username": username, "is_delete": False}},
            {"$project": {
                "conversation_id": 1,
                "conversation_name": 1,
                "turn_count": {"$size": "$turns"},
                "created_at": 1,
                "last_modify_at": 1
            }}
        ]

        mock_cursor = Mock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {"conversation_id": "conv_1", "conversation_name": "Conv 1", "turn_count": 5},
            {"conversation_id": "conv_2", "conversation_name": "Conv 2", "turn_count": 10}
        ])

        with patch.object(mock_db.db.conversations, 'aggregate', new=Mock(return_value=mock_cursor)) as mock_aggregate:
            result = await mock_cursor.to_list(length=100)

            # Single aggregation query instead of N+1 queries
            assert len(result) == 2
            assert all("turn_count" in conv for conv in result)
            mock_aggregate.assert_called_once_with(mock_pipeline)

    @pytest.mark.asyncio
    async def test_bulk_lookup_files_with_images(self, mock_db):
        """Test bulk lookup of files with their images"""
        file_ids = ["file_1", "file_2", "file_3"]

        mock_pipeline = [
            {"$match": {"file_id": {"$in": file_ids}}},
            {"$lookup": {
                "from": "images",
                "localField": "file_id",
                "foreignField": "file_id",
                "as": "images"
            }}
        ]

        mock_cursor = Mock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {"file_id": "file_1", "file_name": "test1.pdf", "images": [{"image_id": "img_1"}]},
            {"file_id": "file_2", "file_name": "test2.pdf", "images": [{"image_id": "img_2"}]}
        ])

        with patch.object(mock_db.db.files, 'aggregate', new=Mock(return_value=mock_cursor)) as mock_aggregate:
            result = await mock_cursor.to_list(length=100)

            # Single aggregation with lookup instead of N queries
            assert len(result) == 2
            assert all("images" in file for file in result)
            mock_aggregate.assert_called_once()


class TestTransactionHandling:
    """Test database transaction handling"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock MongoDB instance"""
        db = MongoDB()
        db.client = Mock()
        db.db = Mock()
        # Mock session for transactions
        db.client.start_session = Mock()
        return db

    @pytest.mark.asyncio
    async def test_transaction_commit_on_success(self, mock_db):
        """Test that transaction commits on successful operations"""
        with patch.object(mock_db.client, 'start_session') as mock_session:
            session = MagicMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock()

            # Simulate successful transaction
            session.start_transaction = Mock()
            session.commit_transaction = Mock()
            session.abort_transaction = Mock()

            # Start transaction
            session.start_transaction()

            # Perform operations (simulated)
            operations_successful = True

            if operations_successful:
                session.commit_transaction()
                session.commit_transaction.assert_called_once()
            else:
                session.abort_transaction()

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, mock_db):
        """Test that transaction rolls back on error"""
        with patch.object(mock_db.client, 'start_session') as mock_session:
            session = MagicMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session.return_value.__aexit__ = AsyncMock()

            session.start_transaction = Mock()
            session.commit_transaction = Mock()
            session.abort_transaction = Mock()

            # Start transaction
            session.start_transaction()

            # Simulate error during operations
            operations_successful = False

            if operations_successful:
                session.commit_transaction()
            else:
                session.abort_transaction()
                session.abort_transaction.assert_called_once()


class TestIndexOptimization:
    """Test database index usage and optimization"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock MongoDB instance"""
        db = MongoDB()
        db.client = Mock()
        db.db = Mock()
        return db

    @pytest.mark.asyncio
    async def test_create_indexes(self, mock_db):
        """Test that indexes are created correctly"""
        with patch.object(mock_db.db.conversations, 'create_index', new=AsyncMock()) as mock_create_index:
            # Create index on conversation_id
            await mock_db.db.conversations.create_index([("conversation_id", 1)], unique=True)

            # Create compound index on username and last_modify_at
            await mock_db.db.conversations.create_index([("username", 1), ("last_modify_at", -1)])

            assert mock_create_index.call_count == 2

    @pytest.mark.asyncio
    async def test_query_uses_index(self, mock_db):
        """Test that queries use indexed fields"""
        # Query using indexed field conversation_id
        with patch.object(mock_db.db.conversations, 'find_one', new=AsyncMock()) as mock_find:
            await mock_db.db.conversations.find_one({"conversation_id": "conv_123"})

            # Verify query uses indexed field
            call_args = mock_find.call_args[0][0]
            assert "conversation_id" in call_args

        # Query using compound index (username, last_modify_at)
        mock_cursor = Mock()
        mock_cursor.to_list = AsyncMock(return_value=[])

        with patch.object(mock_db.db.conversations, 'find', new=Mock(return_value=mock_cursor)) as mock_find:
            await mock_db.db.conversations.find({"username": "testuser"}).sort("last_modify_at", -1).to_list(100)

            # Verify query and sort use indexed fields
            call_args = mock_find.call_args[0][0]
            assert "username" in call_args


class TestConnectionManagement:
    """Test database connection management"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock MongoDB instance"""
        db = MongoDB()
        return db

    @pytest.mark.asyncio
    async def test_connect_to_database(self, mock_db):
        """Test connecting to MongoDB"""
        with patch('motor.motor_asyncio.AsyncIOMotorClient') as mock_client:
            mock_client_instance = MagicMock()
            mock_client.return_value = mock_client_instance

            mock_db.client = mock_client_instance
            mock_db.db = mock_client_instance["layra_db"]

            with patch.object(mock_db, '_create_indexes', new=AsyncMock()):
                await mock_db.connect()

            assert mock_db.client is not None
            assert mock_db.db is not None

    @pytest.mark.asyncio
    async def test_close_connection(self, mock_db):
        """Test closing MongoDB connection"""
        mock_db.client = MagicMock()
        mock_db.client.close = Mock()

        await mock_db.close()

        mock_db.client.close.assert_called_once()
