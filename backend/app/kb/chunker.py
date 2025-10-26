"""Text chunking with deduplication."""
import hashlib
from typing import NamedTuple
import tiktoken


class Chunk(NamedTuple):
    """A text chunk with metadata."""
    content: str
    content_hash: str
    start_idx: int
    end_idx: int


def compute_content_hash(text: str) -> str:
    """Compute SHA256 hash of text content for deduplication."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 200,
    encoding_name: str = "cl100k_base",  # OpenAI's tiktoken encoding
) -> list[Chunk]:
    """
    Chunk text into overlapping segments based on token count.

    Args:
        text: Input text to chunk
        chunk_size: Target tokens per chunk (default: 800)
        chunk_overlap: Overlap tokens between chunks (default: 200)
        encoding_name: Tiktoken encoding to use

    Returns:
        List of Chunk objects with content and metadata
    """
    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except Exception:
        # Fallback to basic character-based chunking if tiktoken fails
        return _chunk_by_chars(text, chunk_size * 4, chunk_overlap * 4)

    # Encode text to tokens
    tokens = encoding.encode(text)

    chunks = []
    start_idx = 0

    while start_idx < len(tokens):
        # Get chunk of tokens
        end_idx = min(start_idx + chunk_size, len(tokens))
        chunk_tokens = tokens[start_idx:end_idx]

        # Decode back to text
        chunk_text = encoding.decode(chunk_tokens)

        # Skip empty or whitespace-only chunks
        if chunk_text.strip():
            chunks.append(Chunk(
                content=chunk_text,
                content_hash=compute_content_hash(chunk_text),
                start_idx=start_idx,
                end_idx=end_idx,
            ))

        # Move start position (with overlap)
        start_idx += chunk_size - chunk_overlap

        # Avoid infinite loop on last small chunk
        if end_idx == len(tokens):
            break

    return chunks


def _chunk_by_chars(text: str, chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """Fallback character-based chunking when tiktoken unavailable."""
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end]

        if chunk_text.strip():
            chunks.append(Chunk(
                content=chunk_text,
                content_hash=compute_content_hash(chunk_text),
                start_idx=start,
                end_idx=end,
            ))

        start += chunk_size - chunk_overlap

        if end == len(text):
            break

    return chunks


def deduplicate_chunks(chunks: list[Chunk]) -> list[Chunk]:
    """
    Remove duplicate chunks based on content hash.

    Args:
        chunks: List of chunks to deduplicate

    Returns:
        Deduplicated list of chunks (first occurrence kept)
    """
    seen_hashes = set()
    unique_chunks = []

    for chunk in chunks:
        if chunk.content_hash not in seen_hashes:
            seen_hashes.add(chunk.content_hash)
            unique_chunks.append(chunk)

    return unique_chunks
