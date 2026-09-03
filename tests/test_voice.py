"""Tests for voice FAQ widget services and WebSocket API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.testclient import TestClient

from crm_enquiries.main import app
from crm_enquiries.services.voice.chat import VoiceChatService
from crm_enquiries.services.voice.stt import GroqSTTService
from crm_enquiries.services.voice.tts import EdgeTTSService


@pytest.fixture
def kb_results():
    return [
        {
            "content": "Glancy Fawcett offers superyacht outfitting and residential projects.",
            "metadata": {"source": "01_company_overview.md"},
        }
    ]


@pytest.mark.asyncio
async def test_voice_chat_kb_fallback_without_groq(kb_results):
    service = VoiceChatService()
    session_id = service.create_session()

    with patch.object(service.settings, "groq_api_key", ""):
        with patch.object(service.kb, "query", return_value=kb_results):
            reply = await service.handle_turn(session_id, "What services do you offer?")

    assert "superyacht" in reply.lower() or "Glancy Fawcett" in reply


@pytest.mark.asyncio
async def test_voice_chat_llm_reply(kb_results):
    service = VoiceChatService()
    session_id = service.create_session()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "We specialise in luxury interior projects."}}]
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch.object(service.settings, "groq_api_key", "test-key"):
        with patch.object(service.kb, "query", return_value=kb_results):
            with patch("crm_enquiries.services.voice.chat.httpx.AsyncClient", return_value=mock_client):
                reply = await service.handle_turn(session_id, "Tell me about your work")

    assert "luxury interior" in reply.lower()


@pytest.mark.asyncio
async def test_voice_chat_empty_input():
    service = VoiceChatService()
    session_id = service.create_session()

    reply = await service.handle_turn(session_id, "   ")
    assert "didn't catch" in reply.lower()


@pytest.mark.asyncio
async def test_groq_stt_transcribe():
    stt = GroqSTTService()

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"text": "What are your payment terms?"}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch.object(stt.settings, "groq_api_key", "test-key"):
        with patch("crm_enquiries.services.voice.stt.httpx.AsyncClient", return_value=mock_client):
            text = await stt.transcribe(b"fake-audio", filename="audio.webm")

    assert text == "What are your payment terms?"


@pytest.mark.asyncio
async def test_edge_tts_synthesize():
    tts = EdgeTTSService()

    async def fake_stream():
        yield {"type": "audio", "data": b"mp3-bytes"}

    mock_communicate = MagicMock()
    mock_communicate.stream = fake_stream

    with patch("crm_enquiries.services.voice.tts.edge_tts.Communicate", return_value=mock_communicate):
        audio = await tts.synthesize("Hello from Glancy Fawcett.")

    assert audio == b"mp3-bytes"


def test_voice_websocket_text_flow():
    mock_chat = MagicMock()
    mock_chat.create_session.return_value = "test-session"
    mock_chat.handle_turn = AsyncMock(return_value="We offer luxury interior design.")

    mock_tts = MagicMock()
    mock_tts.synthesize = AsyncMock(return_value=b"audio-data")

    with patch("crm_enquiries.api.voice._chat_service", mock_chat):
        with patch("crm_enquiries.api.voice._tts_service", mock_tts):
            with TestClient(app) as client:
                with client.websocket_connect("/api/v1/voice/chat") as ws:
                    session_msg = ws.receive_json()
                    assert session_msg["type"] == "session"
                    assert session_msg["session_id"] == "test-session"

                    ws.send_json({"type": "text", "data": "What do you do?"})
                    transcript = ws.receive_json()
                    assert transcript["type"] == "transcript"
                    assert transcript["data"] == "What do you do?"

                    reply = ws.receive_json()
                    assert reply["type"] == "reply"
                    assert "luxury interior" in reply["text"].lower()
                    assert reply["audio"]


def test_voice_demo_page():
    with TestClient(app) as client:
        response = client.get("/voice")
        assert response.status_code == 200
        assert "Glancy Fawcett Voice FAQ" in response.text
