"""
Background Queue Management System with SSE Streaming

This module provides a lightweight implementation combining background job processing
with Server-Sent Events (SSE) streaming for real-time progress updates.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional, Set

import redis.asyncio as redis
import uvloop
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from hypercorn.asyncio import serve
from hypercorn.config import Config
from pydantic import BaseModel, Field

from src.utils.logger_config import set_logger_config

# Configure logging
set_logger_config()
logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobEvent(BaseModel):
    """Event model for job progress updates."""

    job_id: str
    status: JobStatus
    stage: str
    message: str
    progress: Optional[float] = Field(None, ge=0.0, le=100.0)
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None


class JobRequest(BaseModel):
    """Request model for job submission."""

    task_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1, ge=1, le=10)


class JobResponse(BaseModel):
    """Response model for job submission."""

    job_id: str
    status: JobStatus
    message: str


@dataclass
class Job:
    """Job data structure."""

    id: str
    task_type: str
    parameters: Dict[str, Any]
    priority: int
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class EventPublisher:
    """Handles publishing events to Redis pub/sub."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.channel_prefix = "job_events"

    async def publish_event(self, event: JobEvent) -> None:
        """Publish a job event to Redis."""
        try:
            channel = f"{self.channel_prefix}:{event.job_id}"
            message = event.model_dump_json()
            await self.redis.publish(channel, message)
            logger.info(f"📡 Published event for job {event.job_id}: {event.stage}")
        except Exception as e:
            logger.error(f"❌ Failed to publish event: {e}")

    async def publish_broadcast(self, event: JobEvent) -> None:
        """Publish a broadcast event to all subscribers."""
        try:
            channel = f"{self.channel_prefix}:broadcast"
            message = event.model_dump_json()
            await self.redis.publish(channel, message)
        except Exception as e:
            logger.error(f"📢❌ Failed to publish broadcast event: {e}")


class JobManager:
    """Manages job lifecycle and status tracking."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.job_prefix = "job"
        self.queue_key = "job_queue"

    async def create_job(self, request: JobRequest) -> Job:
        """Create a new job and add it to the queue."""
        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            task_type=request.task_type,
            parameters=request.parameters,
            priority=request.priority,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        # Store job data
        await self._store_job(job)

        # Add to priority queue
        await self._add_to_queue(job)

        logger.info(f"🆕 Created job {job_id} of type {request.task_type}")
        return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Retrieve a job by ID."""
        try:
            job_data = await self.redis.hgetall(f"{self.job_prefix}:{job_id}")
            if not job_data:
                return None

            return self._deserialize_job(job_data)
        except Exception as e:
            logger.error(f"🔍❌ Failed to get job {job_id}: {e}")
            return None

    async def update_job_status(
        self, job_id: str, status: JobStatus, **kwargs: Dict[str, Any]
    ) -> bool:
        """Update job status and optional fields."""
        try:
            job = await self.get_job(job_id)
            if not job:
                return False

            job.status = status

            if status == JobStatus.RUNNING and not job.started_at:
                job.started_at = datetime.utcnow()
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                job.completed_at = datetime.utcnow()

            # Update additional fields
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)

            await self._store_job(job)
            return True
        except Exception as e:
            logger.error(f"🔄❌ Failed to update job {job_id}: {e}")
            return False

    async def _store_job(self, job: Job) -> None:
        """Store job data in Redis."""
        job_data = self._serialize_job(job)
        await self.redis.hset(f"{self.job_prefix}:{job.id}", mapping=job_data)
        # Set expiration for completed jobs (24 hours)
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            await self.redis.expire(f"{self.job_prefix}:{job.id}", 86400)

    async def _add_to_queue(self, job: Job) -> None:
        """Add job to priority queue."""
        queue_data = {
            "job_id": job.id,
            "priority": job.priority,
            "created_at": job.created_at.timestamp(),
        }
        await self.redis.zadd(self.queue_key, {json.dumps(queue_data): job.priority})

    async def get_next_job(self) -> Optional[Job]:
        """Get the next job from the queue with highest priority."""
        try:
            # Get job with highest priority (lowest score = highest priority)
            queue_items = await self.redis.zrange(self.queue_key, 0, 0, withscores=True)
            if not queue_items:
                return None

            queue_data = json.loads(queue_items[0][0])
            job_id = queue_data["job_id"]

            # Remove from queue
            await self.redis.zrem(self.queue_key, queue_items[0][0])

            return await self.get_job(job_id)
        except Exception as e:
            logger.error(f"📋❌ Failed to get next job: {e}")
            return None

    def _serialize_job(self, job: Job) -> Dict[str, str]:
        """Serialize job to Redis-compatible format."""
        return {
            "id": job.id,
            "task_type": job.task_type,
            "parameters": json.dumps(job.parameters),
            "priority": str(job.priority),
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else "",
            "completed_at": job.completed_at.isoformat() if job.completed_at else "",
            "result": json.dumps(job.result) if job.result else "",
            "error": job.error or "",
        }

    def _deserialize_job(self, job_data: Dict[str, str]) -> Job:
        """Deserialize job from Redis format."""
        return Job(
            id=job_data["id"],
            task_type=job_data["task_type"],
            parameters=json.loads(job_data["parameters"]),
            priority=int(job_data["priority"]),
            status=JobStatus(job_data["status"]),
            created_at=datetime.fromisoformat(job_data["created_at"]),
            started_at=(
                datetime.fromisoformat(job_data["started_at"]) if job_data["started_at"] else None
            ),
            completed_at=(
                datetime.fromisoformat(job_data["completed_at"])
                if job_data["completed_at"]
                else None
            ),
            result=json.loads(job_data["result"]) if job_data["result"] else None,
            error=job_data["error"] if job_data["error"] else None,
        )


