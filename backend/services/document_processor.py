from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import fitz

from config.settings import get_settings
from models.schemas import ChunkMetadata, ChunkRecord, DocumentInfo


class DocumentProcessingError(RuntimeError):
    pass


class DuplicateDocumentError(DocumentProcessingError):
    pass


@dataclass(slots=True)
class ProcessedDocument:
    document_id: str
    document_name: str
    category: str
    sha256: str
    raw_path: str
    source_url: Optional[str]
    publication_date: Optional[str]
    effective_date: Optional[str]
    upload_date: str
    chunk_records: list[ChunkRecord]

    @property
    def chunk_count(self) -> int:
        return len(self.chunk_records)

    def to_document_info(self) -> DocumentInfo:
        return DocumentInfo(
            document_id=self.document_id,
            name=self.document_name,
            category=self.category,
            chunk_count=self.chunk_count,
            upload_date=self.upload_date,
            status="indexed",
            sha256=self.sha256,
            publication_date=self.publication_date,
            effective_date=self.effective_date,
        )


_SECTION_PATTERNS = [
    re.compile(r"^(chapter|section|part|annex|schedule)\s+[ivx\d]+", re.IGNORECASE),
    re.compile(r"^\d+(\.\d+)*\s+.+"),
    re.compile(r"^[A-Z][A-Z0-9\s,/&().-]{7,}$"),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_name(name: str) -> str:
    stem = Path(name).stem.strip().lower()
    stem = re.sub(r"[^a-z0-9]+", "-", stem)
    return re.sub(r"-+", "-", stem).strip("-") or "document"


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    cleaned_lines: list[str] = []
    blank_run = 0
    for line in lines:
        if not line:
            blank_run += 1
            if blank_run <= 1:
                cleaned_lines.append("")
            continue
        blank_run = 0
        cleaned_lines.append(re.sub(r"\s+", " ", line))
    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _looks_like_heading(line: str) -> bool:
    candidate = line.strip()
    if len(candidate) < 4 or len(candidate) > 140:
        return False
    return any(pattern.match(candidate) for pattern in _SECTION_PATTERNS)


def extract_dates(text: str) -> tuple[Optional[str], Optional[str]]:
    date_patterns = [
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
        r"\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
    ]
    publication_date: Optional[str] = None
    effective_date: Optional[str] = None
    for pattern in date_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            publication_date = match.group(0)
            break
    eff_match = re.search(r"with effect from\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", text, flags=re.IGNORECASE)
    if eff_match:
        effective_date = eff_match.group(1)
    return publication_date, effective_date


def estimate_tokens(text: str) -> int:
    return max(1, len(re.findall(r"\S+", text)))


def _chunk_paragraphs(paragraphs: list[str], chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    buffer: list[str] = []
    buffer_tokens = 0
    overlap_tokens = max(0, overlap)

    def flush_buffer() -> None:
        nonlocal buffer, buffer_tokens
        if buffer:
            chunks.append("\n\n".join(buffer).strip())
            if overlap_tokens and len(buffer) > 1:
                retained: list[str] = []
                retained_tokens = 0
                for para in reversed(buffer):
                    para_tokens = estimate_tokens(para)
                    if retained_tokens + para_tokens > overlap_tokens and retained:
                        break
                    retained.append(para)
                    retained_tokens += para_tokens
                buffer = list(reversed(retained))
                buffer_tokens = retained_tokens
            else:
                buffer = []
                buffer_tokens = 0

    for paragraph in paragraphs:
        tokens = estimate_tokens(paragraph)
        if tokens > chunk_size:
            flush_buffer()
            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            sentence_buffer: list[str] = []
            sentence_tokens = 0
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                stokens = estimate_tokens(sentence)
                if sentence_buffer and sentence_tokens + stokens > chunk_size:
                    chunks.append(" ".join(sentence_buffer).strip())
                    sentence_buffer = sentence_buffer[-1:] if overlap_tokens else []
                    sentence_tokens = sum(estimate_tokens(item) for item in sentence_buffer)
                sentence_buffer.append(sentence)
                sentence_tokens += stokens
            if sentence_buffer:
                chunks.append(" ".join(sentence_buffer).strip())
            continue

        if buffer_tokens + tokens > chunk_size and buffer:
            flush_buffer()

        buffer.append(paragraph)
        buffer_tokens += tokens

    flush_buffer()
    return [chunk for chunk in chunks if chunk.strip()]


def build_chunks_for_page(
    document_id: str,
    document_name: str,
    category: str,
    page_number: int,
    page_text: str,
    sha256: str,
    publication_date: Optional[str],
    effective_date: Optional[str],
) -> list[ChunkRecord]:
    settings = get_settings()
    cleaned = normalize_whitespace(page_text)
    if not cleaned:
        return []

    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
    section_groups: list[tuple[str, list[str]]] = []
    current_section = f"Page {page_number}"
    paragraphs: list[str] = []

    def flush_section() -> None:
        nonlocal paragraphs
        if paragraphs:
            section_groups.append((current_section, paragraphs))
            paragraphs = []

    for line in lines:
        if _looks_like_heading(line):
            flush_section()
            current_section = line
        else:
            paragraphs.append(line)
    flush_section()
    if not section_groups:
        section_groups = [(current_section, [cleaned])]

    section_chunks: list[tuple[str, str]] = []
    for section, section_paragraphs in section_groups:
        section_chunks.extend(
            (section, chunk)
            for chunk in _chunk_paragraphs(section_paragraphs, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        )

    chunk_records: list[ChunkRecord] = []
    for index, (section, chunk_text) in enumerate(section_chunks, start=1):
        chunk_id = f"{document_id}-p{page_number}-c{index}"
        chunk_records.append(
            ChunkRecord(
                text=chunk_text,
                metadata=ChunkMetadata(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    document_name=document_name,
                    source="RBI",
                    page_number=page_number,
                    section=section,
                    category=category,
                    publication_date=publication_date,
                    effective_date=effective_date,
                    sha256=sha256,
                ),
                token_count=estimate_tokens(chunk_text),
            )
        )
    return chunk_records


def parse_pdf(
    pdf_path: Path,
    document_id: str,
    document_name: str,
    category: str,
    source_url: Optional[str] = None,
    publication_date: Optional[str] = None,
    effective_date: Optional[str] = None,
) -> ProcessedDocument:
    if not pdf_path.exists():
        raise DocumentProcessingError(f"PDF file not found: {pdf_path}")

    sha256 = sha256_file(pdf_path)
    try:
        document = fitz.open(pdf_path)
    except Exception as exc:  # pragma: no cover - library specific failure
        raise DocumentProcessingError(f"Failed to open PDF: {exc}") from exc

    try:
        if document.page_count == 0:
            raise DocumentProcessingError("The PDF has no pages.")

        all_chunks: list[ChunkRecord] = []
        saw_text = False
        if publication_date is None or effective_date is None:
            extracted_preview = []
            for page_index in range(min(document.page_count, 3)):
                extracted_preview.append(document[page_index].get_text("text"))
            preview_text = "\n".join(extracted_preview)
            preview_publication, preview_effective = extract_dates(preview_text)
            publication_date = publication_date or preview_publication
            effective_date = effective_date or preview_effective

        for page_number in range(1, document.page_count + 1):
            page_text = document[page_number - 1].get_text("text")
            if page_text.strip():
                saw_text = True
            all_chunks.extend(
                build_chunks_for_page(
                    document_id=document_id,
                    document_name=document_name,
                    category=category,
                    page_number=page_number,
                    page_text=page_text,
                    sha256=sha256,
                    publication_date=publication_date,
                    effective_date=effective_date,
                )
            )

        if not saw_text:
            raise DocumentProcessingError("The PDF does not contain extractable text. Scanned PDFs are not supported.")

        if not all_chunks:
            raise DocumentProcessingError("No searchable text chunks could be extracted from the PDF.")

        upload_date = datetime.now(timezone.utc).isoformat()
        return ProcessedDocument(
            document_id=document_id,
            document_name=document_name,
            category=category,
            sha256=sha256,
            raw_path=str(pdf_path),
            source_url=source_url,
            publication_date=publication_date,
            effective_date=effective_date,
            upload_date=upload_date,
            chunk_records=all_chunks,
        )
    finally:
        document.close()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
