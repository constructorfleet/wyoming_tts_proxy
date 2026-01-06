import pytest
from wyoming.audio import AudioStart, AudioStop
from wyoming_tts_proxy.cache import AudioCache


def test_cache_set_get(tmp_path):
    cache_dir = tmp_path / "cache"
    cache = AudioCache(str(cache_dir), enabled=True)

    text = "Hello world"
    voice = "en_US-hq"
    events = [
        AudioStart(rate=16000, width=2, channels=1).event(),
        AudioStop().event(),
    ]

    cache.set(text, voice, events)
    retrieved = cache.get(text, voice)

    assert retrieved is not None
    assert len(retrieved) == 2
    assert retrieved[0].type == "audio-start"
    assert retrieved[1].type == "audio-stop"


def test_cache_disabled(tmp_path):
    cache_dir = tmp_path / "cache"
    cache = AudioCache(str(cache_dir), enabled=False)

    text = "Hello world"
    events = [AudioStop().event()]

    cache.set(text, None, events)
    assert cache.get(text, None) is None
    assert not (cache_dir / f"{cache.get_hash(text, None)}.events").exists()


def test_cache_miss(tmp_path):
    cache_dir = tmp_path / "cache"
    cache = AudioCache(str(cache_dir), enabled=True)
    assert cache.get("nonexistent", None) is None
