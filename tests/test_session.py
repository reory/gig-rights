from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from gig_rights.db.session import Base, SessionLocal, engine, get_db


class TestDbSession:
    """Unit tests for database session management and dependency injection."""

    def test_engine_and_session_factory_initialized(self):
        """Verifies engine binding and SessionLocal instantiation."""

        assert engine is not None
        assert SessionLocal is not None

        # Verify Base ORM declarative metadata exists
        assert hasattr(Base, "metadata")

    @patch("gig_rights.db.session.SessionLocal")
    def test_get_db_yields_session_and_closes_normally(self, mock_session_factory):
        """get_db yields a database session and ensures session.close() on completion."""

        mock_session = MagicMock(spec=Session)
        mock_session_factory.return_value = mock_session

        gen = get_db()
        db = next(gen)

        assert db == mock_session
        mock_session.close.assert_not_called()

        # Advance generator to trigger cleanup
        with pytest.raises(StopIteration):
            next(gen)

        mock_session.close.assert_called_once()

    @patch("gig_rights.db.session.SessionLocal")
    def test_get_db_closes_session_on_exception(self, mock_session_factory):
        """
        get_db guarantees session.close() is called even if
        an unhandled exception occurs.
        """

        mock_session = MagicMock(spec=Session)
        mock_session_factory.return_value = mock_session

        gen = get_db()
        db = next(gen)

        assert db == mock_session
        mock_session.close.assert_not_called()

        # Simulate FastAPI or business logic raising an exception during request execution
        with pytest.raises(RuntimeError, match="Database query failed"):
            gen.throw(RuntimeError("Database query failed"))

        mock_session.close.assert_called_once()

    def test_real_session_local_lifecycle(self):
        """
        Integration test using the real SessionLocal to
        confirm database session creation.
        """

        session = SessionLocal()
        try:
            assert isinstance(session, Session)
        finally:
            session.close()
