"""Tests for the application configuration."""

import os
import pytest
from unittest.mock import patch
from backend.app.config import Settings, get_settings


class TestSettings:
    """Test Settings model defaults and overrides."""

    def test_default_values(self):
        """Settings should have sensible defaults for all non-secret fields."""
        s = Settings(
            openai_api_key="test-openai",
            anthropic_api_key="test-anthropic",
            pinecone_api_key="test-pinecone",
        )
        assert s.pinecone_index == "legacylens"
        assert s.pinecone_cloud == "aws"
        assert s.pinecone_region == "us-east-1"
        assert s.embedding_model == "text-embedding-3-small"
        assert s.embedding_dimensions == 1536
        assert s.generation_model == "claude-sonnet-4-6"
        assert s.rerank_model == "claude-haiku-4-5-20251001"
        assert s.retrieval_top_k == 10
        assert s.chunk_batch_size == 100
        assert s.lapack_data_dir == "data/lapack"

    def test_reranker_defaults(self):
        """Reranker settings should default to enabled with reasonable top-k values."""
        s = Settings(
            openai_api_key="k",
            anthropic_api_key="k",
            pinecone_api_key="k",
        )
        assert s.use_reranker is True
        assert s.reranker_initial_top_k == 20
        assert s.reranker_final_top_k == 5

    def test_cors_origins_default(self):
        s = Settings(
            openai_api_key="k",
            anthropic_api_key="k",
            pinecone_api_key="k",
        )
        assert "http://localhost:5173" in s.cors_origins
        assert "http://localhost:3000" in s.cors_origins

    def test_env_override(self):
        """Settings can be overridden via environment variables."""
        with patch.dict(os.environ, {"PINECONE_INDEX": "custom-index"}):
            s = Settings(
                openai_api_key="k",
                anthropic_api_key="k",
                pinecone_api_key="k",
            )
            assert s.pinecone_index == "custom-index"

    def test_reranker_can_be_disabled(self):
        with patch.dict(os.environ, {"USE_RERANKER": "false"}):
            s = Settings(
                openai_api_key="k",
                anthropic_api_key="k",
                pinecone_api_key="k",
            )
            assert s.use_reranker is False
