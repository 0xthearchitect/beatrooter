from __future__ import annotations

import sys
from pathlib import Path


def get_beatroot_root() -> Path:
    return Path(__file__).resolve().parents[2] / "BeatRoot"


def is_beatroot_available() -> bool:
    return get_beatroot_root().exists()


def ensure_beatroot_on_path() -> Path:
    """Add the bundled BeatRoot package root to sys.path when present."""
    beatroot_root = get_beatroot_root()
    if not beatroot_root.exists():
        raise RuntimeError(f"BeatRoot service directory not found: {beatroot_root}")
    beatroot_root_str = str(beatroot_root)
    if beatroot_root_str not in sys.path:
        sys.path.insert(0, beatroot_root_str)
    return beatroot_root
