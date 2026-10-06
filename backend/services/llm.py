from __future__ import annotations

import logging
import time
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

from config.settings import get_settings
from models.schemas import ComplianceStatus, RetrievedChunk

logger = logging.getLogger(__name__)


class GroundedAnswerPayload(BaseModel):
    answer: str = Field(...)
    recommended_action: str = Field(...)
    compliance_status: ComplianceStatus = Field(...)


class CompliancePayload(BaseModel):
    status: ComplianceStatus
    reason: str
    applicable_requirements: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    recommended_action: str


class GeminiService:
    _instance: Optional["GeminiService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.settings = get_settings()
        self._client = None
        if self.settings.GEMINI_API_KEY:
            try:
                from google import genai

                self._client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
            except Exception as exc:  # pragma: no cover - import/runtime specific
                raise RuntimeError(f"Failed to initialize Gemini client: {exc}") from exc

    @property
    def configured(self) -> bool:
        return self._client is not None

    def _format_context(self, chunks: list[RetrievedChunk]) -> str:
        lines: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            lines.append(
                f"[Chunk {index}] Document: {chunk.document}; Page: {chunk.page}; Section: {chunk.section}; Score: {chunk.score:.3f}\n{chunk.text}"
            )
        return "\n\n".join(lines)

    def _generate(self, system_instruction: str, prompt: str) -> str:
        if not self._client:
            raise RuntimeError("Gemini API key is not configured.")

        from google.genai import types

        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                response = self._client.models.generate_content(
                    model=self.settings.GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        top_p=0.9,
                        max_output_tokens=1024,
                        response_mime_type="application/json",
                        system_instruction=system_instruction,
                    ),
                )
                text = getattr(response, "text", None)
                if not text:
                    text = str(response)
                return text
            except Exception as exc:  # pragma: no cover - network/model specific
                last_error = exc
                message = str(exc).lower()
                if any(token in message for token in ["429", "resourceexhausted", "rate", "quota"]):
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise
        if last_error:
            raise last_error
        raise RuntimeError("Gemini request failed without a specific error.")

    def generate_grounded_answer(self, question: str, chunks: list[RetrievedChunk], compliance_mode: bool = False) -> GroundedAnswerPayload:
        system_instruction = (
            "You are a banking regulatory assistant for a college project. Answer only from the supplied RBI context. "
            "Never invent regulations, pages, or sections. If the context is inadequate, say exactly: "
            '"Insufficient information was found in the available regulatory documents." ' 
            "Keep the answer concise and separate regulatory text from interpretation. Return JSON with keys answer, recommended_action, compliance_status. "
            "The compliance_status must be one of COMPLIANT, POTENTIALLY_NON_COMPLIANT, or REQUIRES_FURTHER_REVIEW."
        )
        prompt = (
            f"Question: {question}\n\n"
            f"Compliance mode: {str(compliance_mode).lower()}\n\n"
            f"Context:\n{self._format_context(chunks)}\n\n"
            "Return JSON only."
        )
        if not self.configured:
            return self._fallback_answer(question, chunks, compliance_mode)
        raw = self._generate(system_instruction, prompt)
        try:
            payload = GroundedAnswerPayload.model_validate_json(raw)
        except ValidationError as exc:
            logger.warning("Gemini JSON validation failed; using fallback response: %s", exc)
            return self._fallback_answer(question, chunks, compliance_mode)
        return payload

    def generate_compliance_assessment(self, question: str, chunks: list[RetrievedChunk]) -> CompliancePayload:
        system_instruction = (
            "You are evaluating a banking compliance scenario using only the provided RBI context. "
            "Do not give legal advice. Return JSON with keys status, reason, applicable_requirements, evidence, recommended_action. "
            "If the context is insufficient, use REQUIRES_FURTHER_REVIEW and explain what is missing."
        )
        prompt = f"Scenario: {question}\n\nContext:\n{self._format_context(chunks)}\n\nReturn JSON only."
        if not self.configured:
            return self._fallback_compliance(question, chunks)
        raw = self._generate(system_instruction, prompt)
        try:
            return CompliancePayload.model_validate_json(raw)
        except ValidationError as exc:
            logger.warning("Gemini compliance JSON validation failed; using fallback response: %s", exc)
            return self._fallback_compliance(question, chunks)

    def _fallback_answer(self, question: str, chunks: list[RetrievedChunk], compliance_mode: bool) -> GroundedAnswerPayload:
        if not chunks:
            return GroundedAnswerPayload(
                answer="Insufficient information was found in the available regulatory documents.",
                recommended_action="Review the question against the available RBI documents or upload more relevant regulations.",
                compliance_status=ComplianceStatus.REQUIRES_FURTHER_REVIEW,
            )
        excerpt = chunks[0].text.strip().replace("\n", " ")
        answer = (
            "I could not generate a Gemini-backed response because GEMINI_API_KEY is not configured. "
            f"The most relevant retrieved RBI excerpt is: {excerpt[:900]}"
        )
        status = ComplianceStatus.REQUIRES_FURTHER_REVIEW if compliance_mode else ComplianceStatus.REQUIRES_FURTHER_REVIEW
        return GroundedAnswerPayload(
            answer=answer,
            recommended_action="Configure GEMINI_API_KEY to enable grounded synthesis, or use the retrieved excerpt as a reading aid.",
            compliance_status=status,
        )

    def _fallback_compliance(self, question: str, chunks: list[RetrievedChunk]) -> CompliancePayload:
        if not chunks:
            return CompliancePayload(
                status=ComplianceStatus.REQUIRES_FURTHER_REVIEW,
                reason="No sufficiently relevant regulatory text was retrieved.",
                applicable_requirements=[],
                evidence=[],
                recommended_action="Collect more specific facts or upload more relevant RBI documents.",
            )
        top_text = chunks[0].text.strip().replace("\n", " ")
        return CompliancePayload(
            status=ComplianceStatus.REQUIRES_FURTHER_REVIEW,
            reason="Gemini is not configured, so the assessment is limited to retrieved excerpts and cannot be finalized confidently.",
            applicable_requirements=[f"{chunks[0].document} (page {chunks[0].page})"],
            evidence=[top_text[:500]],
            recommended_action="Enable GEMINI_API_KEY for a grounded compliance assessment or review the retrieved RBI excerpt manually.",
        )


def get_gemini_service() -> GeminiService:
    return GeminiService()
