"""Voice FAQ widget API — WebSocket chat and demo page."""

from __future__ import annotations

import base64
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from crm_enquiries.config import get_settings
from crm_enquiries.services.voice.chat import VoiceChatService
from crm_enquiries.services.voice.stt import GroqSTTService
from crm_enquiries.services.voice.tts import EdgeTTSService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice"])

STATIC_DIR = Path(__file__).resolve().parents[1] / "static" / "voice-widget"

_chat_service = VoiceChatService()
_stt_service = GroqSTTService()
_tts_service = EdgeTTSService()

_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_key: str) -> bool:
    settings = get_settings()
    now = time.time()
    window_start = now - 60
    bucket = [t for t in _rate_buckets[client_key] if t > window_start]
    if len(bucket) >= settings.voice_rate_limit_per_minute:
        _rate_buckets[client_key] = bucket
        return False
    bucket.append(now)
    _rate_buckets[client_key] = bucket
    return True


@router.get("/voice")
async def voice_demo_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@router.websocket("/api/v1/voice/chat")
async def voice_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    client_host = websocket.client.host if websocket.client else "unknown"
    session_id = _chat_service.create_session()

    await websocket.send_json(
        {
            "type": "session",
            "session_id": session_id,
            "message": "Connected. Hold the microphone button to ask a question.",
        }
    )

    try:
        while True:
            raw = await websocket.receive_text()
            if not _check_rate_limit(client_host):
                await websocket.send_json(
                    {"type": "error", "message": "Rate limit exceeded. Please wait a moment."}
                )
                continue

            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON message."})
                continue

            msg_type = payload.get("type")
            data = payload.get("data", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            user_text = ""
            if msg_type == "text":
                user_text = str(data).strip()
            elif msg_type == "audio":
                audio_b64 = str(data)
                if audio_b64.startswith("data:"):
                    audio_b64 = audio_b64.split(",", 1)[-1]
                audio_bytes = base64.b64decode(audio_b64)
                filename = payload.get("filename", "audio.webm")
                try:
                    user_text = await _stt_service.transcribe(audio_bytes, filename=filename)
                except Exception as exc:
                    logger.warning("STT failed: %s", exc)
                    await websocket.send_json(
                        {"type": "error", "message": "Could not transcribe audio. Try again or type your question."}
                    )
                    continue
            else:
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})
                continue

            if not user_text:
                await websocket.send_json(
                    {"type": "error", "message": "No speech detected. Please try again."}
                )
                continue

            await websocket.send_json({"type": "transcript", "data": user_text})

            try:
                reply_text = await _chat_service.handle_turn(session_id, user_text)
            except ValueError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
                continue

            audio_bytes = await _tts_service.synthesize(reply_text)
            audio_b64 = base64.b64encode(audio_bytes).decode("ascii") if audio_bytes else ""

            await websocket.send_json(
                {
                    "type": "reply",
                    "text": reply_text,
                    "audio": audio_b64,
                }
            )
    except WebSocketDisconnect:
        logger.debug("Voice WebSocket disconnected: session=%s", session_id)
    except Exception as exc:
        logger.exception("Voice WebSocket error: %s", exc)
        try:
            await websocket.send_json({"type": "error", "message": "An unexpected error occurred."})
        except Exception:
            pass
