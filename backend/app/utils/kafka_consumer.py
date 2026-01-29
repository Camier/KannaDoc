import json
import asyncio
import time
from typing import Optional
from functools import wraps
from pydantic import BaseModel, ValidationError
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord
from app.core.config import settings
from app.core.logging import logger
from app.db.redis import redis
from app.rag.utils import process_file, update_task_progress
from app.utils.timezone import beijing_time_now
from app.workflow.workflow_engine import WorkflowEngine

KAFKA_TOPIC = settings.kafka_topic
KAFKA_BOOTSTRAP_SERVERS = settings.kafka_broker_url
KAFKA_GROUP_ID = settings.kafka_group_id
DLQ_TOPIC = "task_generation_dlq"
IDEMPOTENCY_TTL = 86400  # 24 hours
MAX_CONCURRENT = 10  # Increased from 5 to 10 for higher throughput
MAX_RETRIES = 3
INITIAL_DELAY = 1  # seconds
BACKOFF = 2  # exponential backoff multiplier


def retry(
    max_attempts=MAX_RETRIES,
    initial_delay=INITIAL_DELAY,
    backoff=BACKOFF,
    exceptions=(Exception,),
):
    """Retry decorator with exponential backoff."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            delay = initial_delay
            while attempts < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        raise
                    logger.warning(
                        f"Attempt {attempts}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay}s"
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff

        return wrapper

    return decorator


class FileTaskMessage(BaseModel):
    """Schema for file processing task messages."""

    task_id: str
    username: str
    knowledge_db_id: str
    file_meta: dict
    type: str = "file_processing"


class WorkflowTaskMessage(BaseModel):
    """Schema for workflow task messages."""

    type: str  # workflow, debug_resume, input_resume
    task_id: str
    username: str
    workflow_data: dict


class KafkaConsumerManager:
    """
    Hardened Kafka consumer manager with:
    - Manual commit AFTER processing (not before)
    - Retry with exponential backoff
    - Dead Letter Queue for failed messages
    - Idempotency checking
    - Message validation
    - Concurrency control
    - Metrics tracking
    """

    def __init__(self):
        self.consumer = None
        self.producer = None
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self.processing_tasks = set()
        self._start_time = time.time()
        self.metrics = {
            "processed": 0,
            "failed": 0,
            "dlq_sent": 0,
            "retries": 0,
            "avg_process_time_ms": 0,
            "messages_consumed": 0,
            "last_processed_at": None,
        }

    async def start(self):
        """Initialize and start the Kafka consumer and producer."""
        if not self.consumer:
            self.consumer = AIOKafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=KAFKA_GROUP_ID,
                enable_auto_commit=False,
                max_poll_records=100,
                max_poll_interval_ms=300000,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                isolation_level="read_committed",
                auto_offset_reset="earliest",
            )
            await self.consumer.start()
            logger.info(f"Kafka consumer started for topic: {KAFKA_TOPIC}")

        if not self.producer:
            try:
                self.producer = AIOKafkaProducer(
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    acks="all",
                )
                await self.producer.start()
                logger.info("Kafka producer started for DLQ")
            except Exception as e:
                logger.error(f"Failed to start Kafka producer: {e}")
                raise

    async def stop(self):
        """Gracefully stop consumer and producer."""
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def send_to_dlq(self, msg: ConsumerRecord, error: Exception):
        """Send failed message to Dead Letter Queue."""
        dlq_message = {
            "original_topic": KAFKA_TOPIC,
            "original_partition": msg.partition,
            "original_offset": msg.offset,
            "error": str(error),
            "error_type": type(error).__name__,
            "error_traceback": self._get_traceback_str(error),
            "timestamp": str(beijing_time_now()),
            "retry_count": self.metrics["failed"],
            "payload": json.loads(msg.value.decode("utf-8")),
        }
        try:
            await self.producer.send_and_wait(
                DLQ_TOPIC,
                json.dumps(dlq_message).encode("utf-8"),
            )
            self.metrics["dlq_sent"] += 1
            logger.warning(
                f"Message sent to DLQ: topic={DLQ_TOPIC}, "
                f"original_offset={msg.offset}, error={error}"
            )
        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}")

    def _get_traceback_str(self, error: Exception) -> str:
        """Get traceback string for error."""
        import traceback

        return "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

    def _get_idempotency_key(self, message: dict) -> str:
        msg_type = message.get("type")
        task_id = message.get("task_id", "unknown")
        if msg_type in ("workflow", "debug_resume", "input_resume"):
            return task_id

        file_meta = message.get("file_meta") or {}
        file_id = file_meta.get("file_id")
        if file_id:
            return f"file:{file_id}"
        minio_filename = file_meta.get("minio_filename")
        if minio_filename:
            return f"file:{minio_filename}"
        return f"file_task:{task_id}"

    async def is_duplicate(self, idempotency_key: str) -> bool:
        """Check if idempotency key has already been processed."""
        redis_conn = await redis.get_task_connection()
        return await redis_conn.exists(f"processed:{idempotency_key}")

    async def mark_processed(self, idempotency_key: str):
        """Mark idempotency key as processed."""
        redis_conn = await redis.get_task_connection()
        await redis_conn.set(f"processed:{idempotency_key}", "1", ex=IDEMPOTENCY_TTL)

    async def validate_message(self, message: dict) -> tuple[bool, Optional[BaseModel]]:
        """Validate message against schemas. Returns (is_valid, validated_model)."""
        msg_type = message.get("type")

        if msg_type in ("workflow", "debug_resume", "input_resume"):
            try:
                return True, WorkflowTaskMessage(**message)
            except ValidationError as e:
                logger.error(f"Workflow message validation failed: {e}")
                return False, None
        else:
            try:
                return True, FileTaskMessage(**message)
            except ValidationError as e:
                logger.error(f"File task message validation failed: {e}")
                return False, None

    @retry(max_attempts=MAX_RETRIES, initial_delay=INITIAL_DELAY, backoff=BACKOFF)
    async def process_file_task(self, message: dict):
        """Process file task with retry."""
        task_id = message["task_id"]
        username = message["username"]
        knowledge_db_id = message["knowledge_db_id"]
        file_meta = message["file_meta"]

        redis_conn = await redis.get_task_connection()
        await update_task_progress(
            redis_conn,
            task_id,
            "processing",
            f"Processing {file_meta['original_filename']}...",
        )

        await process_file(
            redis=redis_conn,
            task_id=task_id,
            username=username,
            knowledge_db_id=knowledge_db_id,
            file_meta=file_meta,
        )

    async def process_workflow_task(
        self, message: dict, debug_resume=False, input_resume=False
    ):
        """Process workflow task."""
        task_id = message["task_id"]
        workflow_data = message["workflow_data"]
        redis_conn = await redis.get_task_connection()

        try:
            # Check if workflow was canceled
            exists = await redis_conn.exists(f"workflow:{task_id}:operator")
            if exists:
                status = await redis_conn.hget(f"workflow:{task_id}:operator", "status")
                if status in ["canceling", "canceled", b"canceling", b"canceled"]:
                    await redis_conn.xadd(
                        f"workflow:events:{task_id}",
                        {
                            "type": "workflow",
                            "status": "canceled",
                            "result": "",
                            "error": "Workflow canceled by user",
                            "create_time": str(beijing_time_now()),
                        },
                    )
                    logger.info(f"Skipping canceled workflow: {task_id}")
                    return

            await redis_conn.hset(f"workflow:{task_id}", "status", "running")
            await redis_conn.xadd(
                f"workflow:events:{task_id}",
                {
                    "type": "workflow",
                    "status": "running",
                    "result": "",
                    "error": "",
                    "create_time": str(beijing_time_now()),
                },
            )

            async with WorkflowEngine(
                username=message["username"],
                nodes=workflow_data["nodes"],
                edges=workflow_data["edges"],
                global_variables=workflow_data["global_variables"],
                start_node=workflow_data["start_node"],
                task_id=task_id,
                breakpoints=workflow_data["breakpoints"],
                user_message=workflow_data["user_message"],
                parent_id=workflow_data["parent_id"],
                temp_db_id=workflow_data["temp_db_id"],
                chatflow_id=workflow_data["chatflow_id"],
                docker_image_use=workflow_data["docker_image_use"],
                need_save_image=workflow_data["need_save_image"],
            ) as engine:
                if debug_resume or input_resume:
                    if await engine.load_state():
                        logger.info(f"Resuming workflow {task_id} from saved state")
                    else:
                        raise ValueError("Workflow expired!")

                if not engine.graph[0]:
                    raise ValueError(engine.graph[-1])

                await engine.start(debug_resume, input_resume)

                await redis_conn.hset(
                    f"workflow:{task_id}",
                    mapping={
                        "status": "completed",
                        "result": json.dumps(engine.context),
                        "end_time": str(beijing_time_now()),
                    },
                )

                if engine.break_workflow:
                    await engine.save_state()
                    workflow_status = "pause"
                elif engine.break_workflow_get_input:
                    await engine.save_state()
                    workflow_status = "vlm_input"
                else:
                    workflow_status = "completed"

                await redis_conn.xadd(
                    f"workflow:events:{task_id}",
                    {
                        "type": "workflow",
                        "status": workflow_status,
                        "result": json.dumps(engine.context),
                        "error": "",
                        "create_time": str(beijing_time_now()),
                    },
                )

        except Exception as e:
            await redis_conn.hset(
                name=f"workflow:{task_id}",
                mapping={
                    "status": "failed",
                    "error": str(e),
                    "end_time": str(beijing_time_now()),
                },
            )
            await redis_conn.xadd(
                f"workflow:events:{task_id}",
                {
                    "type": "workflow",
                    "status": "failed",
                    "result": "",
                    "error": str(e),
                    "create_time": str(beijing_time_now()),
                },
            )
            logger.exception(f"Workflow task failed: {task_id} - {e}")
            raise

        finally:
            pipeline = redis_conn.pipeline()
            pipeline.expire(f"workflow:{task_id}", 3600)
            pipeline.expire(f"workflow:{task_id}:nodes", 3600)
            pipeline.expire(f"workflow:events:{task_id}", 3600)
            pipeline.expire(f"workflow:{task_id}:operator", 3600)
            await pipeline.execute()

    async def _process_single_message(self, msg: ConsumerRecord) -> bool:
        """Process a single message with full error handling. Returns True if successful."""
        start_time = time.time()
        message = None

        try:
            # Decode message
            message = json.loads(msg.value.decode("utf-8"))
            task_id = message.get("task_id", "unknown")
            idempotency_key = self._get_idempotency_key(message)

            # Check idempotency
            if await self.is_duplicate(idempotency_key):
                logger.info(f"Skipping duplicate task: {idempotency_key}")
                return True  # Treat as success

            # Validate message
            is_valid, validated = await self.validate_message(message)
            if not is_valid:
                # Invalid message - send to DLQ and commit (skip permanently)
                await self.send_to_dlq(msg, ValueError("Invalid message format"))
                return True

            # Process based on message type
            msg_type = message.get("type")
            if msg_type in ("workflow", "debug_resume", "input_resume"):
                await self.process_workflow_task(
                    message,
                    debug_resume=(msg_type == "debug_resume"),
                    input_resume=(msg_type == "input_resume"),
                )
            else:
                await self.process_file_task(message)

            # Mark as processed
            await self.mark_processed(idempotency_key)

            # Update metrics
            self.metrics["processed"] += 1
            self.metrics["messages_consumed"] += 1
            self.metrics["last_processed_at"] = str(beijing_time_now())

            process_time = (time.time() - start_time) * 1000
            self._update_avg_process_time(process_time)

            logger.info(
                f"Successfully processed task: {task_id} in {process_time:.2f}ms"
            )
            return True

        except ValidationError as e:
            # Invalid message - skip and send to DLQ
            logger.error(f"Message validation failed: {e}")
            await self.send_to_dlq(msg, e)
            self.metrics["failed"] += 1
            return True  # Commit to skip permanently

        except Exception as e:
            # Processing failed - will be retried or sent to DLQ
            self.metrics["failed"] += 1
            logger.exception(
                f"Processing failed for message at offset {msg.offset}: {e}"
            )
            raise

    def _update_avg_process_time(self, new_time_ms: float):
        """Update rolling average of processing time."""
        n = self.metrics["processed"]
        if n > 0:
            self.metrics["avg_process_time_ms"] = (
                self.metrics["avg_process_time_ms"] * (n - 1) + new_time_ms
            ) / n

    async def _process_with_semaphore(self, msg: ConsumerRecord):
        """Process message with concurrency control."""
        async with self.semaphore:
            await self._process_single_message(msg)
            self.processing_tasks.discard(asyncio.current_task())

    async def consume_messages(self):
        """Main message consumption loop with hardening."""
        await self.start()
        logger.info(f"Starting hardened Kafka consumer for topic: {KAFKA_TOPIC}")

        try:
            async for msg in self.consumer:
                # Check concurrent limit
                if len(self.processing_tasks) >= MAX_CONCURRENT:
                    done, self.processing_tasks = await asyncio.wait(
                        self.processing_tasks, return_when=asyncio.FIRST_COMPLETED
                    )

                # Create processing task
                task = asyncio.create_task(self._process_with_semaphore(msg))
                self.processing_tasks.add(task)
                task.add_done_callback(self.processing_tasks.discard)

        except asyncio.CancelledError:
            logger.info("Kafka consumer cancelled")
            raise
        except Exception as e:
            logger.exception(f"Consumer loop error: {e}")
            raise

    def get_metrics(self) -> dict:
        """Get consumer metrics."""
        uptime = time.time() - self._start_time
        return {
            **self.metrics,
            "uptime_seconds": round(uptime, 2),
            "active_tasks": len(self.processing_tasks),
            "concurrency_limit": MAX_CONCURRENT,
            "timestamp": str(beijing_time_now()),
        }

    def get_health_status(self) -> dict:
        """Get consumer health status."""
        try:
            if not self.consumer:
                return {"status": "unhealthy", "reason": "Consumer not initialized"}

            partitions = self.consumer.assignment()
            if not partitions:
                return {"status": "unhealthy", "reason": "No partitions assigned"}

            return {
                "status": "healthy",
                "partitions_assigned": len(partitions),
                "metrics": self.get_metrics(),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global instance
kafka_consumer_manager = KafkaConsumerManager()
