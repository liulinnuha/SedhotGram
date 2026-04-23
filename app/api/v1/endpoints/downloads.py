from typing import Optional

from fastapi import APIRouter, Query

from app.models.job import JobStatus
from app.schemas.job import (
    DownloadRequest,
    JobCreatedResponse,
    JobListResponse,
    JobStatusResponse,
    DeleteJobResponse,
    MediaURLResponse,
    DirectDownloadResponse
)
from app.services.download_service import download_service

router = APIRouter(prefix="/downloads", tags=["Downloads"])

@router.get(
    "/urls",
    response_model=MediaURLResponse,
    summary="Get media URLs without downloading",
)
async def get_media_urls(
    url: str = Query(..., description="Instagram post or reel URL"),
) -> MediaURLResponse:
    """
    Returns direct CDN URLs from Instagram for a post or reel.
    Nothing is saved locally — URLs are fetched and returned immediately.
    Supports single images, videos, and multi-image (sidecar) posts.
    """
    return await download_service.get_media_urls(url)


@router.post(
    "/direct",
    response_model=DirectDownloadResponse,
    summary="Download immediately without queue",
)
async def download_direct(request: DownloadRequest) -> DirectDownloadResponse:
    """
    Downloads a post or reel synchronously and returns the result immediately.
    Blocks until the download completes — use the queue endpoints for large batches.
    """
    return await download_service.download_direct(request.url)

@router.post(
    "/",
    response_model=JobCreatedResponse,
    status_code=202,
    summary="Submit a new download job",
)
async def create_download(request: DownloadRequest) -> JobCreatedResponse:
    """
    Submit an Instagram URL to be downloaded asynchronously.
    Supported types: posts, reels, profile pictures, highlights.
    """
    return await download_service.create_job(request)


@router.get(
    "/",
    response_model=JobListResponse,
    summary="List all download jobs",
)
async def list_downloads(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> JobListResponse:
    return await download_service.list_jobs(status=status, page=page, page_size=page_size)


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get a download job by ID",
)
async def get_download(job_id: str) -> JobStatusResponse:
    return await download_service.get_job(job_id)


@router.delete(
    "/{job_id}",
    response_model=DeleteJobResponse,
    summary="Delete a download job",
)
async def delete_download(job_id: str) -> DeleteJobResponse:
    return await download_service.delete_job(job_id)
