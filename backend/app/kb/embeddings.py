"""Embedding generation with batching support."""
import logging
from typing import List
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client
_openai_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    """Get or create OpenAI client."""
    global _openai_client

    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    return _openai_client


def generate_embeddings(
    texts: list[str],
    model: str = "text-embedding-3-small",
    batch_size: int = 100,
) -> list[list[float]]:
    """
    Generate embeddings for multiple texts with batching.

    Args:
        texts: List of text strings to embed
        model: OpenAI embedding model to use
        batch_size: Number of texts to process per API call

    Returns:
        List of embedding vectors (one per input text)
    """
    if not texts:
        return []

    client = get_openai_client()
    all_embeddings = []

    # Process in batches to respect API rate limits
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        logger.info(f"Generating embeddings for batch {i//batch_size + 1} ({len(batch)} texts)")

        try:
            response = client.embeddings.create(
                input=batch,
                model=model,
            )

            # Extract embeddings in order
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        except Exception as e:
            logger.error(f"Failed to generate embeddings for batch: {e}")
            raise

    logger.info(f"Generated {len(all_embeddings)} embeddings total")
    return all_embeddings


def generate_single_embedding(
    text: str,
    model: str = "text-embedding-3-small",
) -> list[float]:
    """
    Generate embedding for a single text (convenience wrapper).

    Args:
        text: Text to embed
        model: OpenAI embedding model to use

    Returns:
        Embedding vector
    """
    embeddings = generate_embeddings([text], model=model)
    return embeddings[0] if embeddings else []
