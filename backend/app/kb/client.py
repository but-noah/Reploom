"""Qdrant client initialization and collection management."""
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Qdrant client
_qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client instance."""
    global _qdrant_client

    if _qdrant_client is None:
        logger.info(f"Initializing Qdrant client: {settings.QDRANT_URL}")
        _qdrant_client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
        )

    return _qdrant_client


def ensure_collection_exists(
    collection_name: str | None = None,
    vector_size: int = 1536,  # OpenAI text-embedding-3-small dimension
) -> None:
    """
    Ensure Qdrant collection exists with proper configuration.

    Args:
        collection_name: Name of collection (defaults to settings.QDRANT_COLLECTION_NAME)
        vector_size: Dimension of embedding vectors
    """
    collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
    client = get_qdrant_client()

    # Check if collection exists
    collections = client.get_collections().collections
    exists = any(c.name == collection_name for c in collections)

    if not exists:
        logger.info(f"Creating Qdrant collection: {collection_name}")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info(f"Collection '{collection_name}' created successfully")
    else:
        logger.info(f"Collection '{collection_name}' already exists")
