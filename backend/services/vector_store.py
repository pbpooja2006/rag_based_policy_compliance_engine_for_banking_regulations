from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import chromadb

from config.settings import get_settings
from models.schemas import DocumentInfo, RetrievedChunk
from services.document_processor import ProcessedDocument, load_json, save_json


class VectorStoreError(RuntimeError):
    pass


class VectorStoreService:
    _instance: Optional["VectorStoreService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.settings = get_settings()
        self.persist_path = Path(self.settings.CHROMA_PERSIST_DIRECTORY)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.catalog_path = Path(self.settings.DOC_CATALOG_FILE)
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_path))
        self.collection = self.client.get_or_create_collection(
            name=self.settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def _read_catalog(self) -> list[dict[str, Any]]:
        return load_json(self.catalog_path, [])

    def _write_catalog(self, docs: list[dict[str, Any]]) -> None:
        save_json(self.catalog_path, docs)

    def _upsert_catalog(self, info: DocumentInfo, raw_path: Optional[str] = None, source_url: Optional[str] = None) -> None:
        docs = self._read_catalog()
        filtered = [item for item in docs if item.get("document_id") != info.document_id]
        entry = info.model_dump()
        if raw_path:
            entry["raw_path"] = raw_path
        if source_url:
            entry["source_url"] = source_url
        filtered.append(entry)
        self._write_catalog(filtered)

    @staticmethod
    def _clean_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                cleaned[key] = value
            else:
                cleaned[key] = str(value)
        return cleaned

    def list_documents(self) -> list[DocumentInfo]:
        return [DocumentInfo.model_validate(item) for item in self._read_catalog()]

    def has_sha256(self, sha256: str) -> bool:
        docs = self._read_catalog()
        return any(item.get("sha256") == sha256 for item in docs)

    def add_document(self, processed: ProcessedDocument, embeddings: list[list[float]]) -> DocumentInfo:
        if len(embeddings) != len(processed.chunk_records):
            raise VectorStoreError("Embedding count does not match chunk count.")

        try:
            self.collection.delete(where={"document_id": processed.document_id})
            self.collection.add(
                ids=[record.metadata.chunk_id for record in processed.chunk_records],
                embeddings=embeddings,
                documents=[record.text for record in processed.chunk_records],
                metadatas=[self._clean_metadata(record.metadata.model_dump()) for record in processed.chunk_records],
            )
        except Exception as exc:  # pragma: no cover - chroma internals
            raise VectorStoreError(f"Failed to store chunks in ChromaDB: {exc}") from exc

        info = processed.to_document_info()
        self._upsert_catalog(info, raw_path=processed.raw_path, source_url=processed.source_url)
        return info

    def delete_document(self, document_id: str) -> bool:
        try:
            self.collection.delete(where={"document_id": document_id})
        except Exception as exc:
            raise VectorStoreError(f"Failed to delete document chunks: {exc}") from exc

        docs = self._read_catalog()
        new_docs = [item for item in docs if item.get("document_id") != document_id]
        deleted = len(new_docs) != len(docs)
        self._write_catalog(new_docs)
        return deleted

    def clear(self) -> None:
        try:
            self.client.delete_collection(self.settings.CHROMA_COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._write_catalog([])

    def query(self, query_embedding: list[float], top_k: int, category: Optional[str] = None) -> list[RetrievedChunk]:
        where = {"category": category} if category else None
        try:
            response = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError(f"Failed to query ChromaDB: {exc}") from exc

        documents = response.get("documents", [[]])[0]
        metadatas = response.get("metadatas", [[]])[0]
        distances = response.get("distances", [[]])[0]
        results: list[RetrievedChunk] = []
        for text, metadata, distance in zip(documents, metadatas, distances):
            similarity = max(0.0, 1.0 - float(distance))
            results.append(
                RetrievedChunk(
                    text=text,
                    document=metadata.get("document_name") or metadata.get("document_id") or "Unknown document",
                    document_id=metadata.get("document_id", ""),
                    page=int(metadata.get("page_number", 0)),
                    section=metadata.get("section", ""),
                    score=similarity,
                    category=metadata.get("category", ""),
                    publication_date=metadata.get("publication_date"),
                    effective_date=metadata.get("effective_date"),
                )
            )
        return results

    def rehydrate_catalog_entry(self, processed: ProcessedDocument, raw_path: Optional[str] = None) -> None:
        self._upsert_catalog(processed.to_document_info(), raw_path=raw_path or processed.raw_path, source_url=processed.source_url)


def get_vector_store() -> VectorStoreService:
    return VectorStoreService()
