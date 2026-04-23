import logging
from datetime import datetime, timezone
from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.job import DownloadJob, JobStatus, MediaFile

logger = logging.getLogger(__name__)


class JobRepository:
    COLLECTION = "download_jobs"

    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[self.COLLECTION]

    async def create(self, job: DownloadJob) -> DownloadJob:
        await self._col.insert_one(job.to_document())
        logger.debug("Job created: %s", job.job_id)
        return job

    async def get_by_id(self, job_id: str) -> Optional[DownloadJob]:
        doc = await self._col.find_one({"job_id": job_id})
        return DownloadJob(**doc) if doc else None

    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[DownloadJob]:
        query = {}
        if status:
            query["status"] = status
        cursor = (
            self._col.find(query)
            .sort("created_at", -1)
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        docs = await cursor.to_list(length=page_size)
        return [DownloadJob(**d) for d in docs]

    async def count(self, status: Optional[JobStatus] = None) -> int:
        query = {"status": status} if status else {}
        return await self._col.count_documents(query)

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        update: dict = {"status": status, "updated_at": now}
        if error_message is not None:
            update["error_message"] = error_message
        if status == JobStatus.COMPLETED:
            update["completed_at"] = now
        await self._col.update_one({"job_id": job_id}, {"$set": update})

    async def update_result(
        self,
        job_id: str,
        files: List[MediaFile],
        owner_username: str,
        caption: str,
        shortcode: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        await self._col.update_one(
            {"job_id": job_id},
            {
                "$set": {
                    "files": [f.model_dump() for f in files],
                    "owner_username": owner_username,
                    "caption": caption,
                    "shortcode": shortcode,
                    "status": JobStatus.COMPLETED,
                    "updated_at": now,
                    "completed_at": now,
                }
            },
        )

    async def increment_retry(self, job_id: str) -> int:
        result = await self._col.find_one_and_update(
            {"job_id": job_id},
            {"$inc": {"retries": 1}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            return_document=True,
        )
        return result["retries"] if result else 0

    async def delete(self, job_id: str) -> bool:
        result = await self._col.delete_one({"job_id": job_id})
        return result.deleted_count == 1
