from fastapi import APIRouter
from app.core.config import settings
from app.db.redis import get_redis

router = APIRouter(prefix="/queue", tags=["Queue"])


@router.get("/stats", summary="Queue statistics")
async def queue_stats() -> dict:
    redis = await get_redis()
    length = await redis.llen(settings.QUEUE_NAME)
    return {
        "queue_name": settings.QUEUE_NAME,
        "pending_jobs": length,
        "worker_concurrency": settings.WORKER_CONCURRENCY,
    }


@router.delete("/flush", summary="Flush all pending jobs from the queue")
async def flush_queue() -> dict:
    redis = await get_redis()
    count = await redis.llen(settings.QUEUE_NAME)
    await redis.delete(settings.QUEUE_NAME)
    return {"flushed": count, "message": f"Removed {count} pending job(s) from the queue."}
