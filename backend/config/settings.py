import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent

    # Gemini LLM
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Embeddings
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    BGE_QUERY_PREFIX: str = "Represent this sentence for searching relevant passages: "

    # ChromaDB
    CHROMA_PERSIST_DIRECTORY: str = str(Path(__file__).resolve().parent.parent.parent / "chroma_db")
    CHROMA_COLLECTION_NAME: str = "rbi_banking_regulations"
    DOC_CATALOG_FILE: str = str(Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "documents.json")
    RAW_MANIFEST_FILE: str = str(Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "sources_manifest.json")

    # Retrieval
    TOP_K: int = 5
    RELEVANCE_THRESHOLD: float = 0.70  # Calibrated from real retrieval results
    RETRIEVAL_MIN_CONTEXT_CHUNKS: int = 2

    # Chunking (~500-800 tokens, 10-15% overlap)
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100

    # Data directories
    DATA_RAW_DIR: str = str(Path(__file__).resolve().parent.parent.parent / "data" / "raw")
    DATA_PROCESSED_DIR: str = str(Path(__file__).resolve().parent.parent.parent / "data" / "processed")

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = ""
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    def model_post_init(self, __context) -> None:
        # Resolve local paths from backend/ regardless of the launch working directory.
        for name in ("CHROMA_PERSIST_DIRECTORY", "DOC_CATALOG_FILE", "RAW_MANIFEST_FILE", "DATA_RAW_DIR", "DATA_PROCESSED_DIR"):
            value = Path(getattr(self, name))
            if not value.is_absolute():
                setattr(self, name, str((Path(self.BASE_DIR) / value).resolve()))
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
