from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, field_validator
from app.models.job import JobStatus, MediaType, MediaFile


# ── Request ──────────────────────────────────────────────────────────────────

class DownloadRequest(BaseModel):
    url: str
    max_posts: int = 50

    @field_validator("url")
    @classmethod
    def must_be_instagram(cls, v: str) -> str:
        if "instagram.com" not in v:
            raise ValueError("URL must be an Instagram URL.")
        return v.strip()


# ── Responses ─────────────────────────────────────────────────────────────────

class JobCreatedResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str = "Download job queued successfully."


class JobStatusResponse(BaseModel):
    job_id: str
    instagram_url: str
    status: JobStatus
    media_type: Optional[MediaType] = None
    shortcode: Optional[str] = None
    owner_username: Optional[str] = None
    caption: Optional[str] = None
    files: List[MediaFile] = []
    error_message: Optional[str] = None
    retries: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[JobStatusResponse]


class DeleteJobResponse(BaseModel):
    job_id: str
    deleted: bool
    message: str

class MediaURLItem(BaseModel):
    index: int
    media_type: str
    url: str
    thumbnail_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None

class MediaURLResponse(BaseModel):
    shortcode: str
    owner_username: str
    caption: Optional[str] = None
    media_type: str
    likes: int
    taken_at: Optional[datetime] = None
    media: List[MediaURLItem] = []

class DirectDownloadResponse(BaseModel):
    job_id: str
    shortcode: str
    owner_username: str
    caption: Optional[str] = None
    files: List[MediaFile] = []
    duration_seconds: float
