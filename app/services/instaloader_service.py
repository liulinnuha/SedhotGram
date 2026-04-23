import logging
import os
import re
from pathlib import Path
from typing import List, Tuple

import instaloader
from instaloader import Post, Profile, Highlight

from app.core.config import settings
from app.core.exceptions import InstaLoaderError, InvalidInstagramURL
from app.models.job import MediaFile, MediaType

logger = logging.getLogger(__name__)

# Regex patterns for Instagram URL types
_PATTERNS = {
    MediaType.POST:      re.compile(r"instagram\.com/p/([A-Za-z0-9_-]+)"),
    MediaType.REEL:      re.compile(r"instagram\.com/reel/([A-Za-z0-9_-]+)"),
    MediaType.STORY:     re.compile(r"instagram\.com/stories/([^/]+)/(\d+)"),
    MediaType.PROFILE_ALL: re.compile(r"instagram\.com/([^/?#]+)/(?:posts)?/?$"),  # ← add
    MediaType.PROFILE:     re.compile(r"instagram\.com/([^/?#]+)/?$"),
    MediaType.HIGHLIGHT: re.compile(r"instagram\.com/stories/highlights/(\d+)"),
}


class InstaLoaderService:
    """Wraps instaloader with async-friendly, stateless methods."""

    def __init__(self):
        self._loader = instaloader.Instaloader(
            download_pictures=True,
            download_videos=True,
            # download_video_thumbnails=False,
            save_metadata=False,
            post_metadata_txt_pattern="",
            quiet=True,
            sleep=True,
        )
        self._authenticated = False
        self._try_login()

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _try_login(self) -> None:
        session_file = settings.INSTALOADER_SESSION_FILE
        username = settings.INSTAGRAM_USERNAME
        password = settings.INSTAGRAM_PASSWORD

        if os.path.exists(session_file):
            try:
                self._loader.load_session_from_file(username, session_file)
                self._authenticated = True
                logger.info("InstaLoader: session loaded from file.")
                return
            except Exception as exc:
                logger.warning("Could not load session file: %s", exc)

        if username and password:
            try:
                self._loader.login(username, password)
                self._loader.save_session_to_file(session_file)
                self._authenticated = True
                logger.info("InstaLoader: logged in as %s.", username)
            except Exception as exc:
                logger.warning("InstaLoader login failed: %s", exc)
        else:
            logger.info("InstaLoader: running anonymously (limited access).")

    # ── URL Parsing ────────────────────────────────────────────────────────────

    @staticmethod
    def detect_media_type(url: str) -> Tuple[MediaType, str]:
        """Return (MediaType, shortcode_or_identifier) for the given URL."""
        for media_type, pattern in _PATTERNS.items():
            m = pattern.search(url)
            if m:
                return media_type, m.group(1)
        raise InvalidInstagramURL(url)

    # ── Download helpers ────────────────────────────────────────────────────────

    def _target_dir(self, shortcode: str) -> Path:
        path = Path(settings.DOWNLOAD_DIR) / shortcode
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _collect_files(self, directory: Path) -> List[MediaFile]:
        files: List[MediaFile] = []
        shortcode = directory.name
        for f in sorted(directory.iterdir()):
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                mtype = "image"
            elif f.suffix.lower() in {".mp4", ".mov"}:
                mtype = "video"
            else:
                continue
            files.append(
                MediaFile(
                    filename=f.name,
                    media_type=mtype,
                    local_path=str(f),
                    url=f"{settings.MEDIA_BASE_URL}/{shortcode}/{f.name}",
                    size_bytes=f.stat().st_size,
                )
            )
        return files

    # ── Public download methods ─────────────────────────────────────────────────

    def download_post(self, shortcode: str) -> Tuple[List[MediaFile], dict]:
        """Download a single post or reel by shortcode."""
        try:
            post = Post.from_shortcode(self._loader.context, shortcode)
            target = self._target_dir(shortcode)
            self._loader.download_post(post, target)
            files = self._collect_files(target)
            meta = {
                "owner_username": post.owner_username,
                "caption": post.caption or "",
                "shortcode": shortcode,
            }
            return files, meta
        except instaloader.exceptions.InstaloaderException as exc:
            raise InstaLoaderError(str(exc)) from exc

    def download_profile_all(self, username: str, max_posts: int = 50) -> Tuple[List[MediaFile], dict]:
        """Download all posts from a user's profile."""
        try:
            profile = Profile.from_username(self._loader.context, username)
            target = self._target_dir(f"{username}_all")
            count = 0
            for post in profile.get_posts():
                if count >= max_posts:
                    break
                self._loader.download_post(post, target)
                count += 1
            files = self._collect_files(target)
            return files, {
                "owner_username": username,
                "shortcode": f"{username}_all",
                "caption": f"All posts from @{username} ({count} downloaded)",
            }
        except instaloader.exceptions.InstaloaderException as exc:
            raise InstaLoaderError(str(exc)) from exc

    def download_profile_pic(self, username: str) -> Tuple[List[MediaFile], dict]:
        """Download a user's profile picture."""
        try:
            profile = Profile.from_username(self._loader.context, username)
            target = self._target_dir(username)
            # Save original dirname and temporarily switch so InstaLoader
            # writes into our target directory
            original_dir = os.getcwd()
            os.chdir(str(target.parent))
            try:
                self._loader.download_profile_pic(profile)
            finally:
                os.chdir(original_dir)
            files = self._collect_files(target)
            return files, {"owner_username": username, "shortcode": username, "caption": ""}
        except instaloader.exceptions.InstaloaderException as exc:
            raise InstaLoaderError(str(exc)) from exc

    def download_highlight(self, highlight_id: str) -> Tuple[List[MediaFile], dict]:
        """Download a highlight reel."""
        try:
            highlights = [
                h for h in self._loader.get_highlights(user=highlight_id)
                if h.unique_id == int(highlight_id)
            ]
            if not highlights:
                raise InstaLoaderError(f"Highlight {highlight_id} not found.")
            highlight: Highlight = highlights[0]
            target = self._target_dir(f"highlight_{highlight_id}")
            for item in highlight.get_items():
                self._loader.download_storyitem(item, target)
            files = self._collect_files(target)
            return files, {"owner_username": highlight.owner_username, "shortcode": highlight_id, "caption": ""}
        except InstaLoaderError:
            raise
        except instaloader.exceptions.InstaloaderException as exc:
            raise InstaLoaderError(str(exc)) from exc

    def get_media_urls(self, shortcode: str) -> dict:
        """
        Fetch direct CDN URLs from Instagram without downloading anything locally.
        Works for single images, videos, and sidecars (multi-image posts).
        """
        try:
            post = Post.from_shortcode(self._loader.context, shortcode)

            media_items = []
            index = 0

            if post.typename == "GraphSidecar":
                # Multi-image/video post
                for node in post.get_sidecar_nodes():
                    if node.is_video:
                        media_items.append({
                            "index": index,
                            "media_type": "video",
                            "url": node.video_url,
                            "thumbnail_url": node.display_url,
                            "width": None,
                            "height": None,
                        })
                    else:
                        media_items.append({
                            "index": index,
                            "media_type": "image",
                            "url": node.display_url,
                            "thumbnail_url": None,
                            "width": None,
                            "height": None,
                        })
                    index += 1
            elif post.is_video:
                media_items.append({
                    "index": 0,
                    "media_type": "video",
                    "url": post.video_url,
                    "thumbnail_url": post.url,       # thumbnail is the cover image
                    "width": None,
                    "height": None,
                })
            else:
                media_items.append({
                    "index": 0,
                    "media_type": "image",
                    "url": post.url,
                    "thumbnail_url": None,
                    "width": None,
                    "height": None,
                })

            return {
                "shortcode": shortcode,
                "owner_username": post.owner_username,
                "caption": post.caption or "",
                "likes": post.likes,
                "media_type": post.typename.replace("Graph", "").lower(),  # "image" | "video" | "sidecar"
                "taken_at": post.date_utc,
                "media": media_items,
            }
        except instaloader.exceptions.InstaloaderException as exc:
            raise InstaLoaderError(str(exc)) from exc


    def download_post_direct(self, shortcode: str) -> Tuple[List[MediaFile], dict, float]:
        """
        Download a post synchronously and return results immediately.
        Same as download_post() but also returns elapsed time.
        """
        import time
        start = time.perf_counter()
        files, meta = self.download_post(shortcode)
        elapsed = round(time.perf_counter() - start, 2)
        return files, meta, elapsed


# Singleton instance
instaloader_service = InstaLoaderService()
