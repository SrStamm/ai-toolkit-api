from dataclasses import dataclass
from datetime import datetime

@dataclass
class Message:
    role: str 
    content: str 
    timestamp: datetime

# Clase para manejar la memoria de la sesión
class SessionMemory:
    def __init__(self, window_size: int = 10) -> None:
        self.sessions: dict[str, list[Message]] = {}
        self.window_size = window_size

    def add(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        self.sessions[session_id].append(Message(role, content, datetime.now()))

        if len(self.sessions[session_id]) > self.window_size:
            self.sessions[session_id].pop(0)

    def get_history(self, session_id: str) -> list[Message]:
        return self.sessions.get(session_id, [])

    def clear(self, session_id: str):
        self.sessions.pop(session_id, None)

# Singleton
_session_memory = SessionMemory()

def get_session_memory() -> SessionMemory:
    return _session_memory
