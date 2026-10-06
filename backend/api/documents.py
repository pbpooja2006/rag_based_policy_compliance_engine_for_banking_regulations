from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config.settings import get_settings
from models.schemas import DocumentInfo, DocumentUploadResponse, ReindexResponse
from services.document_processor import (
    DocumentProcessingError,
    load_json,
    parse_pdf,
    save_json,
    sanitize_name,
    sha256_bytes,
)
from services.embeddings import get_embedding_service
from services.vector_store import VectorStoreError, get_vector_store

router = APIRouter()


def _raw_dir() -> Path:
    return Path(get_settings().DATA_RAW_DIR)


def _manifest_path() -> Path:
    return Path(get_settings().RAW_MANIFEST_FILE)


def _record_manifest_entry(
    *,
    title: str,
    source_url: str,
    filename: str,
    sha256: str,
    publication_date: Optional[str],
    effective_date: Optional[str],
) -> None:
    path = _manifest_path()
    manifest = load_json(path, [])
    manifest = [entry for entry in manifest if entry.get("sha256") != sha256]
    manifest.append(
        {
            "title": title,
            "source_url": source_url,
            "filename": filename,
            "download_date": datetime.now(timezone.utc).isoformat(),
            "sha256": sha256,
            "publication_date": publication_date,
            "effective_date": effective_date,
        }
    )
    save_json(path, manifest)


def _save_upload_file(file: UploadFile, document_id: str) -> Path:
    raw_dir = _raw_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_name(file.filename or "uploaded-document")
    target = raw_dir / f"{document_id}-{safe_name}.pdf"
    with target.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return target


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents() -> list[DocumentInfo]:
    try:
        return get_vector_store().list_documents()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to list indexed documents.") from exc


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(...),
    publication_date: Optional[str] = Form(None),
    effective_date: Optional[str] = Form(None),
) -> DocumentUploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    document_id = uuid4().hex
    try:
        raw_path = _save_upload_file(file, document_id)
        data = raw_path.read_bytes()
        file_hash = sha256_bytes(data)

        vector_store = get_vector_store()
        if vector_store.has_sha256(file_hash):
            raw_path.unlink(missing_ok=True)
            raise HTTPException(status_code=409, detail="This document already exists in the knowledge base.")

        processed = parse_pdf(
            raw_path,
            document_id=document_id,
            document_name=file.filename,
            category=category,
            source_url="uploaded",
            publication_date=publication_date,
            effective_date=effective_date,
        )
        embeddings = get_embedding_service().embed_documents([record.text for record in processed.chunk_records])
        stored_info = vector_store.add_document(processed, embeddings)
        _record_manifest_entry(
            title=stored_info.name,
            source_url="uploaded",
            filename=raw_path.name,
            sha256=stored_info.sha256 or file_hash,
            publication_date=stored_info.publication_date,
            effective_date=stored_info.effective_date,
        )
        return DocumentUploadResponse(
            document_id=stored_info.document_id,
            name=stored_info.name,
            category=stored_info.category,
            chunks_count=stored_info.chunk_count,
            status=stored_info.status,
            message="Document uploaded and indexed successfully.",
        )
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except VectorStoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            file.file.close()
        except Exception:
            pass


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str) -> dict[str, str]:
    try:
        deleted = get_vector_store().delete_document(document_id)
    except VectorStoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"status": "deleted", "document_id": document_id}


@router.post("/documents/reindex", response_model=ReindexResponse)
async def reindex_documents() -> ReindexResponse:
    settings = get_settings()
    raw_dir = Path(settings.DATA_RAW_DIR)
    manifest = load_json(_manifest_path(), [])
    vector_store = get_vector_store()
    vector_store.clear()

    indexed_documents = 0
    indexed_chunks = 0
    errors: list[str] = []
    for pdf_path in sorted(path for path in raw_dir.iterdir() if path.is_file() and path.suffix.lower() == ".pdf"):
        try:
            metadata = next((item for item in manifest if item.get("filename") == pdf_path.name), {})
            document_id = metadata.get("document_id") or sanitize_name(pdf_path.stem)
            processed = parse_pdf(
                pdf_path,
                document_id=document_id,
                document_name=metadata.get("title") or pdf_path.stem,
                category=metadata.get("category") or "General Regulatory Directive",
                source_url=metadata.get("source_url"),
                publication_date=metadata.get("publication_date"),
                effective_date=metadata.get("effective_date"),
            )
            embeddings = get_embedding_service().embed_documents([record.text for record in processed.chunk_records])
            vector_store.add_document(processed, embeddings)
            indexed_documents += 1
            indexed_chunks += processed.chunk_count
        except Exception as exc:
            errors.append(f"{pdf_path.name}: {exc}")

    message = "Reindex completed."
    if errors:
        message += " Some documents failed to index: " + "; ".join(errors)
    return ReindexResponse(
        status="completed",
        message=message,
        indexed_documents=indexed_documents,
        indexed_chunks=indexed_chunks,
    )
