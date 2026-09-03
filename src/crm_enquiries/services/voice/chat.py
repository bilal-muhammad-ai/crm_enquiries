"""KB-grounded voice FAQ chat with in-memory sessions."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field

import httpx

from crm_enquiries.config import get_settings
from crm_enquiries.services.knowledge_base import KnowledgeBaseService

logger = logging.getLogger(__name__)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are the Glancy Fawcett voice assistant on the company website.
Answer visitor questions using ONLY the FAQ context provided below.
Keep replies short and natural for speech: 2 to 4 sentences maximum.
Do not invent facts, prices, timelines, or policies not supported by the FAQ context.
If the FAQ context does not contain the answer, say: "I don't have that information in our FAQ. Please contact our team directly."
Do not mention internal systems, knowledge bases, or AI."""


@dataclass
class VoiceSession:
    session_id: str
    messages: list[dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


class VoiceChatService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.kb = KnowledgeBaseService()
        self._sessions: dict[str, VoiceSession] = {}

    def create_session(self) -> str:
        self._purge_expired()
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = VoiceSession(session_id=session_id)
        return session_id

    def get_session(self, session_id: str) -> VoiceSession | None:
        self._purge_expired()
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.last_active = time.time()
        return session

    def _purge_expired(self) -> None:
        cutoff = time.time() - self.settings.voice_session_ttl_seconds
        expired = [sid for sid, s in self._sessions.items() if s.last_active < cutoff]
        for sid in expired:
            del self._sessions[sid]

    async def handle_turn(self, session_id: str, user_text: str) -> str:
        session = self.get_session(session_id)
        if session is None:
            raise ValueError(f"Unknown or expired session: {session_id}")

        user_text = user_text.strip()
        if not user_text:
            return "I didn't catch that. Could you please repeat your question?"

        kb_results = self.kb.query(user_text, top_k=3)
        faq_context = self._format_kb_context(kb_results)

        if self.settings.groq_api_key:
            reply = await self._llm_reply(session, user_text, faq_context)
        else:
            reply = self._kb_fallback_reply(kb_results)

        reply = reply[: self.settings.voice_max_reply_chars].strip()
        session.messages.append({"role": "user", "content": user_text})
        session.messages.append({"role": "assistant", "content": reply})
        return reply

    def _format_kb_context(self, kb_results: list[dict]) -> str:
        if not kb_results:
            return "No FAQ excerpts matched this question."
        parts = []
        for i, result in enumerate(kb_results, 1):
            source = result.get("metadata", {}).get("source", "unknown")
            content = result.get("content", "")[:1200]
            parts.append(f"### Excerpt {i} ({source})\n{content}")
        return "\n\n".join(parts)

    def _kb_fallback_reply(self, kb_results: list[dict]) -> str:
        if not kb_results:
            return (
                "I don't have that information in our FAQ. "
                "Please contact our team directly."
            )
        excerpt = kb_results[0].get("content", "").strip()
        if len(excerpt) > 400:
            excerpt = excerpt[:397].rsplit(" ", 1)[0] + "..."
        return excerpt

    def _groq_model_name(self) -> str:
        model = self.settings.llm_model
        if model.startswith("groq/"):
            return model[len("groq/") :]
        return model

    async def _llm_reply(self, session: VoiceSession, user_text: str, faq_context: str) -> str:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n## FAQ Context\n{faq_context}"},
        ]
        for msg in session.messages[-6:]:
            messages.append(msg)
        messages.append({"role": "user", "content": user_text})

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {self.settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._groq_model_name(),
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 256,
                },
            )
            response.raise_for_status()
            payload = response.json()

        choices = payload.get("choices") or []
        if not choices:
            logger.warning("Groq chat returned no choices")
            return self._kb_fallback_reply(self.kb.query(user_text, top_k=1))

        content = choices[0].get("message", {}).get("content", "").strip()
        return content or self._kb_fallback_reply(self.kb.query(user_text, top_k=1))
