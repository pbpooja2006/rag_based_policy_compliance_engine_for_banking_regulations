from __future__ import annotations

from fastapi import APIRouter, HTTPException

from models.schemas import ChatRequest, ChatResponse, ComplianceStatus, SourceCitation
from services.compliance import build_chat_assessment, is_compliance_scenario
from services.llm import get_gemini_service
from services.retrieval import chunks_to_sources, retrieve_relevant_chunks

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        retrieval = retrieve_relevant_chunks(question, category=payload.category)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to retrieve RBI documents.") from exc

    if not retrieval.meets_threshold:
        return ChatResponse(
            answer="I could not find sufficient relevant information in the available RBI documents to answer this confidently.",
            compliance_status=ComplianceStatus.REQUIRES_FURTHER_REVIEW,
            sources=[],
            recommended_action="Try rephrasing the question or upload a more relevant RBI document.",
            is_scenario=is_compliance_scenario(question),
        )

    sources = chunks_to_sources(retrieval.chunks)
    is_scenario = is_compliance_scenario(question)
    if is_scenario:
        _, compliance_status, reason, requirements, evidence, recommended_action = build_chat_assessment(question, retrieval.chunks)
        answer = reason or "AI-assisted assessment, not a legal determination."
        return ChatResponse(
            answer=f"AI-assisted assessment, not a legal determination. {answer}",
            compliance_status=compliance_status,
            sources=[SourceCitation(**item) for item in sources],
            recommended_action=recommended_action,
            is_scenario=True,
        )

    payload_model = get_gemini_service().generate_grounded_answer(question, retrieval.chunks, compliance_mode=False)
    return ChatResponse(
        answer=payload_model.answer,
        compliance_status=payload_model.compliance_status,
        sources=[SourceCitation(**item) for item in sources],
        recommended_action=payload_model.recommended_action,
        is_scenario=False,
    )
