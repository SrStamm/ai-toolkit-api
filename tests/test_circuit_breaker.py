"""
Tests para el circuit breaker del LLMRouter.
"""

import pytest
from unittest.mock import MagicMock, patch

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


class TestCircuitBreaker:
    """Tests para el circuit breaker."""

    def test_initial_state_is_closed(self):
        """Circuit breaker debería empezar en estado CLOSED."""
        from domain.services.router import LLMRouter

        primary = MagicMock()
        primary.name = "primary"
        primary.model = "primary-model"
        primary.chat.return_value = MagicMock()

        fallback = MagicMock()
        fallback.name = "fallback"
        fallback.model = "fallback-model"
        fallback.chat.return_value = MagicMock()

        router = LLMRouter(primary=primary, fallback=fallback)

        assert router.state == "CLOSED"
        assert router.failure_count == 0

    def test_opens_after_threshold_failures(self):
        """Circuit breaker debería abrirse después de threshold fallos."""
        from domain.services.router import LLMRouter

        primary = MagicMock()
        primary.name = "primary"
        primary.model = "primary-model"
        primary.chat.side_effect = Exception("Connection error")

        fallback = MagicMock()
        fallback.name = "fallback"
        fallback.model = "fallback-model"
        fallback.chat.return_value = MagicMock()

        router = LLMRouter(primary=primary, fallback=fallback, failure_threshold=3)

        # Hacer 3 requests que fallen
        for _ in range(3):
            router.chat("test prompt")

        assert router.state == "OPEN"
        assert router.failure_count == 3

    def test_fallback_used_when_open(self):
        """Cuando el circuit breaker está abierto, usar fallback."""
        from domain.services.router import LLMRouter

        primary = MagicMock()
        primary.name = "primary"
        primary.model = "primary-model"
        primary.chat.side_effect = Exception("Connection error")

        fallback = MagicMock()
        fallback.name = "fallback"
        fallback.model = "fallback-model"
        fallback.chat.return_value = MagicMock(content="fallback response")

        router = LLMRouter(primary=primary, fallback=fallback, failure_threshold=1)

        # Trigger threshold
        router.chat("test")

        # Ahora debería usar fallback
        router.chat("another test")

        # Verificar que fallback fue llamado
        assert fallback.chat.called

    def test_success_after_half_open_resets_circuit(self):
        """Después de HALF-OPEN, éxito cierra el circuito."""
        import time
        from domain.services.router import LLMRouter

        primary = MagicMock()
        primary.name = "primary"
        primary.model = "primary-model"
        primary.chat.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Exception("Error 3"),  # Opens circuit
            MagicMock(),  # Success after HALF-OPEN
        ]

        fallback = MagicMock()
        fallback.name = "fallback"
        fallback.model = "fallback-model"
        fallback.chat.return_value = MagicMock()

        router = LLMRouter(primary=primary, fallback=fallback, failure_threshold=3)

        # Trigger 3 failures (opens circuit)
        router.chat("test 1")
        router.chat("test 2")
        router.chat("test 3")

        assert router.state == "OPEN"
        assert router.failure_count == 3

        # Simulate timeout passing by setting opened_at to past
        router.opened_at = time.time() - router.open_timeout - 1

        # Next call should transition to HALF-OPEN and succeed
        router.chat("test 4")

        assert router.state == "CLOSED"
        assert router.failure_count == 0
