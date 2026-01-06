import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from wyoming.event import Event
from wyoming.info import Describe, Info, TtsProgram
from wyoming.tts import Synthesize

from wyoming_tts_proxy.handler import TTSProxyEventHandler
from wyoming_tts_proxy.normalizer import TextNormalizer
from wyoming_tts_proxy.config import ProxyConfig


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


@pytest.mark.asyncio
async def test_handler_describe(proxy_program_info, text_normalizer):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    # Mock __aenter__ and __aexit__ for the context manager
    upstream_client.__aenter__.return_value = upstream_client

    upstream_tts_client_factory = MagicMock(return_value=upstream_client)

    # Mock Info response from upstream
    upstream_info = Info(
        tts=[
            TtsProgram(
                name="upstream-tts",
                description="desc",
                attribution={"name": "attr", "url": "url"},
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
        upstream_tts_uri_for_logging="tcp://upstream",
        upstream_tts_client_factory=upstream_tts_client_factory,
        text_normalizer=text_normalizer,
    )

    # Simulate Describe event
    event = Describe().event()
    result = await handler.handle_event(event)

    assert result is True
    assert upstream_client.write_event.called
    assert writer.write.called  # write_event calls writer.write


@pytest.mark.asyncio
async def test_handler_describe_error(proxy_program_info, text_normalizer):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.side_effect = ConnectionRefusedError()

    upstream_tts_client_factory = MagicMock(return_value=upstream_client)

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_tts_uri_for_logging="tcp://upstream",
        upstream_tts_client_factory=upstream_tts_client_factory,
        text_normalizer=text_normalizer,
    )

    event = Describe().event()
    result = await handler.handle_event(event)

    assert result is True
    # Should have sent Error event
    # We can check writer.write calls to see what was sent


@pytest.mark.asyncio
async def test_handler_describe_info_fallback(proxy_program_info, text_normalizer):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.return_value = upstream_client
    # Return non-Info event
    upstream_client.read_event.return_value = Event(type="not-info", data={})

    upstream_tts_client_factory = MagicMock(return_value=upstream_client)

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_tts_uri_for_logging="tcp://upstream",
        upstream_tts_client_factory=upstream_tts_client_factory,
        text_normalizer=text_normalizer,
    )

    event = Describe().event()
    result = await handler.handle_event(event)

    assert result is True
    assert writer.write.called


@pytest.mark.asyncio
async def test_handler_describe_timeout(proxy_program_info, text_normalizer):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.side_effect = asyncio.TimeoutError()

    upstream_tts_client_factory = MagicMock(return_value=upstream_client)

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_tts_uri_for_logging="tcp://upstream",
        upstream_tts_client_factory=upstream_tts_client_factory,
        text_normalizer=text_normalizer,
    )

    event = Describe().event()
    result = await handler.handle_event(event)

    assert result is True


@pytest.mark.asyncio
async def test_handler_synthesize_timeout(proxy_program_info, text_normalizer):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.side_effect = asyncio.TimeoutError()

    upstream_tts_client_factory = MagicMock(return_value=upstream_client)

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_tts_uri_for_logging="tcp://upstream",
        upstream_tts_client_factory=upstream_tts_client_factory,
        text_normalizer=text_normalizer,
    )

    event = Synthesize(text="hello").event()
    result = await handler.handle_event(event)

    assert result is True


@pytest.mark.asyncio
async def test_handler_synthesize_connection_refused(
    proxy_program_info, text_normalizer
):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.side_effect = ConnectionRefusedError()

    upstream_tts_client_factory = MagicMock(return_value=upstream_client)

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_tts_uri_for_logging="tcp://upstream",
        upstream_tts_client_factory=upstream_tts_client_factory,
        text_normalizer=text_normalizer,
    )

    event = Synthesize(text="hello").event()
    result = await handler.handle_event(event)

    assert result is True
    # writer.write.call_args_list contains the events
    pass


@pytest.mark.asyncio
async def test_handler_describe_fallback(proxy_program_info, text_normalizer):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.return_value = upstream_client
    # Return something that is not Info
    upstream_client.read_event.return_value = Event(type="not-info", data={})

    upstream_tts_client_factory = MagicMock(return_value=upstream_client)

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_tts_uri_for_logging="tcp://upstream",
        upstream_tts_client_factory=upstream_tts_client_factory,
        text_normalizer=text_normalizer,
    )

    event = Describe().event()
    result = await handler.handle_event(event)

    assert result is True
    assert writer.write.called


@pytest.mark.asyncio
async def test_handler_synthesize(proxy_program_info, text_normalizer):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.return_value = upstream_client

    upstream_tts_client_factory = MagicMock(return_value=upstream_client)

    # Mock Synthesize event
    event = Synthesize(text="Hello *world*!").event()

    # Mock upstream response (AudioStart, AudioStop)
    from wyoming.audio import AudioStart, AudioStop

    upstream_client.read_event.side_effect = [
        AudioStart(rate=16000, width=2, channels=1).event(),
        AudioStop().event(),
    ]

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_tts_uri_for_logging="tcp://upstream",
        upstream_tts_client_factory=upstream_tts_client_factory,
        text_normalizer=text_normalizer,
    )

    result = await handler.handle_event(event)

    assert result is True
    # Verify normalized text was sent
    sent_event = upstream_client.write_event.call_args[0][0]
    assert Synthesize.is_type(sent_event.type)
    assert sent_event.data["text"] == "Hello world!"


@pytest.mark.asyncio
async def test_handler_synthesize_empty(proxy_program_info, text_normalizer):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_tts_client_factory = MagicMock()

    # Mock Synthesize event that becomes empty
    event = Synthesize(text="*").event()  # normalizer removes *

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_tts_uri_for_logging="tcp://upstream",
        upstream_tts_client_factory=upstream_tts_client_factory,
        text_normalizer=text_normalizer,
    )

    result = await handler.handle_event(event)

    assert result is True
    assert not upstream_tts_client_factory.called
    assert writer.write.called  # Should have sent AudioStart and AudioStop


@pytest.mark.asyncio
async def test_handler_unhandled_event(proxy_program_info, text_normalizer):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_tts_uri_for_logging="tcp://upstream",
        upstream_tts_client_factory=MagicMock(),
        text_normalizer=text_normalizer,
    )

    event = Event(type="unknown", data={})
    result = await handler.handle_event(event)

    assert result is True


@pytest.mark.asyncio
async def test_handler_describe_generic_error(proxy_program_info, text_normalizer):
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = AsyncMock(spec=asyncio.StreamWriter)

    upstream_client = AsyncMock()
    upstream_client.__aenter__.side_effect = Exception("Generic error")

    upstream_tts_client_factory = MagicMock(return_value=upstream_client)

    handler = TTSProxyEventHandler(
        reader,
        writer,
        proxy_program_info=proxy_program_info,
        cli_args=MagicMock(),
        upstream_tts_uri_for_logging="tcp://upstream",
        upstream_tts_client_factory=upstream_tts_client_factory,
        text_normalizer=text_normalizer,
    )

    event = Describe().event()
    result = await handler.handle_event(event)

    assert result is True
