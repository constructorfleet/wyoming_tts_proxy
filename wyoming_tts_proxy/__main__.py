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


def create_upstream_tts_client(uri: str) -> AsyncClient:
    return AsyncClient.from_uri(uri)


async def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOGLEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(module)s: %(message)s",
    )

    parser = ArgumentParser(description=PROXY_PROGRAM_DESCRIPTION)
    parser.add_argument(
        "--uri",
        default=os.getenv("LISTEN_URI", "tcp://0.0.0.0:10201"),
        help="unix:// or tcp:// URI where this proxy server will listen (env: LISTEN_URI)",
    )
    parser.add_argument(
        "--upstream-tts-uri",
        default=os.getenv("UPSTREAM_TTS_URI"),
        help="unix:// or tcp:// URI of the upstream Wyoming TTS service (env: UPSTREAM_TTS_URI)",
    )
    parser.add_argument(
        "--config",
        default=os.getenv("CONFIG_FILE_PATH"),
        help="Path to YAML configuration file for text normalization (env: CONFIG_FILE_PATH)",
    )
    args = parser.parse_args()

    if not args.upstream_tts_uri:
        print(
            "An upstream TTS URI is required (--upstream-tts-uri or UPSTREAM_TTS_URI env)"
        )
        sys.exit(1)

    _LOGGER.info(f"Starting {PROXY_PROGRAM_NAME} v{PROXY_PROGRAM_VERSION}")
    _LOGGER.info(f"Proxy will listen on: {args.uri}")
    _LOGGER.info(f"Upstream TTS service: {args.upstream_tts_uri}")

    config = load_config(args.config)
    text_normalizer = TextNormalizer(config=config)

    proxy_program_basic_info = {
        "name": PROXY_PROGRAM_NAME,
        "description": PROXY_PROGRAM_DESCRIPTION,
        "version": PROXY_PROGRAM_VERSION,
        "attribution_name": PROXY_ATTRIBUTION_NAME,
        "attribution_url": PROXY_ATTRIBUTION_URL,
    }

    upstream_tts_client_factory = partial(
        create_upstream_tts_client, args.upstream_tts_uri
    )

    handler_factory = partial(
        TTSProxyEventHandler,
        proxy_program_info=proxy_program_basic_info,
        cli_args=args,
        upstream_tts_uri_for_logging=args.upstream_tts_uri,
        upstream_tts_client_factory=upstream_tts_client_factory,
        text_normalizer=text_normalizer,
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
