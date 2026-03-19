from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(level: str, directory: str) -> Path:
    log_dir = Path(directory)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "beatroot.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    return log_file

