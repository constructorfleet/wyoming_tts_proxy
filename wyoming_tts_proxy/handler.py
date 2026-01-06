import logging
import asyncio
import time

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.error import Error
from wyoming.info import Describe, Info, TtsProgram, Attribution
from wyoming.tts import Synthesize
from wyoming.server import AsyncEventHandler
from wyoming.client import AsyncClient

from .metrics import (
    REQUESTS_TOTAL,
    CACHE_HITS_TOTAL,
    UPSTREAM_FAILURES_TOTAL,
    TTS_LATENCY,
)


_LOGGER = logging.getLogger(__name__)


class TTSProxyEventHandler(AsyncEventHandler):
    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, **kwargs
    ) -> None:
        self.proxy_program_info = kwargs.pop("proxy_program_info")
        self.cli_args = kwargs.pop("cli_args")
        self.upstream_uris = kwargs.pop("upstream_uris")
        self.text_normalizer = kwargs.pop("text_normalizer")
        self.cache = kwargs.pop("cache")
        self.config = kwargs.pop("config")

        super().__init__(reader, writer, **kwargs)

        try:
            self.client_address = writer.get_extra_info("peername")
        except Exception:
            self.client_address = "unknown"

        _LOGGER.info(
            f"TTSProxyEventHandler initialized for client {self.client_address}. "
            f"Upstreams: {self.upstream_uris}"
        )

    async def handle_event(self, event: Event) -> bool:
        _LOGGER.debug(f"Received event from client {self.client_address}: {event.type}")
        if Describe.is_type(event.type):
            return await self._handle_describe(event)

        if Synthesize.is_type(event.type):
            return await self._handle_synthesize(event)

        _LOGGER.warning(
            f"Received unhandled event type: {event.type}. Keeping connection open."
        )
        return True

    async def _handle_describe(self, event: Event) -> bool:
        _LOGGER.debug(f"Handling Describe event from client {self.client_address}.")
        for uri in self.upstream_uris:
            try:
                async with AsyncClient.from_uri(uri) as upstream_client:
                    _LOGGER.debug(f"Sending Describe to upstream TTS: {uri}")
                    await upstream_client.write_event(Describe().event())

                    upstream_response = await upstream_client.read_event()
                    if upstream_response and Info.is_type(upstream_response.type):
                        upstream_info = Info.from_event(upstream_response)
                        _LOGGER.debug(
                            f"Received Info from upstream TTS ({uri}): {upstream_info.event().payload}"
                        )

                        modified_tts_programs = []
                        if upstream_info.tts:
                            for prog in upstream_info.tts:
                                new_prog = TtsProgram(
                                    name=f"{prog.name} (via {self.proxy_program_info['name']})",
                                    description=prog.description,
                                    attribution=prog.attribution,
                                    installed=prog.installed,
                                    version=prog.version,
                                    voices=prog.voices or [],
                                )
                                modified_tts_programs.append(new_prog)

                        final_info = Info(
                            asr=upstream_info.asr,
                            tts=modified_tts_programs,
                            handle=upstream_info.handle,
                            intent=upstream_info.intent,
                            wake=upstream_info.wake,
                            mic=upstream_info.mic,
                            snd=upstream_info.snd,
                            satellite=upstream_info.satellite,
                        )
                        await self.write_event(final_info.event())
                        _LOGGER.debug(
                            f"Sent modified Info to client: {final_info.event().payload}"
                        )
                        return True
            except Exception as e:
                _LOGGER.warning(f"Failed to get Describe from upstream {uri}: {e}")
                UPSTREAM_FAILURES_TOTAL.labels(uri=uri).inc()

        # Fallback if all upstreams fail
        _LOGGER.warning("All upstreams failed for Describe. Sending basic proxy info.")
        basic_proxy_info_event = Info(
            tts=[
                TtsProgram(
                    name=self.proxy_program_info["name"],
                    description=self.proxy_program_info["description"],
                    attribution=Attribution(
                        name=self.proxy_program_info["attribution_name"],
                        url=self.proxy_program_info["attribution_url"],
                    ),
                    installed=True,
                    version=self.proxy_program_info["version"],
                    voices=[],
                )
            ]
        ).event()
        await self.write_event(basic_proxy_info_event)
        return True

    async def _handle_synthesize(self, event: Event) -> bool:
        REQUESTS_TOTAL.inc()
        synthesize_event = Synthesize.from_event(event)
        original_text = synthesize_event.text

        normalized_text = self.text_normalizer.normalize(original_text)
        _LOGGER.info(
            f"Text for TTS (original): '{original_text[:50]}...' -> (normalized): '{normalized_text[:50]}...' Voice: {synthesize_event.voice}"
        )

        if not normalized_text:
            await self._send_empty_audio()
            return True

        # Check Cache
        cached_events = self.cache.get(normalized_text, synthesize_event.voice)
        if cached_events:
            CACHE_HITS_TOTAL.inc()
            for ev in cached_events:
                await self.write_event(ev)
            return True

        # Wrap in SSML if configured
        final_text = normalized_text
        if self.config.ssml_template:
            final_text = self.config.ssml_template.replace("{{text}}", normalized_text)
            _LOGGER.debug(f"SSML wrapped text: {final_text}")

        # Try upstreams with failover
        start_time = time.perf_counter()
        first_chunk_sent = False

        for uri in self.upstream_uris:
            try:
                events_to_cache = []
                async with AsyncClient.from_uri(uri) as upstream_client:
                    proxied_synthesize = Synthesize(
                        text=final_text, voice=synthesize_event.voice
                    ).event()
                    await upstream_client.write_event(proxied_synthesize)

                    while True:
                        upstream_event = await upstream_client.read_event()
                        if upstream_event is None:
                            break

                        events_to_cache.append(upstream_event)
                        await self.write_event(upstream_event)

                        if not first_chunk_sent and AudioChunk.is_type(
                            upstream_event.type
                        ):
                            TTS_LATENCY.observe(time.perf_counter() - start_time)
                            first_chunk_sent = True

                        if AudioStop.is_type(upstream_event.type) or Error.is_type(
                            upstream_event.type
                        ):
                            break

                    self.cache.set(
                        normalized_text, synthesize_event.voice, events_to_cache
                    )
                    return True
            except Exception as e:
                _LOGGER.warning(f"Upstream {uri} failed for Synthesize: {e}")
                UPSTREAM_FAILURES_TOTAL.labels(uri=uri).inc()

        _LOGGER.error("All upstreams failed for Synthesize.")
        await self.write_event(Error(text="All upstream TTS services failed.").event())
        return True

    async def _send_empty_audio(self):
        _LOGGER.warning("Text became empty after normalization.")
        await self.write_event(AudioStart(rate=16000, width=2, channels=1).event())
        await self.write_event(AudioStop().event())


# --- END OF FILE handler.py ---
