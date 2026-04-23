# 📸 SedhotG

Async REST API — download Instagram posts, reels, profile pics, highlights.
Stack: **FastAPI** + **Redis queue** + **MongoDB** + **InstaLoader**.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                     FastAPI App                        │
│  POST /api/v1/downloads  →  DownloadService  →  Redis  │
│  GET  /api/v1/downloads/{id}  ←  MongoDB               │
└────────────────┬───────────────────────────────────────┘
                 │  asyncio worker (built-in)
                 ▼
        InstaLoaderService
                 │
         ┌───────┴───────┐
         │   Downloads   │  → /data/downloads
         └───────────────┘
```

| Layer | Tech |
|---|---|
| API | FastAPI 0.115 |
| Queue | Redis 7 (BLPOP/RPUSH) |
| DB | MongoDB 7 via Motor |
| Scraper | InstaLoader 4.15 |
| Runtime | Docker + Compose |

---

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/liulinnuha/SedhotGram.git
cd instagram-downloader
cp .env.example .env
# Edit .env — set INSTAGRAM_USERNAME / PASSWORD for private content
```

### 2. Run

```bash
# Production
docker compose up -d

# Dev (adds Mongo Express on :8081)
docker compose --profile dev up -d
```

### 3. Verify

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.0"}
```

Docs → **http://localhost:8000/docs**

---

## Instagram Login / Session

InstaLoader supports three auth modes. Use credentials for private content or to avoid rate limits.

### Option A — Username + Password (`.env`)

```env
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password
```

On startup the service logs in and saves session to `INSTALOADER_SESSION_FILE`.

### Option B — Pre-bake session file with InstaLoader CLI

Run once on your host machine, then mount the session file into the container.

```bash
# Install instaloader locally
pip install instaloader

# Log in — saves session to ~/.config/instaloader/session-<username>
instaloader --login your_username

#If that fails, try importing from the browser.
#Supported browsers: Arc, Brave, Chrome, Chromium, Edge, Firefox, LibreWolf, Opera, Opera_GX, Safari, and Vivaldi.
instaloader --load-cookies BROWSER-NAME

# Copy session file to project
cp ~/.config/instaloader/session-your_username ./instaloader_session
```

Mount in `docker-compose.yml`:

```yaml
api:
  volumes:
    - ./instaloader_session:/tmp/instaloader_session
```

Set in `.env`:

```env
INSTALOADER_SESSION_FILE=/tmp/instaloader_session
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=   # leave blank — session file used instead
```

### Option C — Anonymous (default)

Leave `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` blank.
Public content only. Rate limits apply.

### Session load order

```
session file exists → load it
  ↓ fail / missing
username + password set → login → save session
  ↓ neither
anonymous mode
```

---

## API Reference

### Get media URLs (no download)

```http
GET /api/v1/downloads/urls?url=https://www.instagram.com/p/ABC123/
```

Returns CDN URLs only — nothing saved locally. Supports single image, video, sidecar.

**Response `200`:**
```json
{
  "shortcode": "ABC123",
  "owner_username": "nasa",
  "caption": "...",
  "media_type": "sidecar",
  "likes": 42000,
  "taken_at": "2026-04-01T10:00:00Z",
  "media": [
    { "index": 0, "media_type": "image", "url": "https://cdn.instagram.com/..." }
  ]
}
```

### Download immediately (sync)

```http
POST /api/v1/downloads/direct
Content-Type: application/json

{ "url": "https://www.instagram.com/p/ABC123/" }
```

Blocks until complete. Returns files + elapsed time. Posts/reels only.

**Response `200`:**
```json
{
  "job_id": "...",
  "shortcode": "ABC123",
  "owner_username": "nasa",
  "files": [...],
  "duration_seconds": 3.14
}
```

### Submit async job

```http
POST /api/v1/downloads/
Content-Type: application/json

{ "url": "https://www.instagram.com/p/ABC123/", "max_posts": 50 }
```

**Response `202`:**
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

**Response `200`:**
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

### List jobs

```http
GET /api/v1/downloads/?status=completed&page=1&page_size=20
```

### Delete job record

```http
DELETE /api/v1/downloads/{job_id}
```

### Queue stats

```http
GET /api/v1/queue/stats
DELETE /api/v1/queue/flush
```

---

## Supported URL Types

| Type | Example |
|---|---|
| Post | `instagram.com/p/<shortcode>/` |
| Reel | `instagram.com/reel/<shortcode>/` |
| Profile pic | `instagram.com/<username>/` |
| Profile all posts | `instagram.com/<username>/posts/` |
| Highlight | `instagram.com/stories/highlights/<id>/` |
| Story | `instagram.com/stories/<username>/<id>/` |

> Private content requires valid credentials in `.env`.

---

## Project Structure

```
instagram-downloader/
├── app/
│   ├── main.py                     # FastAPI app, lifespan hooks
│   ├── api/v1/
│   │   ├── router.py               # Aggregates routers
│   │   └── endpoints/
│   │       ├── downloads.py        # Download CRUD + direct + urls
│   │       └── queue.py            # Queue stats/flush
│   ├── core/
│   │   ├── config.py               # Settings (pydantic-settings)
│   │   ├── exceptions.py           # Custom HTTP exceptions
│   │   └── logging.py              # Logging setup
│   ├── db/
│   │   ├── mongodb.py              # Motor client + indexes
│   │   └── redis.py                # Redis async client
│   ├── models/job.py               # DownloadJob document model
│   ├── schemas/job.py              # Request/response schemas
│   ├── services/
│   │   ├── instaloader_service.py  # InstaLoader wrapper
│   │   ├── job_repository.py       # MongoDB data access
│   │   └── download_service.py     # Orchestration layer
│   ├── workers/queue_manager.py    # Redis queue + asyncio worker
│   └── utils/
│       ├── url_utils.py
│       └── file_utils.py
├── tests/test_api.py
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
| `INSTAGRAM_USERNAME` | *(empty)* | IG login username |
| `INSTAGRAM_PASSWORD` | *(empty)* | IG login password |
| `INSTALOADER_SESSION_FILE` | `/tmp/instaloader_session` | Session file path |
| `DOWNLOAD_DIR` | `/data/downloads` | Local file storage path |
| `MEDIA_BASE_URL` | `http://localhost:8000/media` | Public URL prefix for files |
| `DEBUG` | `false` | Enable debug logging |

---

## Job Lifecycle

```
PENDING → PROCESSING → COMPLETED
                    ↘ FAILED (after max retries)
```

Transient failures → re-queued with incremented retry counter.
After `QUEUE_MAX_RETRIES` → permanently `FAILED`.
