import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.job import DownloadJob, JobStatus, MediaType
from app.schemas.job import JobCreatedResponse, JobStatusResponse


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── POST /api/v1/downloads/ ───────────────────────────────────────────────────

@patch("app.api.v1.endpoints.downloads.download_service")
def test_create_download_success(mock_svc, client):
    mock_svc.create_job = AsyncMock(
        return_value=JobCreatedResponse(
            job_id="abc-123",
            status=JobStatus.PENDING,
        )
    )
    resp = client.post(
        "/api/v1/downloads/",
        json={"url": "https://www.instagram.com/p/ABC123/"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["job_id"] == "abc-123"
    assert data["status"] == "pending"


def test_create_download_invalid_url(client):
    resp = client.post(
        "/api/v1/downloads/",
        json={"url": "https://www.twitter.com/p/ABC123/"},
    )
    assert resp.status_code == 422


# ── GET /api/v1/downloads/{job_id} ───────────────────────────────────────────

@patch("app.api.v1.endpoints.downloads.download_service")
def test_get_download_not_found(mock_svc, client):
    from app.core.exceptions import DownloadJobNotFound
    mock_svc.get_job = AsyncMock(side_effect=DownloadJobNotFound("missing-id"))
    resp = client.get("/api/v1/downloads/missing-id")
    assert resp.status_code == 404


# ── URL Utils ─────────────────────────────────────────────────────────────────

def test_extract_shortcode():
    from app.utils.url_utils import extract_shortcode
    assert extract_shortcode("https://www.instagram.com/p/ABC123/") == "ABC123"
    assert extract_shortcode("https://www.instagram.com/reel/XYZ789/") == "XYZ789"
    assert extract_shortcode("https://example.com") is None


def test_is_valid_instagram_url():
    from app.utils.url_utils import is_valid_instagram_url
    assert is_valid_instagram_url("https://www.instagram.com/p/ABC/") is True
    assert is_valid_instagram_url("https://www.twitter.com/p/ABC/") is False


def test_sanitize_caption():
    from app.utils.url_utils import sanitize_caption
    assert sanitize_caption(None) == ""
    assert sanitize_caption("Hello") == "Hello"
    long = "x" * 600
    result = sanitize_caption(long)
    assert result.endswith("…")
    assert len(result) == 501


# ── InstaLoader service URL detection ────────────────────────────────────────

def test_detect_media_type_post():
    from app.services.instaloader_service import InstaLoaderService
    from app.core.exceptions import InvalidInstagramURL
    mt, sc = InstaLoaderService.detect_media_type("https://www.instagram.com/p/ABC123/")
    assert mt == MediaType.POST
    assert sc == "ABC123"


def test_detect_media_type_reel():
    from app.services.instaloader_service import InstaLoaderService
    mt, sc = InstaLoaderService.detect_media_type("https://www.instagram.com/reel/XYZ789/")
    assert mt == MediaType.REEL
    assert sc == "XYZ789"


def test_detect_media_type_invalid():
    from app.services.instaloader_service import InstaLoaderService
    from app.core.exceptions import InvalidInstagramURL
    with pytest.raises(InvalidInstagramURL):
        InstaLoaderService.detect_media_type("https://example.com/p/ABC")
