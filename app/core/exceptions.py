from fastapi import HTTPException, status


class DownloadJobNotFound(HTTPException):
    def __init__(self, job_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Download job '{job_id}' not found.",
        )

class InvalidInstagramURL(HTTPException):
    def __init__(self, url: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid or unsupported Instagram URL: {url}",
        )

class InstaLoaderError(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"InstaLoader service error: {message}",
        )

class QueueError(Exception):
    """Raised when queue operations fail."""
