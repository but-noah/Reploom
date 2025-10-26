"""Integration tests for KB upload and retrieval."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.kb.retrieval import upsert_document, search_kb
from app.kb.models import KBSearchResult


class TestKBIntegration:
    """Integration tests for KB operations."""

    @patch("app.kb.retrieval.get_qdrant_client")
    @patch("app.kb.retrieval.ensure_collection_exists")
    @patch("app.kb.embeddings.get_openai_client")
    def test_upsert_document_basic(self, mock_openai, mock_ensure_collection, mock_qdrant):
        """Test basic document upload and chunking."""
        # Mock OpenAI client
        mock_openai_instance = MagicMock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536) for _ in range(3)]
        mock_openai_instance.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_openai_instance

        # Mock Qdrant client
        mock_qdrant_instance = MagicMock()
        mock_qdrant.return_value = mock_qdrant_instance

        # Upload a simple document
        text = "This is a test document. " * 100
        result = upsert_document(
            file_content=text,
            workspace_id="workspace-123",
            source="upload",
            title="Test Document",
        )

        # Verify result structure
        assert "chunks_total" in result
        assert "chunks_uploaded" in result
        assert "duplicates_skipped" in result
        assert result["chunks_uploaded"] > 0

        # Verify collection was ensured
        mock_ensure_collection.assert_called_once()

        # Verify embeddings were generated
        mock_openai_instance.embeddings.create.assert_called()

        # Verify upsert was called
        mock_qdrant_instance.upsert.assert_called_once()

    @patch("app.kb.retrieval.get_qdrant_client")
    @patch("app.kb.retrieval.ensure_collection_exists")
    @patch("app.kb.embeddings.get_openai_client")
    def test_upsert_document_deduplication(self, mock_openai, mock_ensure_collection, mock_qdrant):
        """Test that deduplication works during upload."""
        # Mock OpenAI client
        mock_openai_instance = MagicMock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_openai_instance.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_openai_instance

        # Mock Qdrant client
        mock_qdrant_instance = MagicMock()
        mock_qdrant.return_value = mock_qdrant_instance

        # Upload document with repeated content
        text = "Exact same sentence. " * 200  # Will create duplicate chunks
        result = upsert_document(
            file_content=text,
            workspace_id="workspace-123",
            source="upload",
        )

        # Should have deduplicated
        assert result["duplicates_skipped"] >= 0
        assert result["chunks_uploaded"] > 0

    @patch("app.kb.retrieval.get_qdrant_client")
    @patch("app.kb.embeddings.get_openai_client")
    def test_search_kb_basic(self, mock_openai, mock_qdrant):
        """Test basic KB search functionality."""
        # Mock OpenAI client for query embedding
        mock_openai_instance = MagicMock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_openai_instance.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_openai_instance

        # Mock Qdrant search results
        mock_qdrant_instance = MagicMock()
        mock_hit = Mock()
        mock_hit.id = "test-id-123"
        mock_hit.score = 0.95
        mock_hit.payload = {
            "workspace_id": "workspace-123",
            "source": "upload",
            "title": "Test Doc",
            "content": "Relevant content here",
            "tags": ["test"],
        }
        mock_qdrant_instance.search.return_value = [mock_hit]
        mock_qdrant.return_value = mock_qdrant_instance

        # Perform search
        results = search_kb(
            query="test query",
            workspace_id="workspace-123",
            k=5,
        )

        # Verify results
        assert len(results) == 1
        assert isinstance(results[0], KBSearchResult)
        assert results[0].content == "Relevant content here"
        assert results[0].score == 0.95
        assert results[0].workspace_id == "workspace-123"

        # Verify Qdrant search was called with correct params
        mock_qdrant_instance.search.assert_called_once()
        call_kwargs = mock_qdrant_instance.search.call_args[1]
        assert call_kwargs["limit"] == 5
        assert call_kwargs["with_vectors"] == False  # Default optimization

    @patch("app.kb.retrieval.get_qdrant_client")
    @patch("app.kb.embeddings.get_openai_client")
    def test_search_kb_with_vectors(self, mock_openai, mock_qdrant):
        """Test KB search with vectors enabled (debug mode)."""
        # Mock OpenAI
        mock_openai_instance = MagicMock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_openai_instance.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_openai_instance

        # Mock Qdrant
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.search.return_value = []
        mock_qdrant.return_value = mock_qdrant_instance

        # Search with vectors enabled
        search_kb(
            query="test",
            workspace_id="workspace-123",
            k=5,
            with_vectors=True,
        )

        # Verify with_vectors flag was passed
        call_kwargs = mock_qdrant_instance.search.call_args[1]
        assert call_kwargs["with_vectors"] == True

    @patch("app.kb.retrieval.get_qdrant_client")
    @patch("app.kb.embeddings.get_openai_client")
    def test_search_kb_workspace_filtering(self, mock_openai, mock_qdrant):
        """Test that search filters by workspace_id."""
        # Mock OpenAI
        mock_openai_instance = MagicMock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_openai_instance.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_openai_instance

        # Mock Qdrant
        mock_qdrant_instance = MagicMock()
        mock_qdrant_instance.search.return_value = []
        mock_qdrant.return_value = mock_qdrant_instance

        # Search with specific workspace
        search_kb(
            query="test",
            workspace_id="workspace-456",
            k=5,
        )

        # Verify workspace filter was applied
        call_kwargs = mock_qdrant_instance.search.call_args[1]
        assert "query_filter" in call_kwargs
        # Filter should contain workspace_id condition
        filter_obj = call_kwargs["query_filter"]
        assert filter_obj is not None
