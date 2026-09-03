"""FastAPI application entry point."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure CrewAI storage is within project data directory
_data_dir = Path(__file__).resolve().parents[2] / "data" / "crewai"
_data_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_DATA_HOME", str(_data_dir))
os.environ.setdefault("CREWAI_STORAGE_DIR", "crm_enquiries")

from crm_enquiries.crews import compat  # noqa: F401 — Groq/LiteLLM compatibility patch

from crm_enquiries.api.approval import router as approval_router
from crm_enquiries.api.enquiries import router as enquiries_router
from crm_enquiries.api.voice import router as voice_router
from crm_enquiries.api.webhooks import router as webhooks_router
from crm_enquiries.config import get_settings
from crm_enquiries.database import init_db
from crm_enquiries.services.knowledge_base import KnowledgeBaseService

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    kb = KnowledgeBaseService()
    count = kb.ingest()
    logger.info("Knowledge base ready: %d chunks", count)
    yield


app = FastAPI(
    title="Glancy Fawcett CRM Enquiry System",
    description="FastAPI + CrewAI enquiry intake, classification, email response, and meeting follow-up",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(enquiries_router)
app.include_router(approval_router)
app.include_router(webhooks_router)
app.include_router(voice_router)

_static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "crm_enquiries"}


def run() -> None:
    import sys

    settings = get_settings()
    # Uvicorn --reload spawns a child worker; breakpoints in route handlers only
    # hit when the debugger is attached to that worker, not the reloader parent.
    use_reload = settings.is_development and "debugpy" not in sys.modules
    uvicorn.run(
        "crm_enquiries.main:app",
        host="0.0.0.0",
        port=8000,
        reload=use_reload,
    )


if __name__ == "__main__":
    run()
