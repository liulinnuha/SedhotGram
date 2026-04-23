from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.mongodb import connect_db, close_db
from app.workers.queue_manager import start_worker, stop_worker

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    await start_worker()
    yield
    await stop_worker()
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    description="Instagram media downloader API with async queue processing",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
