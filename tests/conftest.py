"""
Test configuration and fixtures.
"""

import os
import tempfile

import pytest
from unittest.mock import MagicMock

# Setup prometheus multiprocess environment before any imports
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", tempfile.mkdtemp())


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    provider.name = "mock"
    provider.model = "mock-model"
    return provider


@pytest.fixture
def mock_rag_orchestrator():
    """Create a mock RAG orchestrator."""
    orchestrator = MagicMock()
    orchestrator.custom_query.return_value = MagicMock(
        answer="Test answer", citations=[], metadata=MagicMock()
    )
    return orchestrator


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.generate_content.return_value = MagicMock(
        content='{"answer": "Test response"}',
        usage=MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        cost=MagicMock(input_cost=0.001, output_cost=0.002, total_cost=0.003),
        model="test-model",
        provider="test",
    )
    return client
