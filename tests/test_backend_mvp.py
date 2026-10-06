from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import main
from backend.models.schemas import ComplianceStatus
from backend.services import embeddings as embeddings_module
from backend.services import vector_store as vector_store_module
from backend.services.document_processor import parse_pdf
from backend.services.embeddings import EmbeddingService


RAW_DIR = ROOT / "data" / "raw"
SAMPLE_PDF = next(RAW_DIR.glob("*.PDF"), None) or next(RAW_DIR.glob("*.pdf"), None)


@dataclass
class TempSettings:
    CHROMA_PERSIST_DIRECTORY: str
    CHROMA_COLLECTION_NAME: str = "test_rbi_collection"
    DOC_CATALOG_FILE: str = ""
    DATA_RAW_DIR: str = ""
    DATA_PROCESSED_DIR: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    BGE_QUERY_PREFIX: str = "Represent this sentence for searching relevant passages: "
    TOP_K: int = 5
    RELEVANCE_THRESHOLD: float = 0.70
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100
    CORS_ORIGINS: list[str] = None
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    def __post_init__(self):
        if self.CORS_ORIGINS is None:
            self.CORS_ORIGINS = ["http://localhost:5173"]


class DummyEmbeddingModel:
    def encode(self, texts, **kwargs):
        if isinstance(texts, str):
            return np.array([1.0, 0.0, 0.0], dtype=float)
        return np.array([[1.0, 0.0, 0.0] for _ in texts], dtype=float)


class DummyGeminiService:
    configured = True

    def generate_grounded_answer(self, question, chunks, compliance_mode=False):
        from backend.services.llm import GroundedAnswerPayload

        return GroundedAnswerPayload(
            answer="Mock grounded answer.",
            recommended_action="Mock recommendation.",
            compliance_status=ComplianceStatus.REQUIRES_FURTHER_REVIEW,
        )

    def generate_compliance_assessment(self, question, chunks):
        from backend.services.llm import CompliancePayload

        return CompliancePayload(
            status=ComplianceStatus.REQUIRES_FURTHER_REVIEW,
            reason="Mock assessment.",
            applicable_requirements=["Mock requirement"],
            evidence=["Mock evidence"],
            recommended_action="Mock action.",
        )


@pytest.fixture(autouse=True)
def reset_singletons():
    embeddings_module._embedding_service_instance = None
    vector_store_module.VectorStoreService._instance = None
    yield
    embeddings_module._embedding_service_instance = None
    vector_store_module.VectorStoreService._instance = None


@pytest.fixture()
def client():
    return TestClient(main.app)


def test_pdf_extraction_and_chunking():
    assert SAMPLE_PDF is not None, "Expected RBI PDFs in data/raw"
    processed = parse_pdf(
        SAMPLE_PDF,
        document_id="sample-doc",
        document_name=SAMPLE_PDF.name,
        category="KYC & Customer Due Diligence",
    )
    assert processed.chunk_count > 0
    first = processed.chunk_records[0]
    assert first.metadata.page_number >= 1
    assert first.metadata.document_id == "sample-doc"
    assert first.metadata.source == "RBI"
    assert first.text.strip()


def test_embedding_shape_and_normalization(monkeypatch):
    monkeypatch.setattr(EmbeddingService, "_load_model", lambda self: setattr(self, "_model", DummyEmbeddingModel()))
    embeddings_module._embedding_service_instance = None
    service = embeddings_module.get_embedding_service()
    query = service.embed_query("test query")
    docs = service.embed_documents(["alpha", "beta"])
    assert len(query) == 3
    assert len(docs) == 2
    assert all(len(item) == 3 for item in docs)


def test_chroma_insert_and_retrieve(monkeypatch, tmp_path):
    temp_settings = TempSettings(
        CHROMA_PERSIST_DIRECTORY=str(tmp_path / "chroma"),
        DOC_CATALOG_FILE=str(tmp_path / "documents.json"),
        DATA_RAW_DIR=str(tmp_path / "raw"),
        DATA_PROCESSED_DIR=str(tmp_path / "processed"),
    )
    monkeypatch.setattr(vector_store_module, "get_settings", lambda: temp_settings)
    monkeypatch.setattr(embeddings_module, "get_settings", lambda: temp_settings)
    monkeypatch.setattr(EmbeddingService, "_load_model", lambda self: setattr(self, "_model", DummyEmbeddingModel()))
    embeddings_module._embedding_service_instance = None

    assert SAMPLE_PDF is not None
    processed = parse_pdf(
        SAMPLE_PDF,
        document_id="sample-doc",
        document_name="sample.pdf",
        category="KYC & Customer Due Diligence",
    )
    embeddings = embeddings_module.get_embedding_service().embed_documents([record.text for record in processed.chunk_records])
    store = vector_store_module.get_vector_store()
    info = store.add_document(processed, embeddings)
    results = store.query([1.0, 0.0, 0.0], top_k=3)
    assert info.chunk_count > 0
    assert results
    assert results[0].document
    assert results[0].score >= 0.0


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert "embedding_model" in payload


def test_chat_insufficient_context(client):
    response = client.post("/chat", json={"question": "What are the corporate income tax brackets for banks?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["compliance_status"] == "REQUIRES_FURTHER_REVIEW"
    assert payload["sources"] == []


def test_chat_with_mocked_gemini(monkeypatch, client):
    monkeypatch.setattr("api.chat.get_gemini_service", lambda: DummyGeminiService())
    response = client.post(
        "/chat",
        json={"question": "What are the RBI requirements regarding KFS in digital lending?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Mock grounded answer."
    assert payload["recommended_action"] == "Mock recommendation."


def _make_pdf(path: Path, text: str) -> None:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_upload_delete_and_list(client, tmp_path):
    pdf_path = tmp_path / "upload-test.pdf"
    _make_pdf(pdf_path, "Reserve Bank of India upload test document for ingestion.")
    with pdf_path.open("rb") as handle:
        response = client.post(
            "/documents/upload",
            files={"file": (pdf_path.name, handle, "application/pdf")},
            data={"category": "General Regulatory Directive"},
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    document_id = payload["document_id"]

    docs = client.get("/documents").json()
    assert any(doc["document_id"] == document_id for doc in docs)

    delete_response = client.delete(f"/documents/{document_id}")
    assert delete_response.status_code == 200
    docs_after = client.get("/documents").json()
    assert all(doc["document_id"] != document_id for doc in docs_after)
