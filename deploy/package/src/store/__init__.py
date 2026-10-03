"""Session storage: the engine's memory.

THE LESSON: the engine should not care WHERE sessions live. It talks to a
tiny interface — get(session_id), save(session) — and we plug in whichever
backend fits the environment:

  local dev / tests .... InMemorySessionStore (a dict, what we had)
  AWS (Lambda) ......... DynamoDBSessionStore (real database, survives restarts)

Same trick as the LLM client: code against the interface, swap the backend.
"""

from __future__ import annotations

from .memory import InMemorySessionStore

__all__ = ["SessionStore", "InMemorySessionStore"]


class SessionStore:
    """Interface. Both backends implement get() and save()."""

    def get(self, session_id: str):
        raise NotImplementedError

    def save(self, session) -> None:
        raise NotImplementedError


def make_store() -> SessionStore:
    """DynamoDB when a table name is configured, memory otherwise."""
    import os

    table = os.environ.get("HOTSEAT_SESSIONS_TABLE")
    if table:
        from .dynamodb import DynamoDBSessionStore

        return DynamoDBSessionStore(table)
    return InMemorySessionStore()
