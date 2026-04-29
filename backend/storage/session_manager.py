"""
Session manager for storing user session state in memory.
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Optional
from uuid import uuid4

from .file_manager import FileManager
from ..config import get_settings
from ..models.session import SessionModel, DatasetMetadata
from ..utils.error_handler import SessionExpiredError, SessionNotFoundError

settings = get_settings()


class SessionManager:
    """In-memory session storage for the chatbot."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionModel] = {}
        self._lock = Lock()

    def create_session(self) -> SessionModel:
        session_id = f"sess_{uuid4().hex}"
        now = datetime.utcnow()
        session = SessionModel(
            session_id=session_id,
            created_at=now,
            last_accessed_at=now,
            dataset=None,
            chat_history=[],
            metadata={},
        )
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> SessionModel:
        with self._lock:
            session = self._sessions.get(session_id)

        if not session:
            raise SessionNotFoundError(session_id)

        if self._is_expired(session):
            with self._lock:
                self._sessions.pop(session_id, None)
            raise SessionExpiredError(session_id)

        session.last_accessed_at = datetime.utcnow()
        return session

    def save_session(self, session: SessionModel) -> None:
        session.last_accessed_at = datetime.utcnow()
        with self._lock:
            self._sessions[session.session_id] = session

    def delete_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def cleanup_expired_sessions(self) -> int:
        now = datetime.utcnow()
        expired_ids = []

        with self._lock:
            for session_id, session in self._sessions.items():
                if now - session.last_accessed_at > timedelta(hours=settings.SESSION_TIMEOUT_HOURS):
                    expired_ids.append(session_id)
            for session_id in expired_ids:
                self._sessions.pop(session_id, None)

        return len(expired_ids)

    def _is_expired(self, session: SessionModel) -> bool:
        return datetime.utcnow() - session.last_accessed_at > timedelta(
            hours=settings.SESSION_TIMEOUT_HOURS
        )


session_manager = SessionManager()
