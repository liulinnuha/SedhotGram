import asyncio
import logging
from typing import Optional

from app.core.config import settings
from app.core.exceptions import QueueError
from app.db.redis import get_redis

logger = logging.getLogger(__name__)

_worker_task: Optional[asyncio.Task] = None


# ── Queue operations ──────────────────────────────────────────────────────────

async def enqueue_job(job_id: str) -> None:
    """Push a job_id onto the right side of the Redis list (RPUSH)."""
    try:
        redis = await get_redis()
        await redis.rpush(settings.QUEUE_NAME, job_id)
        logger.debug("Enqueued job %s → queue '%s'", job_id, settings.QUEUE_NAME)
    except Exception as exc:
        raise QueueError(f"Failed to enqueue job {job_id}: {exc}") from exc


async def dequeue_job(timeout: int = 5) -> Optional[str]:
    """
    Block-pop from the left side of the Redis list (BLPOP).
    Returns the job_id or None on timeout.
    """
    redis = await get_redis()
    result = await redis.blpop(settings.QUEUE_NAME, timeout=timeout)
    if result:
        _, job_id = result
        return job_id
    return None


# ── Worker loop ───────────────────────────────────────────────────────────────

async def _worker_loop() -> None:
    # Lazy import to avoid circular dependency
    from app.services.download_service import download_service

    logger.info(
        "Worker started | queue='%s' | concurrency=%d",
        settings.QUEUE_NAME,
        settings.WORKER_CONCURRENCY,
    )

    semaphore = asyncio.Semaphore(settings.WORKER_CONCURRENCY)

    async def process(job_id: str) -> None:
        async with semaphore:
            try:
                await download_service.process_job(job_id)
            except Exception as exc:
                logger.exception("Unhandled error processing job %s: %s", job_id, exc)

    while True:
        try:
            job_id = await dequeue_job(timeout=5)
            if job_id:
                asyncio.create_task(process(job_id))
        except asyncio.CancelledError:
            logger.info("Worker loop cancelled.")
            break
        except Exception as exc:
            logger.error("Worker loop error: %s", exc)
            await asyncio.sleep(2)


async def start_worker() -> None:
    global _worker_task
    _worker_task = asyncio.create_task(_worker_loop())
    logger.info("Worker task created.")


async def stop_worker() -> None:
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    logger.info("Worker stopped.")
