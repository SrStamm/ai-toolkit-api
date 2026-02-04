from typing import Dict
from uuid import UUID
from datetime import datetime


class CostTracker:
    def __init__(self):
        self.sessions: Dict[UUID, dict] = {}

    def create_session(self, session_id: UUID, tokens, cost) -> dict:
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
            raise ValueError("Session ID not found")

    def add(self, session_id: UUID, tokens: int, cost: float) -> dict:
        if session_id not in self.sessions:
            return self.create_session(session_id, tokens, cost)

        session = self.get_session(session_id)
        session["total_tokens"] += tokens
        session["total_cost"] += cost
        session["requests"] += 1
        session["last_updated"] = datetime.now()

        return session


cost_tracker = CostTracker()
