import logging
import sys
from app.core.config import settings


def setup_logging() -> None:
    level = logging.DEBUG if settings.DEBUG else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Silence noisy third-party loggers
    for noisy in ("urllib3", "asyncio", "instaloader"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("pymongo").setLevel(logging.WARNING)
