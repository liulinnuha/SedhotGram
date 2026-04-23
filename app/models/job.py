from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaType(str, Enum):
    POST = "post"
    REEL = "reel"
    STORY = "story"
    PROFILE = "profile"
    HIGHLIGHT = "highlight"
    PROFILE_ALL = "profile_all"


class MediaFile(BaseModel):
    filename: str
    media_type: str          # "image" | "video"
    url: Optional[str] = None
    local_path: Optional[str] = None
    size_bytes: Optional[int] = None


class DownloadJob(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    instagram_url: str
    max_posts: int = 50
    media_type: Optional[MediaType] = None
    status: JobStatus = JobStatus.PENDING
    retries: int = 0
    files: List[MediaFile] = []
    error_message: Optional[str] = None
    shortcode: Optional[str] = None
    owner_username: Optional[str] = None
    caption: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def to_document(self) -> dict:
        doc = self.model_dump()
        doc["created_at"] = self.created_at
        doc["updated_at"] = self.updated_at
        doc["completed_at"] = self.completed_at
        return doc
