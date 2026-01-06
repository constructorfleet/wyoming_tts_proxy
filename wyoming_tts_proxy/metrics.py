import logging
import threading
from http.server import HTTPServer
from prometheus_client import Counter, Histogram, MetricsHandler

_LOGGER = logging.getLogger(__name__)


class MetricsAndHealthHandler(MetricsHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            super().do_GET()


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

            def run_server():
                httpd = HTTPServer(("0.0.0.0", port), MetricsAndHealthHandler)
                httpd.serve_forever()

            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()
            _LOGGER.info(
                f"Prometheus metrics and health server started on port {port} (/metrics, /health)"
            )
        except Exception as e:
            _LOGGER.error(
                f"Failed to start Prometheus metrics and health server on port {port}: {e}"
            )