class BackgroundWorker:
    """Processes jobs in the background."""

    def __init__(self, job_manager: JobManager, event_publisher: EventPublisher):
        self.job_manager = job_manager
        self.event_publisher = event_publisher
        self.running = False
        self.active_jobs: Set[str] = set()

    async def start(self) -> None:
        """Start the background worker."""
        self.running = True
        logger.info("🚀 Background worker started")
        uvloop.install()

        while self.running:
            try:
                job = await self.job_manager.get_next_job()
                if job:
                    await self._process_job(job)
                else:
                    # No jobs available, wait a bit
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"⚙️ Worker error: {e}")
                await asyncio.sleep(5)

    async def stop(self) -> None:
        """Stop the background worker."""
        self.running = False
        logger.info("🛑 Background worker stopped")

    async def _process_job(self, job: Job) -> None:
        """Process a single job."""
        job_id = job.id
        self.active_jobs.add(job_id)

        try:
            # Update status to running
            await self.job_manager.update_job_status(job_id, JobStatus.RUNNING)
            await self._publish_progress(job_id, "Job started", 0.0)

            # Simulate job processing with multiple stages
            stages = [
                ("Initializing", 10.0),
                ("Processing data", 30.0),
                ("Running calculations", 60.0),
                ("Finalizing results", 90.0),
                ("Job completed", 100.0),
            ]

            for stage_name, progress in stages:
                await asyncio.sleep(2)  # Simulate work
                await self._publish_progress(job_id, stage_name, progress)

            # Complete the job
            result = {"message": "Job completed successfully", "data": job.parameters}
            await self.job_manager.update_job_status(job_id, JobStatus.COMPLETED, result=result)
            await self._publish_progress(job_id, "Job completed", 100.0)

        except Exception as e:
            error_msg = f"Job failed: {str(e)}"
            await self.job_manager.update_job_status(job_id, JobStatus.FAILED, error=error_msg)  # type: ignore
            await self._publish_progress(job_id, error_msg, 0.0, status=JobStatus.FAILED)
            logger.error(f"💥 Job {job_id} failed: {e}")

        finally:
            self.active_jobs.discard(job_id)

    async def _publish_progress(
        self, job_id: str, message: str, progress: float, status: JobStatus = JobStatus.RUNNING
    ) -> None:
        """Publish job progress event."""
        event = JobEvent(
            job_id=job_id,
            status=status,
            stage=message,
            message=message,
            progress=progress,
            timestamp=datetime.now(timezone.utc),
        )
        await self.event_publisher.publish_event(event)


class SSEManager:
    """Manages SSE connections and event streaming."""

    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client
        self.active_connections: Set[asyncio.Queue[JobEvent]] = set()

    async def subscribe_to_job(self, job_id: str) -> asyncio.Queue[JobEvent]:
        """Subscribe to events for a specific job."""
        queue: asyncio.Queue[JobEvent] = asyncio.Queue()
        self.active_connections.add(queue)

        # Start listening for events
        asyncio.create_task(self._listen_for_events(job_id, queue))

        return queue

    async def subscribe_to_broadcast(self) -> asyncio.Queue[JobEvent]:
        """Subscribe to broadcast events."""
        queue: asyncio.Queue[JobEvent] = asyncio.Queue()
        self.active_connections.add(queue)

        # Start listening for broadcast events
        asyncio.create_task(self._listen_for_broadcast(queue))

        return queue

    async def _listen_for_events(self, job_id: str, queue: asyncio.Queue[JobEvent]) -> None:
        """Listen for events on a specific job channel."""
        pubsub = self.redis.pubsub()
        channel = f"job_events:{job_id}"

        try:
            await pubsub.subscribe(channel)

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        event = JobEvent(**event_data)
                        await queue.put(event)
                    except Exception as e:
                        logger.error(f"📄❌ Failed to parse event: {e}")

        except Exception as e:
            logger.error(f"🔊❌ Error listening for events on {channel}: {e}")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            self.active_connections.discard(queue)

    async def _listen_for_broadcast(self, queue: asyncio.Queue[JobEvent]) -> None:
        """Listen for broadcast events."""
        pubsub = self.redis.pubsub()
        channel = "job_events:broadcast"

        try:
            await pubsub.subscribe(channel)

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        event = JobEvent(**event_data)
                        await queue.put(event)
                    except Exception as e:
                        logger.error(f"📢📄❌ Failed to parse broadcast event: {e}")

        except Exception as e:
            logger.error(f"📢🔊❌ Error listening for broadcast events: {e}")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            self.active_connections.discard(queue)


