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
        cli_args=MagicMock(stream_tts=False),
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
        cli_args=MagicMock(stream_tts=False),
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

    cli_args = MagicMock()
    cli_args.stream_tts = False

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=cli_args,
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
        cli_args=MagicMock(stream_tts=False),
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


@pytest.mark.asyncio
async def test_handler_streaming_synthesize(
    proxy_program_info, text_normalizer, audio_cache, proxy_config
):
    """Test handling streaming synthesize request (SynthesizeStart/Chunk/Stop)."""
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.return_value = upstream_client
    upstream_client.read_event.side_effect = [
        AudioStart(rate=16000, width=2, channels=1).event(),
        AudioStop().event(),
    ]

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(stream_tts=False),
        upstream_uris=["tcp://upstream"],
        text_normalizer=text_normalizer,
        cache=audio_cache,
        config=proxy_config,
    )

    from wyoming.tts import SynthesizeStart, SynthesizeChunk, SynthesizeStop

    with patch(
        "wyoming_tts_proxy.handler.AsyncClient.from_uri", return_value=upstream_client
    ):
        # Start streaming
        await handler.handle_event(SynthesizeStart().event())
        assert handler.is_streaming is True

        # Send chunks
        await handler.handle_event(SynthesizeChunk(text="hello ").event())
        await handler.handle_event(SynthesizeChunk(text="world").event())

        # Stop streaming - this triggers the actual synthesis
        result = await handler.handle_event(SynthesizeStop().event())

    assert result is True
    assert handler.is_streaming is False
    # Should have sent streaming events to upstream
    assert upstream_client.write_event.call_count >= 3  # Start + Chunk + Stop


@pytest.mark.asyncio
async def test_handler_force_streaming_with_flag(
    proxy_program_info, text_normalizer, audio_cache, proxy_config
):
    """Test forcing streaming mode with --stream-tts flag."""
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.return_value = upstream_client
    upstream_client.read_event.side_effect = [
        AudioStart(rate=16000, width=2, channels=1).event(),
        AudioStop().event(),
    ]

    # Enable stream_tts flag
    cli_args = MagicMock()
    cli_args.stream_tts = True

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=cli_args,
        upstream_uris=["tcp://upstream"],
        text_normalizer=text_normalizer,
        cache=audio_cache,
        config=proxy_config,
    )

    from wyoming.tts import Synthesize

    event = Synthesize(text="hello").event()
    with patch(
        "wyoming_tts_proxy.handler.AsyncClient.from_uri", return_value=upstream_client
    ):
        result = await handler.handle_event(event)

    assert result is True
    # Should have sent streaming events to upstream (Start, Chunk, Stop)
    assert upstream_client.write_event.call_count == 3


@pytest.mark.asyncio
async def test_handler_preserve_streaming_flag(
    proxy_program_info, text_normalizer, audio_cache, proxy_config
):
    """Test that supports_synthesize_streaming flag is preserved from upstream."""
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.return_value = upstream_client

    # Mock Info response with streaming support
    upstream_info = Info(
        tts=[
            TtsProgram(
                name="upstream-tts",
                description="desc",
                attribution=Attribution(name="attr", url="url"),
                installed=True,
                version="1.0",
                voices=[],
                supports_synthesize_streaming=True,
            )
        ]
    )
    upstream_client.read_event.return_value = upstream_info.event()

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(stream_tts=False),
        upstream_uris=["tcp://upstream"],
        text_normalizer=text_normalizer,
        cache=audio_cache,
        config=proxy_config,
    )

    with patch(
        "wyoming_tts_proxy.handler.AsyncClient.from_uri", return_value=upstream_client
    ):
        event = Describe().event()
        result = await handler.handle_event(event)

    assert result is True
    # Check that the Info sent to client preserves the streaming flag
    # The write call should have the streaming flag set to True
    assert writer.write.called

