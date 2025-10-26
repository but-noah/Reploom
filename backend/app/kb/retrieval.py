"""KB retrieval and search functionality."""
import logging
import uuid
from datetime import datetime
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from app.kb.client import get_qdrant_client, ensure_collection_exists
from app.kb.chunker import Chunk, chunk_text, deduplicate_chunks, compute_content_hash
from app.kb.embeddings import generate_embeddings, generate_single_embedding
from app.kb.models import KBChunk, KBSearchResult
from app.core.config import settings

logger = logging.getLogger(__name__)


def upsert_document(
    file_content: str,
    workspace_id: str,
    source: str = "upload",
    title: str | None = None,
    url: str | None = None,
    tags: list[str] | None = None,
    collection_name: str | None = None,
) -> dict:
    """
    Chunk, embed, and upsert a document into Qdrant.

    Args:
        file_content: Full text content of the document
        workspace_id: Workspace identifier
        source: Source type (e.g., "upload", "url")
        title: Document title
        url: Source URL if applicable
        tags: List of tags for filtering
        collection_name: Qdrant collection (defaults to settings)

    Returns:
        Dict with upload statistics
    """
    collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
    tags = tags or []

    # Ensure collection exists
    ensure_collection_exists(collection_name)

    # Step 1: Chunk the text
    logger.info(f"Chunking document (workspace={workspace_id}, source={source})")
    chunks = chunk_text(file_content, chunk_size=800, chunk_overlap=200)

    # Step 2: Deduplicate by content hash
    original_count = len(chunks)
    chunks = deduplicate_chunks(chunks)
    dedup_count = len(chunks)

    logger.info(f"Deduplication: {original_count} -> {dedup_count} chunks ({original_count - dedup_count} duplicates removed)")

    if not chunks:
        logger.warning("No chunks to upload after deduplication")
        return {
            "chunks_total": 0,
            "chunks_uploaded": 0,
            "duplicates_skipped": 0,
        }

    # Step 3: Generate embeddings in batch
    chunk_texts = [c.content for c in chunks]
    embeddings = generate_embeddings(chunk_texts, batch_size=100)

    # Step 4: Create points with stable IDs (based on content hash)
    client = get_qdrant_client()
    points = []

    for chunk, embedding in zip(chunks, embeddings):
        # Use content hash as stable ID (ensures same content = same ID)
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.content_hash))

        payload = {
            "workspace_id": workspace_id,
            "source": source,
            "title": title,
            "url": url,
            "tags": tags,
            "content": chunk.content,
            "content_hash": chunk.content_hash,
            "created_at": datetime.utcnow().isoformat(),
        }

        points.append(PointStruct(
            id=point_id,
            vector=embedding,
            payload=payload,
        ))

    # Step 5: Upsert to Qdrant (upsert = insert or update if exists)
    logger.info(f"Upserting {len(points)} points to Qdrant collection '{collection_name}'")
    client.upsert(
        collection_name=collection_name,
        points=points,
    )

    logger.info(f"Successfully uploaded {len(points)} chunks")

    return {
        "chunks_total": original_count,
        "chunks_uploaded": dedup_count,
        "duplicates_skipped": original_count - dedup_count,
    }


def search_kb(
    query: str,
    workspace_id: str,
    k: int = 5,
    with_vectors: bool = False,
    collection_name: str | None = None,
) -> list[KBSearchResult]:
    """
    Search KB for relevant chunks.

    Args:
        query: Search query text
        workspace_id: Filter by workspace
        k: Number of results to return
        with_vectors: Include vectors in response (debug mode)
        collection_name: Qdrant collection name

    Returns:
        List of search results ordered by relevance
    """
    collection_name = collection_name or settings.QDRANT_COLLECTION_NAME
    client = get_qdrant_client()

    # Generate query embedding
    logger.info(f"Searching KB: query='{query[:50]}...', workspace={workspace_id}, k={k}")
    query_embedding = generate_single_embedding(query)

    # Search with workspace filter
    search_results = client.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="workspace_id",
                    match=MatchValue(value=workspace_id),
                )
            ]
        ),
        limit=k,
        with_vectors=with_vectors,  # Optimize: skip vectors by default
    )

    # Convert to KBSearchResult
    results = []
    for hit in search_results:
        payload = hit.payload
        results.append(KBSearchResult(
            chunk_id=str(hit.id),
            content=payload.get("content", ""),
            score=hit.score,
            workspace_id=payload.get("workspace_id", ""),
            source=payload.get("source", "unknown"),
            title=payload.get("title"),
            url=payload.get("url"),
            tags=payload.get("tags", []),
        ))

    logger.info(f"Found {len(results)} results")
    return results
