from fastapi import APIRouter
from app.api.v1.endpoints.downloads import router as downloads_router
from app.api.v1.endpoints.queue import router as queue_router

api_router = APIRouter()
api_router.include_router(downloads_router)
api_router.include_router(queue_router)
