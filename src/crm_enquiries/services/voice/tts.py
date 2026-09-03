"""Text-to-speech via edge-tts (Microsoft neural voices)."""

from __future__ import annotations

import logging

import edge_tts

from crm_enquiries.config import get_settings

logger = logging.getLogger(__name__)


class EdgeTTSService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def synthesize(self, text: str) -> bytes:
        if not text.strip():
            return b""

        communicate = edge_tts.Communicate(text.strip(), self.settings.voice_tts_voice)
        audio_chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])

        audio_bytes = b"".join(audio_chunks)
        logger.debug("TTS audio bytes: %d", len(audio_bytes))
        return audio_bytes
