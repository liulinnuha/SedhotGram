import logging
import uuid
import asyncio

from app.core.config import settings
from app.core.exceptions import DownloadJobNotFound, InvalidInstagramURL
from app.db.mongodb import get_db
from app.models.job import DownloadJob, JobStatus, MediaType
from app.schemas.job import (
    DownloadRequest,
    JobCreatedResponse,
    JobListResponse,
    JobStatusResponse,
    DeleteJobResponse,
    MediaURLResponse,
    MediaURLItem,
    DirectDownloadResponse,
)
from app.services.instaloader_service import instaloader_service
from app.services.job_repository import JobRepository
from app.workers.queue_manager import enqueue_job

logger = logging.getLogger(__name__)


class DownloadService:
    async def _repo(self) -> JobRepository:
        return JobRepository(get_db())

    # ── Async queue jobs ──────────────────────────────────────────────────────

    async def create_job(self, request: DownloadRequest) -> JobCreatedResponse:
        media_type, shortcode = instaloader_service.detect_media_type(request.url)
        job = DownloadJob(
            instagram_url=request.url,
            media_type=media_type,
            shortcode=shortcode,
            max_posts=request.max_posts,
        )
        repo = await self._repo()
        await repo.create(job)
        await enqueue_job(job.job_id)
        logger.info("Queued job %s (%s: %s)", job.job_id, media_type, shortcode)
        return JobCreatedResponse(job_id=job.job_id, status=job.status)

    async def get_job(self, job_id: str) -> JobStatusResponse:
        repo = await self._repo()
        job = await repo.get_by_id(job_id)
        if not job:
            raise DownloadJobNotFound(job_id)
        return JobStatusResponse(**job.model_dump())

    async def list_jobs(
        self,
        status: JobStatus | None,
        page: int,
        page_size: int,
    ) -> JobListResponse:
        repo = await self._repo()
        jobs = await repo.list_jobs(status=status, page=page, page_size=page_size)
        total = await repo.count(status=status)
        return JobListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[JobStatusResponse(**j.model_dump()) for j in jobs],
        )

    async def delete_job(self, job_id: str) -> DeleteJobResponse:
        repo = await self._repo()
        deleted = await repo.delete(job_id)
        if not deleted:
            raise DownloadJobNotFound(job_id)
        return DeleteJobResponse(job_id=job_id, deleted=True, message="Job deleted.")

    # Called by the worker
    async def process_job(self, job_id: str) -> None:
        repo = await self._repo()
        job = await repo.get_by_id(job_id)
        if not job:
            logger.warning("Worker: job %s not found, skipping.", job_id)
            return

        await repo.update_status(job_id, JobStatus.PROCESSING)
        logger.info(
            "Processing job %s | type=%s | shortcode=%s",
            job_id, job.media_type, job.shortcode,
        )

        try:
            if job.media_type in (MediaType.POST, MediaType.REEL):
                files, meta = instaloader_service.download_post(job.shortcode)
            elif job.media_type == MediaType.PROFILE:
                files, meta = instaloader_service.download_profile_pic(job.shortcode)
            elif job.media_type == MediaType.PROFILE_ALL:
                files, meta = instaloader_service.download_profile_all(job.shortcode, job.max_posts)
            elif job.media_type == MediaType.HIGHLIGHT:
                files, meta = instaloader_service.download_highlight(job.shortcode)
            else:
                raise ValueError(f"Unsupported media type: {job.media_type}")

            await repo.update_result(
                job_id=job_id,
                files=files,
                owner_username=meta.get("owner_username", ""),
                caption=meta.get("caption", ""),
                shortcode=meta.get("shortcode", job.shortcode),
            )
            logger.info("Job %s completed — %d file(s) downloaded.", job_id, len(files))

        except Exception as exc:
            retries = await repo.increment_retry(job_id)
            if retries >= settings.QUEUE_MAX_RETRIES:
                await repo.update_status(job_id, JobStatus.FAILED, str(exc))
                logger.error("Job %s FAILED after %d retries: %s", job_id, retries, exc)
            else:
                await repo.update_status(job_id, JobStatus.PENDING, str(exc))
                await asyncio.sleep(5)
                await enqueue_job(job_id)
                logger.warning("Job %s re-queued (attempt %d): %s", job_id, retries, exc)

    # ── URL-only (no download) ─────────────────────────────────────────────────

    async def get_media_urls(self, url: str) -> MediaURLResponse:
        media_type, shortcode = instaloader_service.detect_media_type(url)
        if media_type not in (MediaType.POST, MediaType.REEL):
            raise InvalidInstagramURL(url)
        result = await asyncio.to_thread(instaloader_service.get_media_urls, shortcode)
        return MediaURLResponse(
            shortcode=result["shortcode"],
            owner_username=result["owner_username"],
            caption=result["caption"],
            media_type=result["media_type"],
            taken_at=result["taken_at"],
            likes=result["likes"],
            media=[MediaURLItem(**item) for item in result["media"]],
        )

    # ── Direct (sync) downloads ───────────────────────────────────────────────

    async def download_direct(self, url: str) -> DirectDownloadResponse:
        """Original generic direct download (POST /downloads/direct)."""
        media_type, shortcode = instaloader_service.detect_media_type(url)
        if media_type not in (MediaType.POST, MediaType.REEL):
            raise InvalidInstagramURL(url)
        files, meta, elapsed = await asyncio.to_thread(
            instaloader_service.download_post_direct, shortcode
        )
        return DirectDownloadResponse(
            job_id=str(uuid.uuid4()),
            shortcode=shortcode,
            owner_username=meta.get("owner_username", ""),
            caption=meta.get("caption", ""),
            files=files,
            duration_seconds=elapsed,
        )

    async def download_direct_by_type(self, url: str, expected_prefix: str) -> DirectDownloadResponse:
        """
        Used by /direct/post and /direct/reel.
        Validates that the URL matches the expected path prefix before downloading.
        """
        if expected_prefix not in url:
            raise InvalidInstagramURL(url)
        return await self.download_direct(url)

    async def download_profile_direct(self, url: str) -> DirectDownloadResponse:
        """Used by GET /direct/profile."""
        import time
        media_type, username = instaloader_service.detect_media_type(url)
        if media_type not in (MediaType.PROFILE, MediaType.PROFILE_ALL):
            raise InvalidInstagramURL(url)

        start = time.perf_counter()
        files, meta = await asyncio.to_thread(
            instaloader_service.download_profile_pic, username
        )
        elapsed = round(time.perf_counter() - start, 2)

        return DirectDownloadResponse(
            job_id=str(uuid.uuid4()),
            shortcode=username,
            owner_username=meta.get("owner_username", username),
            caption=meta.get("caption", ""),
            files=files,
            duration_seconds=elapsed,
        )

    async def download_highlight_direct(self, url: str) -> DirectDownloadResponse:
        """Used by GET /direct/highlight."""
        import time
        media_type, highlight_id = instaloader_service.detect_media_type(url)
        if media_type != MediaType.HIGHLIGHT:
            raise InvalidInstagramURL(url)

        start = time.perf_counter()
        files, meta = await asyncio.to_thread(
            instaloader_service.download_highlight, highlight_id
        )
        elapsed = round(time.perf_counter() - start, 2)

        return DirectDownloadResponse(
            job_id=str(uuid.uuid4()),
            shortcode=highlight_id,
            owner_username=meta.get("owner_username", ""),
            caption=meta.get("caption", ""),
            files=files,
            duration_seconds=elapsed,
        )


download_service = DownloadService()
