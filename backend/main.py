from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from api.documents import router as documents_router
from config.settings import get_settings
from models.schemas import HealthResponse
from services.llm import get_gemini_service
from services.vector_store import get_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
Path(settings.DATA_RAW_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.DATA_PROCESSED_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.CHROMA_PERSIST_DIRECTORY).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Banking Regulatory Compliance Assistant",
    description="Adaptive RAG pipeline for RBI policy compliance checking.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(documents_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    try:
        vector_store = get_vector_store()
        documents = vector_store.list_documents()
        chunk_count = sum(doc.chunk_count for doc in documents)
        llm_service = get_gemini_service()
        return HealthResponse(
            status="healthy",
            vector_store="healthy",
            embedding_model=settings.EMBEDDING_MODEL_NAME,
            llm_configured=llm_service.configured,
            llm_model=settings.GEMINI_MODEL,
            document_count=len(documents),
            chunk_count=chunk_count,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Backend health check failed.") from exc


@app.on_event("startup")
async def startup_event() -> None:
    try:
        get_vector_store()
        if settings.GEMINI_API_KEY:
            get_gemini_service()
    except Exception as exc:
        logger.warning("Startup initialization warning: %s", exc)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "message": "Banking Regulatory Compliance Assistant backend is running."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=False)
