import logging
from functools import lru_cache
from typing import List

from config.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent re-initialization
        if self._model is None:
            self._load_model()

    def _load_model(self):
        settings = get_settings()
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME} on CPU...")
        try:
            from sentence_transformers import SentenceTransformer
            # Explicitly force CPU
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME, device="cpu")
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load embedding model {settings.EMBEDDING_MODEL_NAME}: {e}", exc_info=True)
            raise RuntimeError(
                f"Failed to load embedding model '{settings.EMBEDDING_MODEL_NAME}'. "
                f"Ensure sentence-transformers is installed and model weights are accessible. Error: {str(e)}"
            )

    @property
    def model(self):
        if self._model is None:
            self._load_model()
        return self._model

    def embed_documents(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Embed document passages without query instruction prefix.
        Embeddings are normalized for cosine similarity.
        """
        if not texts:
            return []
        try:
            # Document chunks must NOT have query prefix
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error embedding document chunks: {e}")
            raise RuntimeError(f"Error encoding document chunks: {str(e)}")

    def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query using the BGE query instruction prefix.
        Embeddings are normalized for cosine similarity.
        """
        settings = get_settings()
        # BGE query instruction prefix for queries only
        prefixed_query = f"{settings.BGE_QUERY_PREFIX}{query.strip()}"
        try:
            embedding = self.model.encode(
                prefixed_query,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            raise RuntimeError(f"Error encoding query: {str(e)}")


_embedding_service_instance = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance


@lru_cache(maxsize=1)
def get_embedding_dimension() -> int:
    service = get_embedding_service()
    return len(service.embed_query("dimension probe"))
