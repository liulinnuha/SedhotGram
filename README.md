# 📸 Instagram Downloader API

Async REST API for downloading Instagram media (posts, reels, profile pictures, highlights) powered by **FastAPI**, **Redis queues**, **MongoDB**, and **InstaLoader**.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                     FastAPI App                        │
│  POST /downloads  →  DownloadService  →  Redis Queue   │
│  GET  /downloads/{id}  ←  MongoDB                     │
└────────────────┬───────────────────────────────────────┘
                 │  async worker (built-in)
                 ▼
        InstaLoaderService
                 │
         ┌───────┴───────┐
         │   Downloads   │   saved to /data/downloads
         └───────────────┘
```

| Layer | Technology |
|---|---|
| API framework | FastAPI 0.115 |
| Task queue | Redis 7 (BLPOP/RPUSH list) |
| Database | MongoDB 7 via Motor (async) |
| Instagram scraping | InstaLoader 4.13 |
| Container runtime | Docker + Docker Compose |

---

## Quick Start

### 1. Clone & configure

```bash
git clone <repo>
cd instagram-downloader
cp .env.example .env
# Edit .env — add INSTAGRAM_USERNAME / PASSWORD for private content
```

### 2. Run with Docker Compose

```bash
# Production stack (API + MongoDB + Redis)
docker compose up -d

# Development stack (adds Mongo Express UI on :8081)
docker compose --profile dev up -d
```

### 3. Verify

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0"}
```

### 4. Interactive API docs

Open **http://localhost:8000/docs** in your browser.

---

## API Reference

### Submit a download job

```http
POST /api/v1/downloads/
Content-Type: application/json

{ "url": "https://www.instagram.com/p/ABC123/" }
```

**Response `202 Accepted`:**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "pending",
  "message": "Download job queued successfully."
}
```

### Poll job status

```http
GET /api/v1/downloads/{job_id}
```

**Response `200 OK`:**
```json
{
  "job_id": "3fa85f64-...",
  "status": "completed",
  "media_type": "post",
  "owner_username": "nasa",
  "caption": "...",
  "files": [
    {
      "filename": "ABC123_1.jpg",
      "media_type": "image",
      "url": "http://localhost:8000/media/ABC123/ABC123_1.jpg",
      "size_bytes": 204800
    }
  ],
  "created_at": "2026-04-20T10:00:00Z",
  "completed_at": "2026-04-20T10:00:05Z"
}
```

### List all jobs

```http
GET /api/v1/downloads/?status=completed&page=1&page_size=20
```

### Delete a job record

```http
DELETE /api/v1/downloads/{job_id}
```

### Queue stats

```http
GET /api/v1/queue/stats
DELETE /api/v1/queue/flush   # flush pending jobs
```

---

## Supported URL Types

| Type | Example URL |
|---|---|
| Post | `instagram.com/p/<shortcode>/` |
| Reel | `instagram.com/reel/<shortcode>/` |
| Profile pic | `instagram.com/<username>/` |
| Highlight | `instagram.com/stories/highlights/<id>/` |

> **Note:** Stories and private content require valid Instagram credentials in `.env`.

---

## Project Structure

```
instagram-downloader/
├── app/
│   ├── main.py                  # FastAPI app, lifespan hooks
│   ├── api/
│   │   └── v1/
│   │       ├── router.py        # Aggregates all routers
│   │       └── endpoints/
│   │           ├── downloads.py # Download CRUD endpoints
│   │           └── queue.py     # Queue stats/flush
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── exceptions.py        # Custom HTTP exceptions
│   │   └── logging.py           # Logging setup
│   ├── db/
│   │   ├── mongodb.py           # Motor client + index setup
│   │   └── redis.py             # Redis async client
│   ├── models/
│   │   └── job.py               # DownloadJob document model
│   ├── schemas/
│   │   └── job.py               # Request/response Pydantic schemas
│   ├── services/
│   │   ├── instaloader_service.py  # InstaLoader wrapper
│   │   ├── job_repository.py       # MongoDB data access
│   │   └── download_service.py     # Orchestration layer
│   ├── workers/
│   │   └── queue_manager.py     # Redis queue + asyncio worker
│   └── utils/
│       ├── url_utils.py
│       └── file_utils.py
├── tests/
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── pytest.ini
```

---

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start dependencies only
docker compose up -d mongo redis

# Run API locally
uvicorn app.main:app --reload

# Run tests
pytest
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MONGODB_URL` | `mongodb://mongo:27017` | MongoDB connection string |
| `MONGODB_DB_NAME` | `instagram_downloader` | Database name |
| `REDIS_URL` | `redis://redis:6379` | Redis connection string |
| `QUEUE_NAME` | `instagram_download_queue` | Redis list key |
| `QUEUE_MAX_RETRIES` | `3` | Max retry attempts per job |
| `WORKER_CONCURRENCY` | `4` | Parallel downloads |
| `INSTAGRAM_USERNAME` | *(empty)* | Optional IG login |
| `INSTAGRAM_PASSWORD` | *(empty)* | Optional IG password |
| `DOWNLOAD_DIR` | `/data/downloads` | Local file storage path |
| `MEDIA_BASE_URL` | `http://localhost:8000/media` | Public URL prefix for files |
| `DEBUG` | `false` | Enable debug logging |

---

## Job Lifecycle

```
PENDING → PROCESSING → COMPLETED
                    ↘ FAILED (after max retries)
```

On transient failures the job is re-queued with an incremented retry counter. After `QUEUE_MAX_RETRIES` failures it is permanently marked `FAILED`.
