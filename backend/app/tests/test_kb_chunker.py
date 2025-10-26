"""Unit tests for KB chunking and deduplication."""
import pytest
from app.kb.chunker import chunk_text, deduplicate_chunks, compute_content_hash, Chunk


class TestChunker:
    """Test text chunking functionality."""

    def test_chunk_text_basic(self):
        """Test basic text chunking."""
        text = "This is a test. " * 100  # Repeat to get multiple chunks
        chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)

        assert len(chunks) > 1
        assert all(isinstance(c, Chunk) for c in chunks)
        assert all(c.content.strip() for c in chunks)

    def test_chunk_text_empty(self):
        """Test chunking empty text."""
        chunks = chunk_text("", chunk_size=100, chunk_overlap=10)
        assert len(chunks) == 0

    def test_chunk_text_small(self):
        """Test chunking text smaller than chunk size."""
        text = "Small text"
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_compute_content_hash(self):
        """Test content hash generation."""
        text1 = "Hello, world!"
        text2 = "Hello, world!"
        text3 = "Different text"

        hash1 = compute_content_hash(text1)
        hash2 = compute_content_hash(text2)
        hash3 = compute_content_hash(text3)

        # Same content = same hash
        assert hash1 == hash2

        # Different content = different hash
        assert hash1 != hash3

        # Hash should be SHA256 (64 hex chars)
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)


class TestDeduplication:
    """Test chunk deduplication."""

    def test_deduplicate_chunks(self):
        """Test deduplication removes duplicate content."""
        # Create chunks with duplicate content
        chunk1 = Chunk(content="Hello world", content_hash=compute_content_hash("Hello world"), start_idx=0, end_idx=10)
        chunk2 = Chunk(content="Different text", content_hash=compute_content_hash("Different text"), start_idx=10, end_idx=20)
        chunk3 = Chunk(content="Hello world", content_hash=compute_content_hash("Hello world"), start_idx=20, end_idx=30)  # Duplicate

        chunks = [chunk1, chunk2, chunk3]
        deduped = deduplicate_chunks(chunks)

        # Should keep only unique chunks (first occurrence)
        assert len(deduped) == 2
        assert deduped[0].content == "Hello world"
        assert deduped[1].content == "Different text"

    def test_deduplicate_chunks_all_unique(self):
        """Test deduplication with no duplicates."""
        chunk1 = Chunk(content="First", content_hash=compute_content_hash("First"), start_idx=0, end_idx=5)
        chunk2 = Chunk(content="Second", content_hash=compute_content_hash("Second"), start_idx=5, end_idx=10)
        chunk3 = Chunk(content="Third", content_hash=compute_content_hash("Third"), start_idx=10, end_idx=15)

        chunks = [chunk1, chunk2, chunk3]
        deduped = deduplicate_chunks(chunks)

        # All chunks should remain
        assert len(deduped) == 3

    def test_deduplicate_chunks_empty(self):
        """Test deduplication with empty list."""
        deduped = deduplicate_chunks([])
        assert len(deduped) == 0

    def test_deduplicate_preserves_order(self):
        """Test that deduplication preserves order of first occurrences."""
        chunk1 = Chunk(content="A", content_hash=compute_content_hash("A"), start_idx=0, end_idx=1)
        chunk2 = Chunk(content="B", content_hash=compute_content_hash("B"), start_idx=1, end_idx=2)
        chunk3 = Chunk(content="A", content_hash=compute_content_hash("A"), start_idx=2, end_idx=3)
        chunk4 = Chunk(content="C", content_hash=compute_content_hash("C"), start_idx=3, end_idx=4)

        chunks = [chunk1, chunk2, chunk3, chunk4]
        deduped = deduplicate_chunks(chunks)

        assert len(deduped) == 3
        assert [c.content for c in deduped] == ["A", "B", "C"]


class TestChunkingIntegration:
    """Integration tests for chunking with deduplication."""

    def test_chunk_and_dedupe_workflow(self):
        """Test full chunking + deduplication workflow."""
        # Text with repeated sections (will create duplicate chunks)
        text = "Introduction section. " * 50 + "Body section. " * 50 + "Introduction section. " * 50

        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
        original_count = len(chunks)

        deduped = deduplicate_chunks(chunks)
        deduped_count = len(deduped)

        # Should have removed some duplicates
        assert deduped_count < original_count
        assert deduped_count > 0

        # All remaining chunks should be unique
        hashes = [c.content_hash for c in deduped]
        assert len(hashes) == len(set(hashes))
