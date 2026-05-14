"""
retriever.py — Query ChromaDB for relevant chunks given a natural-language query.

Usage (from app.py):
    from backend.rag.retriever import Retriever

    retriever = Retriever()          # lazy-loads ChromaDB on first call
    chunks = retriever.query(
        query_text="sensor fault in power subsystem",
        source_bodies=["NASA_Lessons_Learned", "NASA_NPR"],
        n_results=5,
    )
    # chunks: list of dicts with keys:
    #   source_body, document, section, topic, text, relevance_score

Environment variables (loaded from .env):
    OPENAI_API_KEY   — required
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

_ROOT = Path(__file__).parent.parent.parent
load_dotenv(_ROOT / ".env")

CHROMA_PATH = Path(os.getenv("CHROMA_PATH", str(_ROOT / "backend" / "chroma_db")))
COLLECTION_NAME = "shap_rag_corpus"
EMBED_MODEL = "text-embedding-3-small"
DEFAULT_N_RESULTS = 5


class Retriever:
    """
    Thin wrapper around ChromaDB for semantic retrieval.

    The client and collection are initialised lazily on the first call to
    ``query()``, so importing this module does not require ChromaDB to be
    populated yet.
    """

    def __init__(self) -> None:
        self._chroma: chromadb.PersistentClient | None = None
        self._collection: Any = None
        self._openai = OpenAI()

    # ── Private ───────────────────────────────────────────────────────────────

    def _ensure_collection(self) -> None:
        if self._collection is not None:
            return
        self._chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self._collection = self._chroma.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _embed(self, text: str) -> list[float]:
        response = self._openai.embeddings.create(model=EMBED_MODEL, input=[text])
        return response.data[0].embedding

    # ── Public ────────────────────────────────────────────────────────────────

    def query(self,query_text: str, source_bodies: list[str] | None = None, n_results: int = DEFAULT_N_RESULTS,) -> list[dict[str, Any]]:
        """
        Return up to ``n_results`` chunks most relevant to ``query_text``.

        Parameters
        ----------
        query_text:
            Free-text query (typically derived from event metadata + SHAP values).
        source_bodies:
            Optional whitelist of source_body values to filter by
            (e.g. ``["EU_AI_Act", "NASA_NPR"]``).  Pass ``None`` or ``[]``
            to search across all sources.
        n_results:
            Maximum number of chunks to return.

        Returns
        -------
        List of chunk dicts, each containing:
            source_body, document, section, topic, text, relevance_score
        """
        self._ensure_collection()

        # Build optional where-filter for source_body
        where: dict | None = None
        if source_bodies:
            if len(source_bodies) == 1:
                where = {"source_body": {"$eq": source_bodies[0]}}
            else:
                where = {"source_body": {"$in": source_bodies}}

        query_embedding = self._embed(query_text)

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[dict[str, Any]] = []
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for doc, meta, dist in zip(docs, metas, distances):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite.
            # Convert to a [0, 1] relevance score.
            relevance_score = max(0.0, 1.0 - dist / 2.0)
            chunks.append(
                {
                    "source_body": meta.get("source_body", ""),
                    "document": meta.get("document", ""),
                    "section": meta.get("section", ""),
                    "topic": meta.get("topic", ""),
                    "text": doc,
                    "relevance_score": relevance_score,
                }
            )

        return chunks
