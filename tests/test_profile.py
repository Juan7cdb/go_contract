"""Tests for `/auth/me` preferences exposure and `/profile/` preferences merge.

These tests avoid hitting a real database by overriding the FastAPI
`get_db` and `get_current_user` dependencies. The fake `User` instance
acts as the in-memory store: `PUT /profile/` mutates its attributes
directly, and the next `GET /auth/me` (against the same fake user)
reads those mutations back.

Pattern mirrors `tests/test_billing.py` (FakeAsyncSession + dependency
overrides + TestClient). See Phase 1 of
`thoughts/shared/plans/2026-06-08-fix-settings-persistence.md`.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models import User
from tests.conftest import FakeAsyncSession


# --------------------------------------------------------------------------- #
# Fixtures                                                                    #
# --------------------------------------------------------------------------- #


@pytest.fixture
def fake_session() -> FakeAsyncSession:
    return FakeAsyncSession()


@pytest.fixture
def fake_user() -> User:
    """Fresh User per test with seeded preferences."""
    return User(
        id=42,
        email="u@example.com",
        hashed_password="x",
        first_name="Juan",
        last_name="Doe",
        credits_remaining=5,
        preferences={"language": "en", "autoSave": True},
    )


@pytest.fixture
def client(fake_session: FakeAsyncSession, fake_user: User):
    """TestClient with `get_db` and `get_current_user` overridden."""

    async def _override_get_db():
        yield fake_session

    async def _override_get_current_user():
        return fake_user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #


def test_get_me_returns_preferences(client: TestClient, fake_user: User):
    """`GET /api/v1/auth/me` must include `preferences` in the response body.

    `/auth/me` now serializes through `AuthMeResponse` with
    `response_model_exclude_none=True` + `response_model_by_alias=True`, so
    unset typed fields are dropped and the seeded camelCase keys survive
    untouched. The result happens to be an exact match against the seed.
    """
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert "preferences" in body
    # exclude_none + by_alias collapse the typed shape back to the seed.
    assert body["preferences"] == {"language": "en", "autoSave": True}


def test_update_profile_partial_preferences_merges(
    client: TestClient, fake_user: User
):
    """PUT with one key preserves other existing keys (shallow merge)."""
    # Seed already includes language=en, autoSave=True.
    resp = client.put(
        "/api/v1/profile/",
        json={"preferences": {"language": "es"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    # ProfileResponse uses `response_model_exclude_none=True`, so only
    # the keys actually set appear in the wire body — assert key-by-key.
    assert body["preferences"]["language"] == "es"
    # autoSave must be preserved from the seed.
    assert body["preferences"]["autoSave"] is True

    # The underlying dict on the user model holds only the merged keys.
    assert fake_user.preferences == {"language": "es", "autoSave": True}

    # Reload via /auth/me — same fake user — verifies the in-memory mutation
    # is what subsequent requests see (proxy for "persisted").
    me = client.get("/api/v1/auth/me")
    assert me.json()["preferences"] == {"language": "es", "autoSave": True}


def test_update_profile_full_preferences_persists_all(
    client: TestClient, fake_user: User
):
    """PUT with all five typed fields persists them and exposes via /auth/me."""
    payload = {
        "preferences": {
            "language": "pt-BR",
            "timezone": "EST",
            "autoSave": False,
            "aiSuggestions": True,
            "twoFactor": False,
        }
    }
    resp = client.put("/api/v1/profile/", json=payload)
    assert resp.status_code == 200
    prefs = resp.json()["preferences"]
    assert prefs["language"] == "pt-BR"
    assert prefs["timezone"] == "EST"
    assert prefs["autoSave"] is False
    assert prefs["aiSuggestions"] is True
    assert prefs["twoFactor"] is False

    me = client.get("/api/v1/auth/me")
    me_prefs = me.json()["preferences"]
    assert me_prefs["language"] == "pt-BR"
    assert me_prefs["timezone"] == "EST"
    assert me_prefs["autoSave"] is False
    assert me_prefs["aiSuggestions"] is True
    assert me_prefs["twoFactor"] is False


def test_update_profile_empty_preferences_noop(
    client: TestClient, fake_user: User
):
    """PUT with `preferences: {}` does not raise and preserves existing keys."""
    resp = client.put("/api/v1/profile/", json={"preferences": {}})
    assert resp.status_code == 200
    # Seed values untouched on the user model.
    assert fake_user.preferences == {"language": "en", "autoSave": True}
    # Response surfaces the same.
    prefs = resp.json()["preferences"]
    assert prefs["language"] == "en"
    assert prefs["autoSave"] is True


def test_update_profile_typed_preferences_rejects_invalid_types(
    client: TestClient, fake_user: User
):
    """Pydantic rejects wrong types (e.g., string for `autoSave` bool) with 422."""
    resp = client.put(
        "/api/v1/profile/",
        json={"preferences": {"autoSave": "not-a-bool"}},
    )
    assert resp.status_code == 422


def test_update_profile_explicit_null_clears_key(
    client: TestClient, fake_user: User
):
    """Sending `{key: null}` must clear the persisted value, not be ignored.

    Regression guard: `model_dump(exclude_unset=True)` (not `exclude_none=True`)
    so explicit nulls flow through the merge and overwrite the stored value.
    """
    # Seed had autoSave=True.
    resp = client.put(
        "/api/v1/profile/",
        json={"preferences": {"autoSave": None}},
    )
    assert resp.status_code == 200
    # The stored dict now has autoSave=None — frontend can finally "unset" it.
    assert fake_user.preferences["autoSave"] is None
    # Other seeded keys are preserved.
    assert fake_user.preferences["language"] == "en"


def test_update_profile_preserves_extra_legacy_keys(
    client: TestClient, fake_user: User
):
    """Legacy/extra preference keys not declared in UserPreferences survive a PUT.

    Regression guard: `model_config = ConfigDict(extra='allow')` on
    UserPreferences. Without it, Pydantic silently drops `theme` from the
    response body even though the underlying row keeps it.
    """
    fake_user.preferences = {"language": "en", "theme": "dark"}

    resp = client.put(
        "/api/v1/profile/",
        json={"preferences": {"language": "es"}},
    )
    assert resp.status_code == 200
    # Response body keeps the legacy key.
    assert resp.json()["preferences"].get("theme") == "dark"
    # Underlying user model keeps it too.
    assert fake_user.preferences["theme"] == "dark"
    assert fake_user.preferences["language"] == "es"
