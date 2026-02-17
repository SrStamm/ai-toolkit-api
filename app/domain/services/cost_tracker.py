from typing import Dict
from uuid import UUID
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()


class CostTracker:
    def __init__(self, session_ttl_hours: int = 24):
        self.sessions: Dict[UUID, dict] = {}
        self.session_ttl = timedelta(hours=session_ttl_hours)

    def _cleanup_expired_sessions(self):
        """Remove sessions older than TTL"""
        now = datetime.now()
        expired = [
            sid
            for sid, data in self.sessions.items()
            if now - data["last_updated"] > self.session_ttl
        ]

        for sid in expired:
            del self.sessions[sid]

        if expired:
            logger.info("sessions_cleaned", count=len(expired))

    def create_session(self, session_id: UUID, tokens, cost) -> dict:
        # Cleanup before creating
        self._cleanup_expired_sessions()

        session = {
            "total_tokens": tokens,
            "total_cost": cost,
            "requests": 1,
            "last_updated": datetime.now(),
        }
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: UUID) -> dict:
        try:
            return self.sessions[session_id]
        except KeyError:
            raise ValueError(f"Session {session_id} not found")

    def add(self, session_id: UUID, tokens: int, cost: float) -> dict:
        if session_id not in self.sessions:
            return self.create_session(session_id, tokens, cost)

        session = self.get_session(session_id)
        session["total_tokens"] += tokens
        session["total_cost"] += cost
        session["requests"] += 1
        session["last_updated"] = datetime.now()

        return session

    def get_all_sessions(self) -> Dict[UUID, dict]:
        """Get all active sessions (for metrics endpoint)"""
        self._cleanup_expired_sessions()
        return self.sessions.copy()

    def clear_session(self, session_id: UUID) -> bool:
        """Manually clear a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False


cost_tracker = CostTracker()
