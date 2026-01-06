import logging
from prometheus_client import Counter, Histogram, start_http_server

_LOGGER = logging.getLogger(__name__)

# Metrics
REQUESTS_TOTAL = Counter(
    "tts_proxy_requests_total", "Total number of TTS requests received"
)
CACHE_HITS_TOTAL = Counter(
    "tts_proxy_cache_hits_total", "Total number of audio cache hits"
)
UPSTREAM_FAILURES_TOTAL = Counter(
    "tts_proxy_upstream_failures_total", "Total number of failures to upstream TTS services", ["uri"]
)
TTS_LATENCY = Histogram(
    "tts_proxy_latency_seconds", "Latency of TTS generation (from request to first audio chunk)"
)


def start_metrics_server(port: int) -> None:
    if port > 0:
        try:
            start_http_server(port)
            _LOGGER.info(f"Prometheus metrics server started on port {port}")
        except Exception as e:
            _LOGGER.error(f"Failed to start Prometheus metrics server on port {port}: {e}")
