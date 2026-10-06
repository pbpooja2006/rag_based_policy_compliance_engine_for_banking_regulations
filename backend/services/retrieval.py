from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config.settings import get_settings
from models.schemas import RetrievedChunk
from services.embeddings import get_embedding_service
from services.vector_store import get_vector_store


@dataclass(slots=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    top_score: float
    meets_threshold: bool


def retrieve_relevant_chunks(question: str, category: Optional[str] = None, top_k: Optional[int] = None) -> RetrievalResult:
    settings = get_settings()
    vector_store = get_vector_store()
    embedding = get_embedding_service().embed_query(question)
    chunks = vector_store.query(embedding, top_k or settings.TOP_K, category=category)
    top_score = chunks[0].score if chunks else 0.0
    meets_threshold = bool(chunks) and top_score >= settings.RELEVANCE_THRESHOLD
    return RetrievalResult(chunks=chunks, top_score=top_score, meets_threshold=meets_threshold)


def chunks_to_sources(chunks: list[RetrievedChunk]) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    for chunk in chunks:
        sources.append(
            {
                "document": chunk.document,
                "page": chunk.page,
                "section": chunk.section,
                "evidence": chunk.text,
            }
        )
    return sources
