"""
Session memory with Redis persistence.

Replaces in-memory session storage with Redis-backed storage.
This enables:
- Session persistence across API restarts
- Horizontal scaling (multiple workers share same sessions)
- Configurable TTL for automatic session expiration
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import TypedDict

import structlog

from app.core.redis import get_redis


log = structlog.get_logger()


class MessageDict(TypedDict):
    """Dict representation of Message for JSON serialization."""

    role: str
    content: str
    timestamp: str


@dataclass
class Message:
    """A single message in a conversation session."""

    role: str
    content: str
    timestamp: datetime

    def to_dict(self) -> MessageDict:
        """Convert to dict for JSON serialization."""
        return MessageDict(
            role=self.role,
            content=self.content,
            timestamp=self.timestamp.isoformat(),
        )

    @classmethod
    def from_dict(cls, data: MessageDict) -> "Message":
        """Create Message from dict."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class RedisSessionMemory:
    """
    Redis-backed session memory with sliding window.

    Uses Redis lists with LPUSH/LTRIM for efficient window management.
    Keys follow pattern: session:{session_id}
    """

    # Default settings
    DEFAULT_WINDOW_SIZE = 10
    DEFAULT_TTL_SECONDS = 86400  # 24 hours

    def __init__(
        self,
        window_size: int = DEFAULT_WINDOW_SIZE,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self.window_size = window_size
        self.ttl_seconds = ttl_seconds
        self._redis = get_redis()

    def _key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"session:{session_id}"

    def add(self, session_id: str, role: str, content: str) -> None:
        """Add a message to the session history."""
        key = self._key(session_id)

        message = Message(role=role, content=content, timestamp=datetime.now())
        message_json = json.dumps(message.to_dict())

        # Push to the left (most recent first)
        self._redis.lpush(key, message_json)

        # Trim to window size
        self._redis.ltrim(key, 0, self.window_size - 1)

        # Refresh TTL
        self._redis.expire(key, self.ttl_seconds)

        log.debug(
            "session_message_added",
            session_id=session_id,
            role=role,
            window_size=self.window_size,
        )

    def get_history(self, session_id: str) -> list[Message]:
        """Get conversation history for a session."""
        key = self._key(session_id)

        # Get all messages in the list
        raw_messages = self._redis.lrange(key, 0, -1)

        if not raw_messages:
            return []

        messages = []
        for raw in raw_messages:
            try:
                data = json.loads(raw)
                messages.append(Message.from_dict(data))
            except (json.JSONDecodeError, KeyError) as e:
                log.warning(
                    "invalid_message_in_session",
                    session_id=session_id,
                    error=str(e),
                )
                continue

        # Return in chronological order (oldest first)
        return list(reversed(messages))

    def clear(self, session_id: str) -> None:
        """Delete a session and its history."""
        key = self._key(session_id)
        self._redis.delete(key)
        log.debug("session_cleared", session_id=session_id)

    def exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return self._redis.exists(self._key(session_id)) > 0

    def get_ttl(self, session_id: str) -> int:
        """Get remaining TTL for a session in seconds. Returns -2 if key doesn't exist."""
        return self._redis.ttl(self._key(session_id))


# Module-level singleton
_session_memory: RedisSessionMemory | None = None


def get_session_memory() -> RedisSessionMemory:
    """Get or create the session memory singleton."""
    global _session_memory
    if _session_memory is None:
        _session_memory = RedisSessionMemory()
    return _session_memory


# Backwards compatibility: allow injection of custom memory implementation
def set_session_memory(memory: RedisSessionMemory) -> None:
    """Set a custom session memory instance (for testing)."""
    global _session_memory
    _session_memory = memory


# Alias for the type used by Agent
SessionMemory = RedisSessionMemory
