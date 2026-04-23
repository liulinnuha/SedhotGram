import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    global _client, _db
    logger.info("Connecting to MongoDB...")
    _client = AsyncIOMotorClient(settings.MONGODB_URL)
    _db = _client[settings.MONGODB_DB_NAME]
    await _db.command("ping")
    logger.info("MongoDB connected: %s / %s", settings.MONGODB_URL, settings.MONGODB_DB_NAME)

    # Ensure indexes
    await _db["download_jobs"].create_index("job_id", unique=True)
    await _db["download_jobs"].create_index("status")
    await _db["download_jobs"].create_index("created_at")


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed.")


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialised. Call connect_db() first.")
    return _db
