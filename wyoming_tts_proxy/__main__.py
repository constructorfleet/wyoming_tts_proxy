# --- START OF FILE __main__.py ---
import os
import asyncio
import logging
import sys
import yaml
from pathlib import Path
from typing import Optional
from functools import partial
from argparse import ArgumentParser

from wyoming.server import AsyncServer
from wyoming.client import AsyncClient
# from wyoming.event import Event

from .handler import TTSProxyEventHandler
from .normalizer import TextNormalizer
from .config import ProxyConfig
from .cache import AudioCache
from .metrics import start_metrics_server


PROXY_PROGRAM_NAME = "tts-proxy"
PROXY_PROGRAM_DESCRIPTION = "Wyoming TTS proxy with text normalization"
PROXY_PROGRAM_VERSION = "0.1.0"
PROXY_ATTRIBUTION_NAME = "My TTS Proxy"
PROXY_ATTRIBUTION_URL = "https://github.com/mitrokun/wyoming_tts_proxy"

_LOGGER = logging.getLogger(__name__)


def load_config(config_path_str: Optional[str]) -> ProxyConfig:
    if not config_path_str:
        return ProxyConfig()

    config_path = Path(config_path_str)
    if not config_path.exists():
        _LOGGER.error(f"Config file not found: {config_path_str}")
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        if config_dict is None:
            return ProxyConfig()

        config = ProxyConfig.model_validate(config_dict)
        _LOGGER.info(f"Loaded and validated config from {config_path_str}")
        return config
    except Exception as e:
        _LOGGER.error(f"Failed to load or validate config from {config_path_str}: {e}")
        sys.exit(1)


async def main() -> None:
    parser = ArgumentParser(description=PROXY_PROGRAM_DESCRIPTION)
    parser.add_argument(
        "--uri",
        default=os.getenv("LISTEN_URI", "tcp://0.0.0.0:10201"),
        help="unix:// or tcp:// URI where this proxy server will listen (env: LISTEN_URI)",
    )
    parser.add_argument(
        "--upstream-tts-uri",
        action="append",
        help="unix:// or tcp:// URI of the Wyoming TTS service to proxy. Can be specified multiple times for failover. (env: UPSTREAM_TTS_URI)",
    )
    parser.add_argument(
        "--config",
        default=os.getenv("CONFIG_FILE_PATH"),
        help="Path to YAML configuration file for text normalization (env: CONFIG_FILE_PATH)",
    )
    parser.add_argument(
        "--cache-dir",
        default=os.getenv("CACHE_DIR", "/tmp/wyoming_tts_cache"),
        help="Directory to store cached audio (env: CACHE_DIR)",
    )
    parser.add_argument(
        "--metrics-port",
        type=int,
        default=int(os.getenv("METRICS_PORT", "0")),
        help="Port to expose Prometheus metrics (0 = disabled) (env: METRICS_PORT)",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (env: LOG_LEVEL, default: INFO)",
    )
    parser.add_argument(
        "--debug",
        action="store_const",
        const="DEBUG",
        dest="log_level",
        help="Set log level to DEBUG",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(module)s: %(message)s",
    )

    config = load_config(args.config)

    # Merge CLI args with config
    upstream_uris = args.upstream_tts_uri or []
    if not upstream_uris and os.getenv("UPSTREAM_TTS_URI"):
        upstream_uris = [os.getenv("UPSTREAM_TTS_URI")]

    if not upstream_uris:
        upstream_uris = config.upstream_uris

    if not upstream_uris:
        _LOGGER.error(
            "An upstream TTS URI is required (--upstream-tts-uri, UPSTREAM_TTS_URI env, or config file)"
        )
        sys.exit(1)

    # Metrics
    metrics_port = args.metrics_port or config.metrics_port
    start_metrics_server(metrics_port)

    # Cache
    cache_dir = args.cache_dir or config.cache_dir
    cache = AudioCache(cache_dir=cache_dir, enabled=config.cache_enabled)

    _LOGGER.info(f"Starting {PROXY_PROGRAM_NAME} v{PROXY_PROGRAM_VERSION}")
    _LOGGER.info(f"Proxy will listen on: {args.uri}")
    _LOGGER.info(f"Upstream TTS services: {upstream_uris}")

    text_normalizer = TextNormalizer(config=config)

    proxy_program_basic_info = {
        "name": PROXY_PROGRAM_NAME,
        "description": PROXY_PROGRAM_DESCRIPTION,
        "version": PROXY_PROGRAM_VERSION,
        "attribution_name": PROXY_ATTRIBUTION_NAME,
        "attribution_url": PROXY_ATTRIBUTION_URL,
    }

    handler_factory = partial(
        TTSProxyEventHandler,
        proxy_program_info=proxy_program_basic_info,
        cli_args=args,
        upstream_uris=upstream_uris,
        text_normalizer=text_normalizer,
        cache=cache,
        config=config,
    )

    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info(f"Proxy server ready and listening at {args.uri}")

    try:
        await server.run(handler_factory)
    except OSError as e:
        _LOGGER.error(f"Failed to start server at {args.uri}: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        _LOGGER.info("Server shutting down due to KeyboardInterrupt.")
    finally:
        _LOGGER.info("Proxy server has shut down.")


if __name__ == "__main__":
    asyncio.run(main())
# --- END OF FILE __main__.py ---
