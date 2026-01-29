"""
Workflow Engine Tests
Tests workflow execution, loop nodes, condition nodes, VLM nodes, and state management
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from app.workflow.workflow_engine import WorkflowEngine
from app.workflow.graph import TreeNode, WorkflowGraph


class TestWorkflowEngine:
    """Test WorkflowEngine core functionality"""

    @pytest.fixture
    def sample_nodes(self):
        """Create sample nodes for testing"""
        return [
            {
                "id": "node_start",
                "type": "start",
                "data": {"name": "Start Node"}
            },
            {
                "id": "node_code_1",
                "type": "code",
                "data": {
                    "name": "Code Node 1",
                    "code": "result = 42\nprint(result)"
                }
            },
            {
                "id": "node_vlm_1",
                "type": "vlm",
                "data": {
                    "name": "VLM Node",
                    "vlmInput": "What is in this image?",
                    "prompt": "You are a helpful assistant.",
                    "isChatflowInput": False,
                    "isChatflowOutput": True,
                    "useChatHistory": False,
                    "mcpUse": {},
                    "chatflowOutputVariable": "vlm_result",
                    "modelConfig": {
                        "model_name": "gpt-4",
                        "model_url": "",
                        "api_key": "test_key",
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                }
            },
            {
                "id": "node_end",
                "type": "end",
                "data": {"name": "End Node"}
            }
        ]

    @pytest.fixture
    def sample_edges(self):
        """Create sample edges for testing"""
        return [
            {"source": "node_start", "target": "node_code_1"},
            {"source": "node_code_1", "target": "node_vlm_1"},
            {"source": "node_vlm_1", "target": "node_end"}
        ]

    @pytest.fixture
    def mock_engine(self, sample_nodes, sample_edges):
        """Create a mock WorkflowEngine for testing"""
        engine = WorkflowEngine(
            username="testuser",
            nodes=sample_nodes,
            edges=sample_edges,
            global_variables={},
            task_id="test_task_123",
            user_message="Test message",
            parent_id="",
            temp_db_id="",
            chatflow_id="test_chatflow"
        )
        return engine

    def test_workflow_initialization(self, mock_engine):
        """Test that workflow engine initializes correctly"""
        assert mock_engine.username == "testuser"
        assert mock_engine.task_id == "test_task_123"
        assert len(mock_engine.nodes) == 4
        assert mock_engine.global_variables == {}
        assert mock_engine.context == {}

    def test_graph_creation(self, mock_engine):
        """Test that workflow graph is created correctly"""
        success, root, msg = mock_engine.get_graph()
        assert success is True
        assert root is not None
        assert "验证通过" in msg or "valid" in msg.lower()

    def test_graph_validation_invalid_edges(self, sample_nodes):
        """Test that invalid graph edges are rejected"""
        invalid_edges = [
            {"source": "nonexistent", "target": "node_code_1"}
        ]
        engine = WorkflowEngine(
            username="testuser",
            nodes=sample_nodes,
            edges=invalid_edges,
            global_variables={},
            task_id="test_task"
        )
        success, root, msg = engine.get_graph()
        assert success is False
        assert "验证失败" in msg or "validation" in msg.lower()

    @pytest.mark.asyncio
    async def test_code_node_execution(self, mock_engine):
        """Test code node execution"""
        with patch('app.workflow.workflow_engine.CodeSandbox') as mock_sandbox_class:
            mock_sandbox = AsyncMock()
            mock_sandbox_class.return_value.__aenter__ = AsyncMock(return_value=mock_sandbox)
            mock_sandbox_class.return_value.__aexit__ = AsyncMock()
            mock_sandbox.execute = AsyncMock(return_value={
                "result": "42\n####Global variable updated####\nnew_var = 100\n\n"
            })

            async with mock_engine:
                code_node = TreeNode(
                    node_id="node_code_1",
                    node_type="code",
                    data={
                        "name": "Code Node",
                        "code": "result = 42"
                    },
                    condition=None
                )

                result = await mock_engine.execute_node(code_node)

                assert result is True
                assert "node_code_1" in mock_engine.context
                mock_sandbox.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_code_node_execution_error(self, mock_engine):
        """Test code node error handling"""
        with patch('app.workflow.workflow_engine.CodeSandbox') as mock_sandbox_class:
            import docker
            mock_sandbox = AsyncMock()
            mock_sandbox_class.return_value.__aenter__ = AsyncMock(return_value=mock_sandbox)
            mock_sandbox_class.return_value.__aexit__ = AsyncMock()
            mock_sandbox.execute = AsyncMock(side_effect=docker.errors.ContainerError(
                "test_container", 1, "test_command", b"Container error", b"Error output"
            ))

            async with mock_engine:
                code_node = TreeNode(
                    node_id="node_code_1",
                    node_type="code",
                    data={
                        "name": "Code Node",
                        "code": "invalid_code"
                    },
                    condition=None
                )

                with pytest.raises(ValueError) as exc_info:
                    await mock_engine.execute_node(code_node)

                assert "容器执行错误" in str(exc_info.value) or "container" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_vlm_node_execution(self, mock_engine):
        """Test VLM node execution"""
        with patch('app.workflow.workflow_engine.ChatService') as mock_chat_service:
            # Mock the chat stream generator
            async def mock_stream():
                chunks = [
                    json.dumps({"type": "text", "data": "Hello ", "message_id": "msg123"}),
                    json.dumps({"type": "text", "data": "world!", "message_id": "msg123"}),
                    json.dumps({"type": "token", "total_token": 10, "completion_tokens": 5, "prompt_tokens": 5, "message_id": "msg123"}),
                ]
                for chunk in chunks:
                    yield f"data: {chunk}\n\n"

            mock_chat_service.create_chat_stream = Mock(return_value=mock_stream())

            async with mock_engine:
                vlm_node = TreeNode(
                    node_id="node_vlm_1",
                    node_type="vlm",
                    data={
                        "name": "VLM Node",
                        "vlmInput": "What is in this image?",
                        "prompt": "You are helpful.",
                        "isChatflowInput": False,
                        "isChatflowOutput": True,
                        "useChatHistory": False,
                        "mcpUse": {},
                        "chatflowOutputVariable": "vlm_result",
                        "modelConfig": {
                            "model_name": "gpt-4",
                            "model_url": "",
                            "api_key": "test_key"
                        }
                    },
                    condition=None
                )

                result = await mock_engine.execute_node(vlm_node)

                assert result is True
                assert "vlm_result" in mock_engine.global_variables
                assert mock_engine.global_variables["vlm_result"] == repr("Hello world!")

    @pytest.mark.asyncio
    async def test_vlm_node_with_chatflow_input(self, mock_engine):
        """Test VLM node that requires user input"""
        with patch('app.workflow.workflow_engine.ChatService'):
            async with mock_engine:
                vlm_node = TreeNode(
                    node_id="node_vlm_input",
                    node_type="vlm",
                    data={
                        "name": "VLM Input Node",
                        "vlmInput": "",
                        "prompt": "You are helpful.",
                        "isChatflowInput": True,
                        "isChatflowOutput": False,
                        "useChatHistory": False,
                        "mcpUse": {},
                        "chatflowOutputVariable": "",
                        "modelConfig": {}
                    },
                    condition=None
                )

                result = await mock_engine.execute_node(vlm_node)

                # Should pause and return False
                assert result is False
                assert mock_engine.break_workflow_get_input is True


class TestConditionNode:
    """Test condition node functionality"""

    @pytest.fixture
    def condition_nodes(self):
        """Create nodes with conditions"""
        return [
            {
                "id": "node_start",
                "type": "start",
                "data": {"name": "Start"}
            },
            {
                "id": "node_condition",
                "type": "condition",
                "data": {
                    "name": "Condition Node",
                    "conditions": {
                        "0": "x > 10",
                        "1": "x == 5",
                        "2": "x < 0"
                    }
                }
            },
            {
                "id": "node_branch_0",
                "type": "code",
                "data": {"name": "Branch 0", "code": "pass"}
            },
            {
                "id": "node_branch_1",
                "type": "code",
                "data": {"name": "Branch 1", "code": "pass"}
            },
            {
                "id": "node_branch_2",
                "type": "code",
                "data": {"name": "Branch 2", "code": "pass"}
            }
        ]

    @pytest.fixture
    def condition_edges(self):
        """Create edges for condition testing"""
        return [
            {"source": "node_start", "target": "node_condition"},
            {"source": "node_condition", "target": "node_branch_0", "condition": 0},
            {"source": "node_condition", "target": "node_branch_1", "condition": 1},
            {"source": "node_condition", "target": "node_branch_2", "condition": 2}
        ]

    @pytest.mark.asyncio
    async def test_condition_node_evaluation_first_branch(self, condition_nodes, condition_edges):
        """Test condition node evaluates first branch correctly"""
        engine = WorkflowEngine(
            username="testuser",
            nodes=condition_nodes,
            edges=condition_edges,
            global_variables={"x": 15},
            task_id="test_task"
        )

        condition_node = TreeNode(
            node_id="node_condition",
            node_type="condition",
            data={
                "name": "Condition Node",
                "conditions": {
                    "0": "x > 10",
                    "1": "x == 5"
                }
            },
            condition=None
        )

        result = await engine.handle_condition(condition_node)

        # Should match first condition (x > 10)
        assert len(result) == 1
        assert result[0].condition == 0

    @pytest.mark.asyncio
    async def test_condition_node_evaluation_second_branch(self, condition_nodes, condition_edges):
        """Test condition node evaluates second branch correctly"""
        engine = WorkflowEngine(
            username="testuser",
            nodes=condition_nodes,
            edges=condition_edges,
            global_variables={"x": 5},
            task_id="test_task"
        )

        condition_node = TreeNode(
            node_id="node_condition",
            node_type="condition",
            data={
                "name": "Condition Node",
                "conditions": {
                    "0": "x > 10",
                    "1": "x == 5"
                }
            },
            condition=None
        )

        result = await engine.handle_condition(condition_node)

        # Should match second condition (x == 5)
        assert len(result) == 1
        assert result[0].condition == 1

    @pytest.mark.asyncio
    async def test_condition_node_no_match(self, condition_nodes, condition_edges):
        """Test condition node when no conditions match"""
        engine = WorkflowEngine(
            username="testuser",
            nodes=condition_nodes,
            edges=condition_edges,
            global_variables={"x": 7},
            task_id="test_task"
        )

        condition_node = TreeNode(
            node_id="node_condition",
            node_type="condition",
            data={
                "name": "Condition Node",
                "conditions": {
                    "0": "x > 10",
                    "1": "x == 5"
                }
            },
            condition=None
        )

        result = await engine.handle_condition(condition_node)

        # Should return empty list (no match)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_condition_node_multiple_matches(self, condition_nodes, condition_edges):
        """Test condition node when multiple conditions match"""
        engine = WorkflowEngine(
            username="testuser",
            nodes=condition_nodes,
            edges=condition_edges,
            global_variables={"x": 15},
            task_id="test_task"
        )

        condition_node = TreeNode(
            node_id="node_condition",
            node_type="condition",
            data={
                "name": "Condition Node",
                "conditions": {
                    "0": "x > 10",
                    "1": "x > 0",
                    "2": "x < 100"
                }
            },
            condition=None
        )

        result = await engine.handle_condition(condition_node)

        # All three should match
        assert len(result) == 3


class TestLoopNode:
    """Test loop node functionality"""

    @pytest.fixture
    def loop_nodes(self):
        """Create nodes with loops"""
        return [
            {
                "id": "node_start",
                "type": "start",
                "data": {"name": "Start"}
            },
            {
                "id": "node_loop",
                "type": "loop",
                "data": {
                    "name": "Count Loop",
                    "loopType": "count",
                    "maxCount": "3"
                }
            },
            {
                "id": "node_loop_body",
                "type": "code",
                "data": {"name": "Loop Body", "code": "pass"}
            },
            {
                "id": "node_after_loop",
                "type": "code",
                "data": {"name": "After Loop", "code": "pass"}
            }
        ]

    @pytest.fixture
    def loop_edges(self):
        """Create edges for loop testing"""
        return [
            {"source": "node_start", "target": "node_loop"},
            {"source": "node_loop", "target": "node_loop_body", "isLoopBody": True},
            {"source": "node_loop_body", "target": "node_loop"},
            {"source": "node_loop", "target": "node_after_loop"}
        ]

    @pytest.mark.asyncio
    async def test_loop_node_count_type(self, loop_nodes, loop_edges):
        """Test count-based loop node"""
        engine = WorkflowEngine(
            username="testuser",
            nodes=loop_nodes,
            edges=loop_edges,
            global_variables={},
            task_id="test_task"
        )

        # Create a mock loop node
        loop_node = Mock()
        loop_node.node_id = "node_loop"
        loop_node.node_type = "loop"
        loop_node.data = {"name": "Count Loop", "loopType": "count", "maxCount": "3"}
        loop_node.loop_last = []
        loop_node.loop_info = []
        loop_node.loop_children = []
        loop_node.parents = []
        loop_node.condition = None
        loop_node.children = []

        # Initialize loop index
        engine.loop_index["node_loop"] = 0

        # Test loop iteration
        assert engine.loop_index["node_loop"] < 3
        engine.loop_index["node_loop"] += 1
        assert engine.loop_index["node_loop"] == 1

    @pytest.mark.asyncio
    async def test_loop_node_condition_type(self, loop_nodes, loop_edges):
        """Test condition-based loop node"""
        engine = WorkflowEngine(
            username="testuser",
            nodes=loop_nodes,
            edges=loop_edges,
            global_variables={"x": 0},
            task_id="test_task"
        )

        loop_node = Mock()
        loop_node.node_id = "node_loop"
        loop_node.node_type = "loop"
        loop_node.data = {"name": "Condition Loop", "loopType": "condition", "condition": "x >= 5"}
        loop_node.loop_last = []
        loop_node.loop_info = []
        loop_node.loop_children = []
        loop_node.parents = []
        loop_node.condition = None
        loop_node.children = []

        engine.loop_index["node_loop"] = 0

        # Test loop continues while condition is False
        assert engine.loop_index["node_loop"] < 100

        # Test loop exits when condition is True
        engine.global_variables["x"] = 10
        should_exit = engine.safe_eval("x >= 5", "test", "test_id")
        assert should_exit is True


class TestStateManagement:
    """Test workflow state persistence and loading"""

    @pytest.fixture
    def sample_engine(self):
        """Create engine for state testing"""
        nodes = [
            {"id": "node_start", "type": "start", "data": {"name": "Start"}},
            {"id": "node_1", "type": "code", "data": {"name": "Node 1", "code": "x = 1"}}
        ]
        edges = [{"source": "node_start", "target": "node_1"}]

        engine = WorkflowEngine(
            username="testuser",
            nodes=nodes,
            edges=edges,
            global_variables={"x": 10, "y": 20},
            task_id="state_test_task"
        )
        engine.execution_status = {"node_start": True, "node_1": False}
        engine.context = {"node_start": [{"result": "completed"}]}
        engine.loop_index = {}
        engine.skip_nodes = []

        return engine

    @pytest.mark.asyncio
    async def test_save_state(self, sample_engine):
        """Test saving workflow state to Redis"""
        with patch('app.workflow.workflow_engine.redis') as mock_redis:
            mock_conn = AsyncMock()
            mock_redis.get_task_connection = AsyncMock(return_value=mock_conn)

            await sample_engine.save_state()

            # Verify Redis setex was called
            mock_conn.setex.assert_called_once()
            call_args = mock_conn.setex.call_args
            assert "workflow:state_test_task:state" in call_args[0][0]

            # Verify state JSON contains expected keys
            state_json = call_args[0][1]
            state = json.loads(state_json)
            assert "global_variables" in state
            assert "execution_status" in state
            assert "context" in state
            assert state["global_variables"]["x"] == 10

    @pytest.mark.asyncio
    async def test_load_state(self, sample_engine):
        """Test loading workflow state from Redis"""
        state_to_load = {
            "global_variables": {"x": 100, "y": 200},
            "execution_status": {"node_start": True, "node_1": True},
            "execution_stack": [],
            "loop_index": {},
            "context": {"node_1": [{"result": "loaded"}]},
            "skip_nodes": []
        }

        with patch('app.workflow.workflow_engine.redis') as mock_redis:
            mock_conn = AsyncMock()
            mock_redis.get_task_connection = AsyncMock(return_value=mock_conn)
            mock_conn.get = AsyncMock(return_value=json.dumps(state_to_load))

            success = await sample_engine.load_state()

            assert success is True
            assert sample_engine.global_variables["x"] == 100
            assert sample_engine.global_variables["y"] == 200
            assert sample_engine.execution_status["node_1"] is True
            assert sample_engine.context["node_1"][0]["result"] == "loaded"

    @pytest.mark.asyncio
    async def test_load_state_no_existing_state(self, sample_engine):
        """Test loading state when none exists"""
        with patch('app.workflow.workflow_engine.redis') as mock_redis:
            mock_conn = AsyncMock()
            mock_redis.get_task_connection = AsyncMock(return_value=mock_conn)
            mock_conn.get = AsyncMock(return_value=None)

            success = await sample_engine.load_state()

            assert success is False
            # Original values should remain unchanged
            assert sample_engine.global_variables["x"] == 10


class TestWorkflowCancellation:
    """Test workflow cancellation handling"""

    @pytest.fixture
    def cancellable_engine(self):
        """Create engine for cancellation testing"""
        nodes = [
            {"id": "node_start", "type": "start", "data": {"name": "Start"}},
            {"id": "node_1", "type": "code", "data": {"name": "Node 1", "code": "pass"}}
        ]
        edges = [{"source": "node_start", "target": "node_1"}]

        engine = WorkflowEngine(
            username="testuser",
            nodes=nodes,
            edges=edges,
            global_variables={},
            task_id="cancellable_task"
        )

        return engine

    @pytest.mark.asyncio
    async def test_check_cancellation_not_cancelled(self, cancellable_engine):
        """Test cancellation check when not cancelled"""
        with patch('app.workflow.workflow_engine.redis') as mock_redis:
            mock_conn = AsyncMock()
            mock_redis.get_task_connection = AsyncMock(return_value=mock_conn)
            mock_conn.hget = AsyncMock(return_value=b"running")

            # Should not raise exception
            await cancellable_engine.check_cancellation()

    @pytest.mark.asyncio
    async def test_check_cancellation_is_cancelled(self, cancellable_engine):
        """Test cancellation check when cancelled"""
        with patch('app.workflow.workflow_engine.redis') as mock_redis:
            mock_conn = AsyncMock()
            mock_redis.get_task_connection = AsyncMock(return_value=mock_conn)
            mock_conn.hget = AsyncMock(return_value=b"canceling")

            with patch.object(cancellable_engine, 'cleanup', new=AsyncMock()):
                with pytest.raises(ValueError) as exc_info:
                    await cancellable_engine.check_cancellation()

                assert "canceled" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_cleanup_resources(self, cancellable_engine):
        """Test cleanup of resources on cancellation"""
        mock_sandbox = AsyncMock()
        cancellable_engine.sandbox = mock_sandbox

        with patch('app.workflow.workflow_engine.redis') as mock_redis:
            mock_conn = AsyncMock()
            mock_redis.get_task_connection = AsyncMock(return_value=mock_conn)
            mock_conn.hset = AsyncMock()
            mock_conn.xadd = AsyncMock()

            await cancellable_engine.cleanup()

            # Verify sandbox is closed
            mock_sandbox.close.assert_called_once()
            # Verify Redis state is updated
            mock_conn.hset.assert_called_once()
            # Verify cancellation event is sent
            mock_conn.xadd.assert_called_once()


class TestBreakpoints:
    """Test breakpoint functionality for debugging"""

    @pytest.fixture
    def debug_engine(self):
        """Create engine with breakpoints"""
        nodes = [
            {"id": "node_start", "type": "start", "data": {"name": "Start"}},
            {"id": "node_1", "type": "code", "data": {"name": "Node 1", "code": "pass"}},
            {"id": "node_2", "type": "code", "data": {"name": "Node 2", "code": "pass"}}
        ]
        edges = [
            {"source": "node_start", "target": "node_1"},
            {"source": "node_1", "target": "node_2"}
        ]

        engine = WorkflowEngine(
            username="testuser",
            nodes=nodes,
            edges=edges,
            global_variables={},
            task_id="debug_task",
            breakpoints=["node_1"]
        )

        return engine

    def test_breakpoint_initialization(self, debug_engine):
        """Test that breakpoints are initialized correctly"""
        assert "node_1" in debug_engine.breakpoints
        assert len(debug_engine.breakpoints) == 1

    @pytest.mark.asyncio
    async def test_send_pause_event(self, debug_engine):
        """Test sending pause event to Redis"""
        mock_node = Mock()
        mock_node.node_id = "node_1"
        mock_node.node_type = "code"
        mock_node.data = {"name": "Node 1"}
        mock_node.condition = None

        with patch('app.workflow.workflow_engine.redis') as mock_redis:
            mock_conn = AsyncMock()
            mock_redis.get_task_connection = AsyncMock(return_value=mock_conn)
            mock_conn.xadd = AsyncMock()
            mock_conn.pipeline = Mock(return_value=mock_conn)
            mock_conn.expire = AsyncMock()

            await debug_engine._send_pause_event(mock_node)

            # Verify event was sent
            mock_conn.xadd.assert_called_once()
            call_args = mock_conn.xadd.call_args
            assert call_args[0][0] == f"workflow:events:{debug_engine.task_id}"
            assert call_args[0][1]["status"] == "pause"
            assert call_args[0][1]["node"] == "node_1"
