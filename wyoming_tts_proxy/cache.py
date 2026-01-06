import hashlib
import logging
from pathlib import Path
from typing import List, Optional

from wyoming.event import Event, read_event, write_event

_LOGGER = logging.getLogger(__name__)


class AudioCache:
    def __init__(self, cache_dir: str, enabled: bool = True):
        self.cache_dir = Path(cache_dir)
        self.enabled = enabled
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            _LOGGER.info(f"Audio cache initialized at: {self.cache_dir}")

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
        except Exception as e:
            _LOGGER.warning(f"Failed to write cache file {cache_file}: {e}")
