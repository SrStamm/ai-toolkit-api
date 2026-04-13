"""
Tests para SessionMemory con Redis.

Uses fakeredis for testing without a real Redis connection.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

# Try to import fakeredis, skip if not available
try:
    import fakeredis

    HAS_FAKEREDIS = True
except ImportError:
    HAS_FAKEREDIS = False


@pytest.fixture
def mock_redis():
    """Create a fake Redis client for testing."""
    if not HAS_FAKEREDIS:
        pytest.skip("fakeredis not installed")
    return fakeredis.FakeRedis(decode_responses=False)


@pytest.fixture
def session_memory(mock_redis):
    """Create a RedisSessionMemory with mocked Redis."""
    from api.agent.session_memory import RedisSessionMemory, set_session_memory

    memory = RedisSessionMemory(window_size=5, ttl_seconds=3600)
    memory._redis = mock_redis

    # Set as singleton for tests
    set_session_memory(memory)

    yield memory

    # Cleanup
    set_session_memory(None)


class TestRedisSessionMemory:
    """Tests para RedisSessionMemory."""

    def test_add_message_to_new_session(self, session_memory, mock_redis):
        """Debería agregar mensaje a una sesión nueva."""
        session_memory.add("session-1", "user", "Hello")

        history = session_memory.get_history("session-1")

        assert len(history) == 1
        assert history[0].role == "user"
        assert history[0].content == "Hello"

    def test_window_size_limits_history(self, session_memory, mock_redis):
        """Window size debería limitar la cantidad de mensajes."""
        # session_memory has window_size=5 from fixture

        for i in range(8):
            session_memory.add("session-1", "user", f"Message {i}")

        history = session_memory.get_history("session-1")

        # Should only have 5 most recent
        assert len(history) == 5
        assert history[0].content == "Message 3"  # Older ones removed
        assert history[4].content == "Message 7"

    def test_multiple_sessions_independent(self, session_memory, mock_redis):
        """Múltiples sesiones deberían ser independientes."""
        session_memory.add("session-1", "user", "Hello from session 1")
        session_memory.add("session-2", "user", "Hello from session 2")

        history1 = session_memory.get_history("session-1")
        history2 = session_memory.get_history("session-2")

        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0].content == "Hello from session 1"
        assert history2[0].content == "Hello from session 2"

    def test_get_history_nonexistent_session(self, session_memory, mock_redis):
        """get_history de sesión inexistente debería retornar lista vacía."""
        history = session_memory.get_history("nonexistent")

        assert history == []

    def test_clear_session(self, session_memory, mock_redis):
        """Clear debería eliminar una sesión."""
        session_memory.add("session-1", "user", "Hello")
        session_memory.clear("session-1")

        history = session_memory.get_history("session-1")

        assert history == []

    def test_messages_have_timestamps(self, session_memory, mock_redis):
        """Mensajes deberían tener timestamps."""
        session_memory.add("session-1", "user", "Hello")

        history = session_memory.get_history("session-1")

        assert history[0].timestamp is not None
        assert isinstance(history[0].timestamp, datetime)

    def test_different_roles(self, session_memory, mock_redis):
        """Debería manejar diferentes roles."""
        session_memory.add("session-1", "user", "Question")
        session_memory.add("session-1", "assistant", "Answer")

        history = session_memory.get_history("session-1")

        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"

    def test_messages_in_chronological_order(self, session_memory, mock_redis):
        """Mensajes deberían estar en orden cronológico (oldest first)."""
        import time

        session_memory.add("session-1", "user", "First")
        time.sleep(0.01)  # Small delay to ensure different timestamps
        session_memory.add("session-1", "assistant", "Second")
        time.sleep(0.01)
        session_memory.add("session-1", "user", "Third")

        history = session_memory.get_history("session-1")

        assert history[0].content == "First"
        assert history[1].content == "Second"
        assert history[2].content == "Third"

    def test_exists_returns_true_for_existing_session(self, session_memory, mock_redis):
        """exists() debería retornar True para sesiones existentes."""
        session_memory.add("session-1", "user", "Hello")

        assert session_memory.exists("session-1") is True

    def test_exists_returns_false_for_nonexistent_session(
        self, session_memory, mock_redis
    ):
        """exists() debería retornar False para sesiones inexistentes."""
        assert session_memory.exists("nonexistent") is False

    def test_ttl_is_set_on_add(self, session_memory, mock_redis):
        """TTL debería configurarse al agregar un mensaje."""
        session_memory.add("session-1", "user", "Hello")

        ttl = session_memory.get_ttl("session-1")

        # TTL should be positive and <= configured value
        assert ttl > 0
        assert ttl <= 3600

    def test_message_serialization_roundtrip(self, session_memory, mock_redis):
        """Mensajes deberían serializarse/deserializarse correctamente."""
        original_content = "Test content with special chars: áéíóú ñ"
        session_memory.add("session-1", "user", original_content)

        history = session_memory.get_history("session-1")

        assert len(history) == 1
        assert history[0].content == original_content
        assert history[0].role == "user"

    def test_clear_nonexistent_session_does_not_error(self, session_memory, mock_redis):
        """Clear de sesión inexistente no debería lanzar error."""
        # Should not raise
        session_memory.clear("nonexistent")


class TestMessageDataclass:
    """Tests para Message dataclass."""

    def test_to_dict(self):
        """Debería convertir a dict correctamente."""
        from api.agent.session_memory import Message

        msg = Message(
            role="user", content="Hello", timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        data = msg.to_dict()

        assert data["role"] == "user"
        assert data["content"] == "Hello"
        assert data["timestamp"] == "2024-01-01T12:00:00"

    def test_from_dict(self):
        """Debería crear Message desde dict correctamente."""
        from api.agent.session_memory import Message

        data = {
            "role": "assistant",
            "content": "Hello!",
            "timestamp": "2024-01-01T12:00:00",
        }
        msg = Message.from_dict(data)

        assert msg.role == "assistant"
        assert msg.content == "Hello!"
        assert msg.timestamp == datetime(2024, 1, 1, 12, 0, 0)
