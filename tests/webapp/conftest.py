"""Webapp test fixtures -- FastAPI TestClient and DB seeding."""

import pytest
from fastapi.testclient import TestClient

from webapp.app import app


@pytest.fixture
def client():
    """FastAPI test client backed by the in-memory DB from _fresh_db."""
    return TestClient(app)
