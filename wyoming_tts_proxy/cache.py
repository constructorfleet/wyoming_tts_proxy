import hashlib
import logging
from pathlib import Path
from typing import List, Optional

from wyoming.event import Event, read_event, write_event

_LOGGER = logging.getLogger(__name__)


class AudioCache:
    def __init__(self, cache_dir: str, max_size_mb: int = 512, enabled: bool = True):
        self.cache_dir = Path(cache_dir)
        self.max_size_mb = max_size_mb
        self.enabled = enabled
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            _LOGGER.info(
                f"Audio cache initialized at: {self.cache_dir} (limit: {max_size_mb} MB)"
            )

    def get_hash(self, text: str, voice: Optional[str] = None) -> str:
        key = f"{text}|{voice or ''}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def get(self, text: str, voice: Optional[str] = None) -> Optional[List[Event]]:
        if not self.enabled:
            return None

        cache_key = self.get_hash(text, voice)
        cache_file = self.cache_dir / f"{cache_key}.events"

        if not cache_file.exists():
            return None

        try:
            events = []
            with open(cache_file, "rb") as f:
                while True:
                    event = read_event(f)
                    if event is None:
                        break
                    events.append(event)
            _LOGGER.debug(f"Cache hit for text hash: {cache_key}")
            return events
        except Exception as e:
            _LOGGER.warning(f"Failed to read cache file {cache_file}: {e}")
            return None

    def set(self, text: str, voice: Optional[str], events: List[Event]) -> None:
        if not self.enabled:
            return

        cache_key = self.get_hash(text, voice)
        cache_file = self.cache_dir / f"{cache_key}.events"

        try:
            with open(cache_file, "wb") as f:
                for event in events:
                    write_event(event, f)
            _LOGGER.debug(f"Cached {len(events)} events for text hash: {cache_key}")
            self._prune_cache()
        except Exception as e:
            _LOGGER.warning(f"Failed to write cache file {cache_file}: {e}")

    def _get_cache_size(self) -> int:
        """Return total size of cache in bytes."""
        return sum(
            f.stat().st_size for f in self.cache_dir.glob("*.events") if f.is_file()
        )

    def _prune_cache(self) -> None:
        """Remove oldest cache files if total size exceeds limit."""
        max_bytes = self.max_size_mb * 1024 * 1024
        current_size = self._get_cache_size()

        if current_size <= max_bytes:
            return

        _LOGGER.debug(
            f"Cache size ({current_size} bytes) exceeds limit ({max_bytes} bytes). Pruning..."
        )

        # Sort files by access time (oldest first)
        files = sorted(
            list(self.cache_dir.glob("*.events")),
            key=lambda f: f.stat().st_atime,
        )

        for cache_file in files:
            file_size = cache_file.stat().st_size
            try:
                cache_file.unlink()
                current_size -= file_size
                _LOGGER.debug(f"Deleted old cache file: {cache_file}")
            except Exception as e:
                _LOGGER.warning(f"Failed to delete {cache_file}: {e}")

            if current_size <= max_bytes:
                break
