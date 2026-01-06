from prometheus_client import REGISTRY
from wyoming_tts_proxy.metrics import (
    REQUESTS_TOTAL,
)


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


def test_health_endpoint():
    import time
    import urllib.request
    from wyoming_tts_proxy.metrics import start_metrics_server

    port = 9999
    start_metrics_server(port)
    time.sleep(0.5)  # Wait for server to start

    response = urllib.request.urlopen(f"http://127.0.0.1:{port}/health")
    assert response.getcode() == 200
    assert response.read() == b"OK"
