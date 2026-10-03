"""In-memory session store — local dev and tests."""

from __future__ import annotations

from ..models.session import Session


class InMemorySessionStore:
    """A dict. Fast, free, and forgets everything on restart."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def save(self, session: Session) -> None:
        self._sessions[session.session_id] = session
