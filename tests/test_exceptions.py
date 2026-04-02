"""
Tests para las excepciones del dominio.
"""

import pytest

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


class TestExceptions:
    """Tests para el sistema de excepciones."""

    def test_llm_error_is_base(self):
        """LLMError debería ser la clase base."""
        from domain.exceptions import LLMError, RetryableError, PermanentError

        assert issubclass(RetryableError, LLMError)
        assert issubclass(PermanentError, LLMError)

    def test_retryable_errors(self):
        """Retryable errors deberían heredar de RetryableError."""
        from domain.exceptions import (
            RetryableError,
            NetworkTimeoutError,
            LLMConnectionError,
            RateLimitError,
        )

        assert issubclass(NetworkTimeoutError, RetryableError)
        assert issubclass(LLMConnectionError, RetryableError)
        assert issubclass(RateLimitError, RetryableError)

    def test_permanent_errors(self):
        """Permanent errors deberían heredar de PermanentError."""
        from domain.exceptions import (
            PermanentError,
            InvalidAPIKeyError,
            ModelNotFoundError,
            ContextLengthExceededError,
        )

        assert issubclass(InvalidAPIKeyError, PermanentError)
        assert issubclass(ModelNotFoundError, PermanentError)
        assert issubclass(ContextLengthExceededError, PermanentError)

    def test_vector_store_errors(self):
        """Vector store errors deberían tener su jerarquía."""
        from domain.exceptions import (
            VectorStoreError,
            CollectionNotFoundError,
            EmbeddingError,
        )

        assert issubclass(CollectionNotFoundError, VectorStoreError)
        assert issubclass(EmbeddingError, VectorStoreError)

    def test_tool_errors(self):
        """Tool errors deberían tener su jerarquía."""
        from domain.exceptions import (
            ToolError,
            ToolNotFoundError,
            ToolExecutionError,
        )

        assert issubclass(ToolNotFoundError, ToolError)
        assert issubclass(ToolExecutionError, ToolError)

    def test_can_catch_by_category(self):
        """Debería poder capturar errores por categoría."""
        from domain.exceptions import (
            LLMError,
            RetryableError,
            PermanentError,
            NetworkTimeoutError,
        )

        # Capturar por LLMError
        try:
            raise PermanentError("API key inválida")
        except LLMError as e:
            assert isinstance(e, PermanentError)

        # Capturar por RetryableError
        try:
            raise NetworkTimeoutError("Timeout")
        except RetryableError as e:
            assert isinstance(e, NetworkTimeoutError)
