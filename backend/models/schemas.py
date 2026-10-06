from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    POTENTIALLY_NON_COMPLIANT = "POTENTIALLY_NON_COMPLIANT"
    REQUIRES_FURTHER_REVIEW = "REQUIRES_FURTHER_REVIEW"


class SourceCitation(BaseModel):
    document: str = Field(..., description="Document title or filename")
    page: int = Field(..., description="1-indexed page number in the source PDF")
    section: str = Field(..., description="Section or chapter title/clause")
    evidence: str = Field(..., description="Exact textual excerpt from the source chunk")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User query or banking compliance scenario")
    category: Optional[str] = Field(None, description="Optional category filter")


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Grounded answer based strictly on retrieved RBI context")
    compliance_status: Optional[ComplianceStatus] = Field(
        None, description="Assessed status for scenarios: COMPLIANT, POTENTIALLY_NON_COMPLIANT, or REQUIRES_FURTHER_REVIEW"
    )
    sources: List[SourceCitation] = Field(
        default_factory=list, description="Citations directly extracted from retrieved chunk metadata"
    )
    recommended_action: Optional[str] = Field(
        None, description="Actionable recommendation based strictly on regulatory requirements"
    )
    is_scenario: bool = Field(default=False, description="Whether the request was classified as a compliance scenario")


class ComplianceAssessment(BaseModel):
    status: ComplianceStatus = Field(..., description="Compliance status")
    reason: str = Field(..., description="Detailed rationale based only on retrieved regulatory clauses")
    applicable_requirements: List[str] = Field(
        default_factory=list, description="Applicable RBI regulations and clauses cited"
    )
    evidence: List[str] = Field(
        default_factory=list, description="Direct excerpts from retrieved RBI text supporting the assessment"
    )
    recommended_action: str = Field(
        ..., description="Recommended compliance actions or corrective steps based only on regulations"
    )


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    source: str = "RBI"
    page_number: int
    section: str
    category: str
    publication_date: Optional[str] = None
    effective_date: Optional[str] = None
    sha256: Optional[str] = None


class ChunkRecord(BaseModel):
    text: str
    metadata: ChunkMetadata
    token_count: int


class DocumentInfo(BaseModel):
    document_id: str
    name: str
    category: str
    chunk_count: int
    upload_date: str
    status: str
    sha256: Optional[str] = None
    publication_date: Optional[str] = None
    effective_date: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    document_id: str
    name: str
    category: str
    chunks_count: int
    status: str
    message: str


class ReindexResponse(BaseModel):
    status: str
    message: str
    indexed_documents: int
    indexed_chunks: int


class HealthResponse(BaseModel):
    status: str
    vector_store: str
    embedding_model: str
    llm_configured: bool
    llm_model: str
    document_count: int
    chunk_count: int


class RetrievedChunk(BaseModel):
    text: str
    document: str
    document_id: str
    page: int
    section: str
    score: float
    category: str
    publication_date: Optional[str] = None
    effective_date: Optional[str] = None
