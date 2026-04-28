from fastapi import APIRouter, Query

from app.schemas.job import DirectDownloadResponse, MediaURLResponse, MediaURLResponse
from app.services.download_service import download_service

router = APIRouter(prefix="/direct", tags=["Direct Downloads"])

@router.get("/post", response_model=DirectDownloadResponse, summary="Download a post directly")
async def download_post(
    url: str = Query(..., description="Instagram post URL — instagram.com/p/<shortcode>/"),
) -> DirectDownloadResponse:
    """
    Download a single Instagram post (image or sidecar) synchronously.
    Blocks until complete. Returns files + elapsed time.
    """
    return await download_service.download_direct_by_type(url, expected_prefix="/p/")

@router.get(
    "/reel",
    response_model=DirectDownloadResponse,
    summary="Download a reel directly",
)
async def download_reel(
    url: str = Query(..., description="Instagram reel URL - instagram.com/reel/<shortcode>/"),
) -> DirectDownloadResponse:
    """
    Download a single Instagram reel synchronously.
    Blocks until complete. Returns files + elapsed time.
    """
    return await download_service.download_direct_by_type(url, expected_prefix="/reel/")

@router.get(
    "/profile",
    response_model=DirectDownloadResponse,
    summary="Download a profile directly",
)
async def download_profile(
    url: str = Query(..., description="Instagram profile URL - instagram.com/<username>/"),
) -> DirectDownloadResponse:
    """
    Download a single Instagram profile synchronously.
    Blocks until complete. Returns files + elapsed time.
    """
    return await download_service.download_profile_direct(url)

@router.get(
    "/highlight",
    response_model=DirectDownloadResponse,
    summary="Download a highlight directly",
)
async def download_highlight(
    url: str = Query(..., description="Instagram highlight URL - instagram.com/<username>/highlights/<shortcode>/"),
) -> DirectDownloadResponse:
    """
    Download a single Instagram highlight synchronously.
    Blocks until complete. Returns files + elapsed time.
    """
    return await download_service.download_direct_highlight_direct(url)
