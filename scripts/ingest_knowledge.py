#!/usr/bin/env python3
"""Ingest Glancy Fawcett FAQ markdown into Chroma vector store.

Usage:
    python scripts/ingest_knowledge.py [--force]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crm_enquiries.services.knowledge_base import KnowledgeBaseService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest FAQ knowledge base into Chroma")
    parser.add_argument("--force", action="store_true", help="Re-ingest even if collection exists")
    args = parser.parse_args()

    kb = KnowledgeBaseService()
    count = kb.ingest(force=args.force)
    print(f"Ingested {count} chunks into knowledge base at {kb.settings.chroma_persist_dir}")


if __name__ == "__main__":
    main()
