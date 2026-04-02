"""
Tests para LLMClient generate_structured_output.
"""

import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


class TestStructuredOutput:
    """Tests para generate_structured_output."""

    def test_successful_parsing(self):
        """Debería parsear respuesta JSON correctamente."""
        from application.llm.client import LLMClient
        from domain.services.router import LLMRouter
        from domain.models import LLMResponse, TokenUsage, CostBreakdown

        # Mock router
        mock_router = MagicMock()
        mock_router.chat.return_value = LLMResponse(
            content='{"answer": "Test response"}',
            usage=TokenUsage(10, 5, 15),
            cost=CostBreakdown(0.001, 0.002, 0.003),
            model="test",
            provider="test",
        )

        client = LLMClient(router=mock_router)

        class TestSchema(BaseModel):
            answer: str

        result = client.generate_structured_output("test prompt", TestSchema)

        assert result.content.answer == "Test response"

    def test_retry_on_invalid_json(self):
        """Debería hacer retry cuando el JSON es inválido."""
        from application.llm.client import LLMClient
        from domain.models import LLMResponse, TokenUsage, CostBreakdown

        # Mock router - primero inválido, después válido
        mock_router = MagicMock()
        mock_router.chat.side_effect = [
            LLMResponse(
                content="invalid json",
                usage=TokenUsage(10, 5, 15),
                cost=CostBreakdown(0.001, 0.002, 0.003),
                model="test",
                provider="test",
            ),
            LLMResponse(
                content='{"answer": "Fixed response"}',
                usage=TokenUsage(10, 5, 15),
                cost=CostBreakdown(0.001, 0.002, 0.003),
                model="test",
                provider="test",
            ),
        ]

        client = LLMClient(router=mock_router)

        class TestSchema(BaseModel):
            answer: str

        result = client.generate_structured_output("test prompt", TestSchema)

        assert result.content.answer == "Fixed response"
        assert mock_router.chat.call_count == 2

    def test_max_retries_exceeded_raises(self):
        """Debería lanzar excepción después de max retries."""
        from application.llm.client import LLMClient, MAX_STRUCTURED_OUTPUT_RETRIES
        from app.domain.exceptions import StructuredOutputError
        from app.domain.models import LLMResponse, TokenUsage, CostBreakdown

        # Mock router - siempre devuelve JSON inválido
        mock_router = MagicMock()
        mock_router.chat.return_value = LLMResponse(
            content="still invalid",
            usage=TokenUsage(10, 5, 15),
            cost=CostBreakdown(0.001, 0.002, 0.003),
            model="test",
            provider="test",
        )

        client = LLMClient(router=mock_router)

        class TestSchema(BaseModel):
            answer: str

        with pytest.raises(StructuredOutputError) as exc_info:
            client.generate_structured_output("test prompt", TestSchema)

        assert "Failed to parse structured output" in str(exc_info.value)
        # Con MAX_STRUCTURED_OUTPUT_RETRIES = 2:
        # - Intento 1: _retries=0, falla, llama con _retries=1
        # - Intento 2: _retries=1, falla, llama con _retries=2
        # - Intento 3: _retries=2 >= MAX_RETRIES, lanza excepción
        # Total: 2 llamadas al router (no 3 porque la verificación de límite ocurre antes de la llamada)
        assert mock_router.chat.call_count == MAX_STRUCTURED_OUTPUT_RETRIES
