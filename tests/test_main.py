from unittest.mock import patch

import pytest  # noqa
from fastapi.testclient import TestClient

from gig_rights.main import app


class TestMainApp:
    """Unit and integration tests for the main FastAPI application entrypoint."""

    def test_app_metadata_configured(self):
        """Verifies OpenAPI metadata and title configurations."""

        assert app.title == "GigRights API"
        assert app.version == "1.0.0"

    def test_health_check_endpoint(self):
        """GET /health returns HTTP 200 and the standard health status payload."""

        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok", "service": "GigRights API"}

    @patch("gig_rights.main.Base.metadata.create_all")
    def test_lifespan_creates_db_tables(self, mock_create_all):
        """
        Verifies that app startup triggers
        SQLAlchemy table creation via lifespan context manager.
        """

        with TestClient(app):
            mock_create_all.assert_called_once()
