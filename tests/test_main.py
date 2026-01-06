import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from wyoming_tts_proxy.__main__ import main


@pytest.mark.asyncio
async def test_main_cli():
    # Test main with minimal args
    with (
        patch("sys.argv", ["prog", "--upstream-tts-uri", "tcp://127.0.0.1:10200"]),
        patch("wyoming_tts_proxy.__main__.AsyncServer") as mock_server_class,
    ):
        mock_server = MagicMock()
        mock_server_class.from_uri.return_value = mock_server
        mock_server.run = AsyncMock(
            side_effect=asyncio.CancelledError
        )  # Stop after one "run"

        try:
            await main()
        except asyncio.CancelledError:
            pass

        mock_server_class.from_uri.assert_called_with("tcp://0.0.0.0:10201")


@pytest.mark.asyncio
async def test_main_log_level_env():
    env = {
        "UPSTREAM_TTS_URI": "tcp://upstream:1234",
        "LOG_LEVEL": "DEBUG",
    }
    with (
        patch("os.environ", env),
        patch("sys.argv", ["prog"]),
        patch("wyoming_tts_proxy.__main__.AsyncServer") as mock_server_class,
        patch("logging.basicConfig") as mock_logging_config,
    ):
        mock_server = MagicMock()
        mock_server_class.from_uri.return_value = mock_server
        mock_server.run = AsyncMock(side_effect=asyncio.CancelledError)

        try:
            await main()
        except asyncio.CancelledError:
            pass

        # Check if basicConfig was called with DEBUG level
        args, kwargs = mock_logging_config.call_args
        assert kwargs["level"] == "DEBUG"


@pytest.mark.asyncio
async def test_main_log_level_cli():
    with (
        patch(
            "sys.argv",
            ["prog", "--upstream-tts-uri", "tcp://upstream", "--log-level", "ERROR"],
        ),
        patch("wyoming_tts_proxy.__main__.AsyncServer") as mock_server_class,
        patch("logging.basicConfig") as mock_logging_config,
    ):
        mock_server = MagicMock()
        mock_server_class.from_uri.return_value = mock_server
        mock_server.run = AsyncMock(side_effect=asyncio.CancelledError)

        try:
            await main()
        except asyncio.CancelledError:
            pass

        # Check if basicConfig was called with ERROR level
        args, kwargs = mock_logging_config.call_args
        assert kwargs["level"] == "ERROR"


@pytest.mark.asyncio
async def test_main_debug_flag():
    with (
        patch("sys.argv", ["prog", "--upstream-tts-uri", "tcp://upstream", "--debug"]),
        patch("wyoming_tts_proxy.__main__.AsyncServer") as mock_server_class,
        patch("logging.basicConfig") as mock_logging_config,
    ):
        mock_server = MagicMock()
        mock_server_class.from_uri.return_value = mock_server
        mock_server.run = AsyncMock(side_effect=asyncio.CancelledError)

        try:
            await main()
        except asyncio.CancelledError:
            pass

        # Check if basicConfig was called with DEBUG level
        args, kwargs = mock_logging_config.call_args
        assert kwargs["level"] == "DEBUG"


@pytest.mark.asyncio
async def test_main_cli_with_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("normalize_markdown: true")

    with (
        patch(
            "sys.argv",
            [
                "prog",
                "--upstream-tts-uri",
                "tcp://127.0.0.1:10200",
                "--config",
                str(config_file),
            ],
        ),
        patch("wyoming_tts_proxy.__main__.AsyncServer") as mock_server_class,
    ):
        mock_server = MagicMock()
        mock_server_class.from_uri.return_value = mock_server
        mock_server.run = AsyncMock(side_effect=asyncio.CancelledError)

        try:
            await main()
        except asyncio.CancelledError:
            pass

        mock_server_class.from_uri.assert_called()


@pytest.mark.asyncio
async def test_main_env_vars():
    # Test main with environment variables
    env = {
        "LISTEN_URI": "tcp://1.2.3.4:5678",
        "UPSTREAM_TTS_URI": "tcp://upstream:1234",
    }
    with (
        patch("os.environ", env),
        patch("sys.argv", ["prog"]),
        patch("wyoming_tts_proxy.__main__.AsyncServer") as mock_server_class,
    ):
        mock_server = MagicMock()
        mock_server_class.from_uri.return_value = mock_server
        mock_server.run = AsyncMock(side_effect=asyncio.CancelledError)

        try:
            await main()
        except asyncio.CancelledError:
            pass

        mock_server_class.from_uri.assert_called_with("tcp://1.2.3.4:5678")
