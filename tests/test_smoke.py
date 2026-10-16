"""Smoke tests for the FastAPI app: boot, health, and seeding of the bundled test definitions.

No LLM provider is called. Run with: pytest tests/test_smoke.py
"""

import os
import tempfile
from pathlib import Path

import pytest

# Settings are read at import time, so point the app at a throwaway database first.
_DB_DIR = tempfile.mkdtemp(prefix="llm-evals-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{Path(_DB_DIR) / 'test.db'}"
os.environ.setdefault("LOG_LEVEL", "WARNING")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from init_db import load_test_configurations  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_seed_loads_bundled_test_definitions(client):
    client.portal.call(load_test_configurations)

    categories = client.get("/api/tests/categories").json()
    assert {c["test_type"] for c in categories} == {
        "reasoning",
        "code_generation",
        "text_generation",
        "vision",
    }

    configs = client.get("/api/tests/configs").json()
    assert len(configs) == 12
