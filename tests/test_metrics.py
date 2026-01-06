import pytest
from prometheus_client import REGISTRY
from wyoming_tts_proxy.metrics import REQUESTS_TOTAL, CACHE_HITS_TOTAL, UPSTREAM_FAILURES_TOTAL, TTS_LATENCY

def test_metrics_initialization():
    # Check if our metrics are in the registry
    metric_names = [m.name for m in REGISTRY.collect()]
    # Prometheus-client might strip or add _total depending on version and presence
    assert any("tts_proxy_requests" in name for name in metric_names)
    assert any("tts_proxy_cache_hits" in name for name in metric_names)
    assert any("tts_proxy_upstream_failures" in name for name in metric_names)
    assert any("tts_proxy_latency" in name for name in metric_names)

def test_metrics_increment():
    before = REQUESTS_TOTAL._value.get()
    REQUESTS_TOTAL.inc()
    after = REQUESTS_TOTAL._value.get()
    assert after == before + 1
