"""Knowledge base service — Chroma vector store over FAQ markdown."""

from __future__ import annotations

import logging
from pathlib import Path

from crm_enquiries.config import get_settings

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    COLLECTION_NAME = "glancy_faq"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.knowledge_dir = Path(self.settings.knowledge_dir)
        self._client = None
        self._collection = None

    def _get_embedding_function(self):
        from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

        return OllamaEmbeddingFunction(
            url=self.settings.ollama_base_url,
            model_name=self.settings.embedding_model,
        )

    def _create_collection(self, client):
        return client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            embedding_function=self._get_embedding_function(),
            metadata={
                "description": "Glancy Fawcett FAQ knowledge base",
                "embedding_model": self.settings.embedding_model,
            },
        )

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        try:
            import chromadb

            persist_dir = Path(self.settings.chroma_persist_dir)
            persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(persist_dir))
            self._collection = self._create_collection(self._client)
            logger.info(
                "Chroma collection ready (embeddings via Ollama: %s @ %s)",
                self.settings.embedding_model,
                self.settings.ollama_base_url,
            )
            return self._collection
        except Exception as exc:
            logger.warning("Chroma unavailable, using file fallback: %s", exc)
            return None

    def ingest(self, force: bool = False) -> int:
        collection = self._get_collection()
        md_files = sorted(self.knowledge_dir.glob("*.md"))
        if not md_files:
            logger.warning("No markdown files in %s", self.knowledge_dir)
            return 0

        if collection is None:
            return len(md_files)

        if not force and collection.count() > 0:
            return collection.count()

        if force:
            try:
                self._client.delete_collection(self.COLLECTION_NAME)
                self._collection = self._create_collection(self._client)
                collection = self._collection
            except Exception:
                pass

        docs, ids, metadatas = [], [], []
        for md_path in md_files:
            text = md_path.read_text(encoding="utf-8")
            chunks = self._chunk_text(text, md_path.stem)
            for i, chunk in enumerate(chunks):
                docs.append(chunk)
                ids.append(f"{md_path.stem}_{i}")
                metadatas.append({"source": md_path.name, "section": md_path.stem})

        if docs:
            collection.add(documents=docs, ids=ids, metadatas=metadatas)
        logger.info("Ingested %d chunks from %d files", len(docs), len(md_files))
        return len(docs)

    def _chunk_text(self, text: str, source: str, chunk_size: int = 800) -> list[str]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: list[str] = []
        current = f"[Source: {source}]\n"
        for para in paragraphs:
            if len(current) + len(para) > chunk_size and current.strip():
                chunks.append(current.strip())
                current = f"[Source: {source}]\n"
            current += para + "\n\n"
        if current.strip():
            chunks.append(current.strip())
        return chunks

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        collection = self._get_collection()
        if collection is not None and collection.count() > 0:
            try:
                results = collection.query(query_texts=[query_text], n_results=top_k)
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                return [
                    {"content": doc, "metadata": meta}
                    for doc, meta in zip(documents, metadatas)
                ]
            except Exception as exc:
                logger.warning("Chroma query failed: %s", exc)

        return self._file_fallback_query(query_text, top_k)

    def _file_fallback_query(self, query_text: str, top_k: int) -> list[dict]:
        query_lower = query_text.lower()
        scored: list[tuple[int, dict]] = []
        for md_path in sorted(self.knowledge_dir.glob("*.md")):
            text = md_path.read_text(encoding="utf-8")
            score = sum(1 for word in query_lower.split() if word in text.lower())
            if score > 0:
                scored.append((score, {"content": text[:2000], "metadata": {"source": md_path.name}}))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def get_context_for_enquiry(self, message: str, enquiry_type: str) -> str:
        query = f"{enquiry_type} enquiry: {message}"
        results = self.query(query, top_k=5)
        if not results:
            return "No specific FAQ context found. Use general Glancy Fawcett professionalism."
        parts = []
        for i, r in enumerate(results, 1):
            source = r.get("metadata", {}).get("source", "unknown")
            parts.append(f"### FAQ Excerpt {i} ({source})\n{r['content'][:1500]}")
        return "\n\n".join(parts)
