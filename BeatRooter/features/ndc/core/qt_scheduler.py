from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer

from .runtime import NDCClientRuntime


class NDCFlushScheduler(QObject):
    def __init__(self, runtime: NDCClientRuntime, parent=None) -> None:
        super().__init__(parent)
        self.runtime = runtime
        self.timer = QTimer(self)
        self.timer.setInterval(int(self.runtime.flush_interval_seconds * 1000))
        self.timer.timeout.connect(self.flush_if_needed)

    def start(self) -> None:
        if not self.timer.isActive():
            self.timer.start()

    def stop(self) -> None:
        if self.timer.isActive():
            self.timer.stop()

    def flush_if_needed(self):
        health = self.runtime.health_snapshot()
        if int(health.get("ready_count", 0)) <= 0:
            return None
        return self.runtime.flush_once()

    def flush_now(self):
        return self.runtime.flush_once()

