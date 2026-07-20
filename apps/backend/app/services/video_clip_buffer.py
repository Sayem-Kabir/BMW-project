"""Rolling in-memory frame buffer for 30-second safety clips (Module 4E)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock


@dataclass(frozen=True)
class BufferedFrame:
    timestamp: datetime
    data: bytes


class VideoClipBuffer:
    """Store recent JPEG frames for later MP4 materialization."""

    def __init__(self, *, duration_seconds: float = 30.0, fps: float = 30.0) -> None:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        if fps <= 0:
            raise ValueError("fps must be positive")
        self.duration_seconds = float(duration_seconds)
        self.fps = float(fps)
        self._maxlen = max(1, int(self.duration_seconds * self.fps) + 2)
        self._frames: deque[BufferedFrame] = deque(maxlen=self._maxlen)
        self._lock = RLock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._frames)

    def clear(self) -> None:
        with self._lock:
            self._frames.clear()

    def append_jpeg(self, data: bytes, *, timestamp: datetime | None = None) -> None:
        if not data:
            return
        moment = timestamp or datetime.now(timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        with self._lock:
            self._frames.append(BufferedFrame(timestamp=moment, data=data))

    def collect_clip(
        self,
        *,
        duration_seconds: float | None = None,
        anchor: datetime | None = None,
    ) -> list[bytes]:
        """Return JPEG frames covering the last ``duration_seconds`` window."""
        window = duration_seconds if duration_seconds is not None else self.duration_seconds
        end = anchor or datetime.now(timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        start = end.timestamp() - float(window)

        with self._lock:
            frames = [
                frame.data
                for frame in self._frames
                if frame.timestamp.timestamp() >= start
            ]
        return frames
