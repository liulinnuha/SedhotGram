import re
from typing import Optional


INSTAGRAM_SHORTCODE_RE = re.compile(r"instagram\.com/(?:p|reel)/([A-Za-z0-9_-]+)")


def extract_shortcode(url: str) -> Optional[str]:
    """Extract post/reel shortcode from an Instagram URL."""
    m = INSTAGRAM_SHORTCODE_RE.search(url)
    return m.group(1) if m else None


def is_valid_instagram_url(url: str) -> bool:
    return "instagram.com" in url


def sanitize_caption(caption: Optional[str], max_length: int = 500) -> str:
    if not caption:
        return ""
    caption = caption.strip().replace("\n", " ")
    return caption[:max_length] + ("…" if len(caption) > max_length else "")
