"""
Tests para SessionMemory.
"""

import pytest
from datetime import datetime

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


class TestSessionMemory:
    """Tests para SessionMemory."""

    def test_add_message_to_new_session(self):
        """Debería agregar mensaje a una sesión nueva."""
        from api.agent.session_memory import SessionMemory

        memory = SessionMemory()

        memory.add("session-1", "user", "Hello")

        history = memory.get_history("session-1")

        assert len(history) == 1
        assert history[0].role == "user"
        assert history[0].content == "Hello"

    def test_window_size_limits_history(self):
        """Window size debería limitar la cantidad de mensajes."""
        from api.agent.session_memory import SessionMemory

        memory = SessionMemory(window_size=3)

        for i in range(5):
            memory.add("session-1", "user", f"Message {i}")

        history = memory.get_history("session-1")

        assert len(history) == 3
        assert history[0].content == "Message 2"  # Más antiguos eliminados
        assert history[2].content == "Message 4"

    def test_multiple_sessions_independent(self):
        """Múltiples sesiones deberían ser independientes."""
        from api.agent.session_memory import SessionMemory

        memory = SessionMemory()

        memory.add("session-1", "user", "Hello from session 1")
        memory.add("session-2", "user", "Hello from session 2")

        history1 = memory.get_history("session-1")
        history2 = memory.get_history("session-2")

        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0].content == "Hello from session 1"
        assert history2[0].content == "Hello from session 2"

    def test_get_history_nonexistent_session(self):
        """get_history de sesión inexistente debería retornar lista vacía."""
        from api.agent.session_memory import SessionMemory

        memory = SessionMemory()

        history = memory.get_history("nonexistent")

        assert history == []

    def test_clear_session(self):
        """Clear debería eliminar una sesión."""
        from api.agent.session_memory import SessionMemory

        memory = SessionMemory()

        memory.add("session-1", "user", "Hello")
        memory.clear("session-1")

        history = memory.get_history("session-1")

        assert history == []

    def test_messages_have_timestamps(self):
        """Mensajes deberían tener timestamps."""
        from api.agent.session_memory import SessionMemory

        memory = SessionMemory()

        memory.add("session-1", "user", "Hello")

        history = memory.get_history("session-1")

        assert history[0].timestamp is not None
        assert isinstance(history[0].timestamp, datetime)

    def test_different_roles(self):
        """Debería manejar diferentes roles."""
        from api.agent.session_memory import SessionMemory

        memory = SessionMemory()

        memory.add("session-1", "user", "Question")
        memory.add("session-1", "assistant", "Answer")

        history = memory.get_history("session-1")

        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"
