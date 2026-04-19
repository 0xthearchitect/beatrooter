from __future__ import annotations

import os
from pathlib import Path

from .runtime import DisabledNDCClientRuntime, NDCClientRuntime, create_default_runtime


_default_runtime: NDCClientRuntime | DisabledNDCClientRuntime | None = None
_default_scheduler = None


def get_default_ndc_runtime() -> NDCClientRuntime | DisabledNDCClientRuntime:
    global _default_runtime
    if _default_runtime is None:
        _default_runtime = create_default_runtime(_default_ndc_home())
    return _default_runtime


def ensure_default_ndc_scheduler():
    global _default_scheduler
    if _default_scheduler is not None:
        return _default_scheduler

    runtime = get_default_ndc_runtime()
    if not getattr(runtime, "enabled", True):
        return None

    try:
        from PyQt6.QtCore import QCoreApplication
    except Exception:
        return None

    app = QCoreApplication.instance()
    if app is None:
        return None

    from .qt_scheduler import NDCFlushScheduler

    _default_scheduler = NDCFlushScheduler(runtime, parent=app)
    _default_scheduler.start()
    return _default_scheduler


def _default_ndc_home() -> Path:
    override = os.environ.get("BEATROOTER_NDC_HOME", "").strip()
    if override:
        candidate = Path(override).expanduser().resolve()
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate

    primary = Path.home() / ".beatrooter" / "ndc"
    try:
        primary.mkdir(parents=True, exist_ok=True)
        return primary
    except OSError:
        fallback = Path("/tmp") / "beatrooter_ndc"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
