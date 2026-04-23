import os
import shutil
from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def remove_dir(path: str | Path) -> bool:
    """Recursively remove a directory. Returns True if removed."""
    p = Path(path)
    if p.exists() and p.is_dir():
        shutil.rmtree(p)
        return True
    return False


def file_size_human(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.1f} TB"


def list_media_files(directory: str | Path) -> list[Path]:
    """Return all image/video files in a directory, sorted by name."""
    exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov"}
    return sorted(p for p in Path(directory).iterdir() if p.suffix.lower() in exts)
