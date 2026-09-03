from app.models import SearchSession


class SessionStore:
    """Small in-memory store for each chat's current search flow."""

    def __init__(self) -> None:
        self._sessions: dict[int, SearchSession] = {}

    def start(self, chat_id: int, query: str) -> SearchSession:
        session = SearchSession(query=query)
        self._sessions[chat_id] = session
        return session

    def get(self, chat_id: int) -> SearchSession | None:
        return self._sessions.get(chat_id)

    def delete(self, chat_id: int) -> None:
        self._sessions.pop(chat_id, None)
