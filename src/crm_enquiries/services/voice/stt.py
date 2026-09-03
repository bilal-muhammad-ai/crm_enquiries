"""Speech-to-text via Groq Whisper."""

from __future__ import annotations

import logging

import httpx

from crm_enquiries.config import get_settings

logger = logging.getLogger(__name__)

GROQ_TRANSCRIPTIONS_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


class GroqSTTService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        if not self.settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required for speech transcription")

        content_type = "audio/webm"
        if filename.endswith(".wav"):
            content_type = "audio/wav"
        elif filename.endswith(".mp3"):
            content_type = "audio/mpeg"
        elif filename.endswith(".ogg"):
            content_type = "audio/ogg"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                GROQ_TRANSCRIPTIONS_URL,
                headers={"Authorization": f"Bearer {self.settings.groq_api_key}"},
                data={"model": self.settings.voice_stt_model, "response_format": "json"},
                files={"file": (filename, audio_bytes, content_type)},
            )
            response.raise_for_status()
            payload = response.json()

        text = (payload.get("text") or "").strip()
        logger.debug("STT transcript length: %d", len(text))
        return text
