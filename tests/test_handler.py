import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from wyoming.info import Describe, Info, TtsProgram, Attribution
from wyoming.tts import Synthesize
from wyoming.audio import AudioStart, AudioStop

from wyoming_tts_proxy.handler import TTSProxyEventHandler
from wyoming_tts_proxy.normalizer import TextNormalizer
from wyoming_tts_proxy.config import ProxyConfig
from wyoming_tts_proxy.cache import AudioCache


@pytest.fixture
def proxy_program_info():
    return {
        "name": "test-proxy",
        "description": "test description",
        "version": "0.1.0",
        "attribution_name": "test attribution",
        "attribution_url": "http://test.com",
    }


@pytest.fixture
def text_normalizer():
    return TextNormalizer(ProxyConfig())


@pytest.fixture
def audio_cache(tmp_path):
    return AudioCache(str(tmp_path / "cache"), enabled=False)


@pytest.fixture
def proxy_config():
    return ProxyConfig()


@pytest.mark.asyncio
async def test_handler_describe(
    proxy_program_info, text_normalizer, audio_cache, proxy_config
):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.return_value = upstream_client

    # Mock Info response from upstream
    upstream_info = Info(
        tts=[
            TtsProgram(
                name="upstream-tts",
                description="desc",
                attribution=Attribution(name="attr", url="url"),
                installed=True,
                version="1.0",
                voices=[],
            )
        ]
    )
    upstream_client.read_event.return_value = upstream_info.event()

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_uris=["tcp://upstream"],
        text_normalizer=text_normalizer,
        cache=audio_cache,
        config=proxy_config,
    )

    with patch(
        "wyoming_tts_proxy.handler.AsyncClient.from_uri", return_value=upstream_client
    ):
        # Simulate Describe event
        event = Describe().event()
        result = await handler.handle_event(event)

    assert result is True
    assert upstream_client.write_event.called
    assert writer.write.called


@pytest.mark.asyncio
async def test_handler_describe_failover(
    proxy_program_info, text_normalizer, audio_cache, proxy_config
):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    client1 = AsyncMock()
    client1.__aenter__.side_effect = Exception("Failed")

    client2 = AsyncMock()
    client2.__aenter__.return_value = client2
    client2.read_event.return_value = Info(tts=[]).event()

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_uris=["tcp://upstream1", "tcp://upstream2"],
        text_normalizer=text_normalizer,
        cache=audio_cache,
        config=proxy_config,
    )

    with patch(
        "wyoming_tts_proxy.handler.AsyncClient.from_uri", side_effect=[client1, client2]
    ):
        event = Describe().event()
        result = await handler.handle_event(event)

    assert result is True
    assert client2.write_event.called


@pytest.mark.asyncio
async def test_handler_synthesize_ssml(
    proxy_program_info, text_normalizer, audio_cache
):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.return_value = upstream_client
    upstream_client.read_event.side_effect = [
        AudioStart(rate=16000, width=2, channels=1).event(),
        AudioStop().event(),
    ]

    config = ProxyConfig(ssml_template="<speak>{{text}}</speak>")

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_uris=["tcp://upstream"],
        text_normalizer=text_normalizer,
        cache=audio_cache,
        config=config,
    )

    event = Synthesize(text="hello").event()
    with patch(
        "wyoming_tts_proxy.handler.AsyncClient.from_uri", return_value=upstream_client
    ):
        result = await handler.handle_event(event)

    assert result is True
    sent_event = upstream_client.write_event.call_args[0][0]
    assert sent_event.data["text"] == "<speak>hello</speak>"


@pytest.mark.asyncio
async def test_handler_synthesize_cache_hit(
    proxy_program_info, text_normalizer, tmp_path, proxy_config
):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    cache = AudioCache(str(tmp_path / "cache"), enabled=True)
    events = [
        AudioStart(rate=16000, width=2, channels=1).event(),
        AudioStop().event(),
    ]
    cache.set("hello", None, events)

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_uris=["tcp://upstream"],
        text_normalizer=text_normalizer,
        cache=cache,
        config=proxy_config,
    )

    event = Synthesize(text="hello").event()
    result = await handler.handle_event(event)

    assert result is True
    # Verify events were written to client without calling upstream
    assert writer.write.call_count == 2
