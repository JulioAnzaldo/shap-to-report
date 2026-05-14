"""
ingest.py — Load corpus.json into ChromaDB with OpenAI embeddings.

Usage:
    python -m backend.rag.ingest            # from project root
    python backend/rag/ingest.py            # direct

Idempotent: re-running upserts by chunk ID, so it is safe to re-run after
adding new chunks to corpus.json.

Environment variables (loaded from .env):
    OPENAI_API_KEY   — required
    CHROMA_PATH      — optional, defaults to ./chroma_db at project root
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent.parent
load_dotenv(_ROOT / ".env")

CORPUS_PATH = Path(__file__).parent / "corpus.json"
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", str(_ROOT / "backend" / "chroma_db")))
COLLECTION_NAME = "shap_rag_corpus"
EMBED_MODEL = "text-embedding-3-small"
EMBED_BATCH = 100          # OpenAI allows up to 2048 inputs per call; keep conservative
EMBED_RETRY_DELAY = 5      # seconds to wait on rate-limit before retrying


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_chunk_id(chunk: dict, idx: int) -> str:
    """Stable ID: source_body + section slug + index."""
    slug = chunk["section"].replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
    return f"{chunk['source_body']}__{slug}__{idx:04d}"


def _embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts, retrying once on rate-limit."""
    for attempt in range(2):
        try:
            response = client.embeddings.create(model=EMBED_MODEL, input=texts)
            return [item.embedding for item in response.data]
        except Exception as exc:
            if attempt == 0 and "rate" in str(exc).lower():
                print(f"  Rate limit hit, waiting {EMBED_RETRY_DELAY}s…")
                time.sleep(EMBED_RETRY_DELAY)
            else:
                raise


# ── Main ──────────────────────────────────────────────────────────────────────

def ingest() -> None:
    print(f"Loading corpus from {CORPUS_PATH}")
    chunks: list[dict] = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    print(f"  {len(chunks)} chunks found")

    print(f"Connecting to ChromaDB at {CHROMA_PATH}")
    chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    openai_client = OpenAI()

    # Build parallel lists for ChromaDB upsert
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for i, chunk in enumerate(chunks):
        ids.append(_make_chunk_id(chunk, i))
        documents.append(chunk["text"])
        metadatas.append(
            {
                "source_body": chunk["source_body"],
                "document": chunk["document"],
                "section": chunk["section"],
                "topic": chunk["topic"],
            }
        )

    # Embed in batches
    print(f"Embedding {len(documents)} texts with {EMBED_MODEL}…")
    all_embeddings: list[list[float]] = []
    for start in range(0, len(documents), EMBED_BATCH):
        batch = documents[start : start + EMBED_BATCH]
        print(f"  Batch {start // EMBED_BATCH + 1}: {len(batch)} texts")
        all_embeddings.extend(_embed_batch(openai_client, batch))

    # Upsert into ChromaDB
    print("Upserting into ChromaDB…")
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=all_embeddings,
        metadatas=metadatas,
    )

    count = collection.count()
    print(f"Done. Collection '{COLLECTION_NAME}' now has {count} documents.")


if __name__ == "__main__":
    ingest()
