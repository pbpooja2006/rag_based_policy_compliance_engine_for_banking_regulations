from __future__ import annotations

import re
from typing import Optional

from models.schemas import ComplianceStatus, RetrievedChunk
from services.llm import get_gemini_service


SCENARIO_HINTS = [
    r"\bscenario\b",
    r"\bwhat if\b",
    r"\bis it compliant\b",
    r"\bcompliant\b",
    r"\bliability\b",
    r"\bfraud\b",
    r"\bunauthorised\b",
    r"\bunauthorized\b",
    r"\bcustomer\b",
    r"\baccount\b",
    r"\bloan\b",
]


def is_compliance_scenario(question: str) -> bool:
    text = question.strip().lower()
    if not text:
        return False
    return any(re.search(pattern, text) for pattern in SCENARIO_HINTS)


def build_chat_assessment(question: str, retrieved_chunks: list[RetrievedChunk], force_scenario: Optional[bool] = None) -> tuple[bool, ComplianceStatus, str, list[str], list[str], str]:
    scenario = is_compliance_scenario(question) if force_scenario is None else force_scenario
    if not scenario:
        return scenario, ComplianceStatus.REQUIRES_FURTHER_REVIEW, "", [], [], ""

    if not retrieved_chunks:
        return (
            True,
            ComplianceStatus.REQUIRES_FURTHER_REVIEW,
            "No sufficiently relevant regulatory text was retrieved.",
            [],
            [],
            "Collect more facts or upload additional RBI source documents.",
        )

    payload = get_gemini_service().generate_compliance_assessment(question, retrieved_chunks)
    return (
        True,
        payload.status,
        payload.reason,
        payload.applicable_requirements,
        payload.evidence,
        payload.recommended_action,
    )