# Global instances
redis_client: Optional[redis.Redis] = None
job_manager: Optional[JobManager] = None
event_publisher: Optional[EventPublisher] = None
background_worker: Optional[BackgroundWorker] = None
sse_manager: Optional[SSEManager] = None


async def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    if redis_client is None:
        raise RuntimeError("Redis client not initialized")
    return redis_client


async def get_job_manager() -> JobManager:
    """Get job manager instance."""
    if job_manager is None:
        raise RuntimeError("Job manager not initialized")
    return job_manager


async def get_event_publisher() -> EventPublisher:
    """Get event publisher instance."""
    if event_publisher is None:
        raise RuntimeError("Event publisher not initialized")
    return event_publisher


async def get_sse_manager() -> SSEManager:
    """Get SSE manager instance."""
    if sse_manager is None:
        raise RuntimeError("SSE manager not initialized")
    return sse_manager


async def startup_event() -> None:
    """Initialize the system on startup."""
    global redis_client, job_manager, event_publisher, background_worker, sse_manager

    # Initialize Redis client
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("🔗 Connected to Redis")
    except Exception as e:
        logger.error(f"🔗❌ Failed to connect to Redis: {e}")
        raise

    # Initialize components
    job_manager = JobManager(redis_client)
    event_publisher = EventPublisher(redis_client)
    sse_manager = SSEManager(redis_client)
    background_worker = BackgroundWorker(job_manager, event_publisher)

    # Start background worker
    asyncio.create_task(background_worker.start())
    logger.info("🎯 Background queue management system initialized")


async def shutdown_event() -> None:
    """Cleanup on shutdown."""
    global background_worker

    if background_worker:
        await background_worker.stop()

    if redis_client:
        await redis_client.close()

    logger.info("🔄 Background queue management system shutdown")


# FastAPI app
app = FastAPI(
    title="Background Queue Management",
    description="Background job processing with SSE streaming",
    version="1.0.0",
)

app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)


@app.post("/jobs", response_model=JobResponse)
async def submit_job(request: JobRequest) -> JobResponse:
    """Submit a new job for processing."""
    try:
        job_manager = await get_job_manager()
        job = await job_manager.create_job(request)

        return JobResponse(job_id=job.id, status=job.status, message="Job submitted successfully")
    except Exception as e:
        logger.error(f"📝❌ Failed to submit job: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit job")


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get the status of a specific job."""
    try:
        job_manager = await get_job_manager()
        job = await job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return {
            "job_id": job.id,
            "task_type": job.task_type,
            "status": job.status,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "result": job.result,
            "error": job.error,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"📊❌ Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job status")


@app.get("/jobs/{job_id}/events")
async def stream_job_events(job_id: str) -> StreamingResponse:
    """Stream SSE events for a specific job."""
    try:
        sse_manager = await get_sse_manager()
        queue: asyncio.Queue[JobEvent] = await sse_manager.subscribe_to_job(job_id)

        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                while True:
                    event = await queue.get()
                    yield f"data: {event.model_dump_json()}\n\n"
            except asyncio.CancelledError:
                logger.info(f"📡❌ SSE connection cancelled for job {job_id}")
            except Exception as e:
                logger.error(f"📡❌ SSE error for job {job_id}: {e}")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )
    except Exception as e:
        logger.error(f"📡❌ Failed to create SSE stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to create event stream")


@app.get("/events/broadcast")
async def stream_broadcast_events() -> StreamingResponse:
    """Stream broadcast events to all clients."""
    try:
        sse_manager = await get_sse_manager()
        queue: asyncio.Queue[JobEvent] = await sse_manager.subscribe_to_broadcast()

        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                while True:
                    event = await queue.get()
                    yield f"data: {event.model_dump_json()}\n\n"
            except asyncio.CancelledError:
                logger.info("📢📡❌ Broadcast SSE connection cancelled")
            except Exception as e:
                logger.error(f"📢📡❌ Broadcast SSE error: {e}")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )
    except Exception as e:
        logger.error(f"📢📡❌ Failed to create broadcast SSE stream: {e}")
        raise HTTPException(status_code=500, detail="Failed to create broadcast stream")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    try:
        redis_client = await get_redis_client()
        await redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        logger.error(f"💚❌ Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


if __name__ == "__main__":

    asyncio.run(serve(app, Config()))  # type: ignore
