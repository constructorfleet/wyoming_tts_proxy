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
