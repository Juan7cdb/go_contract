"""Smoke tests for wire-format guarantees and Alembic migration parseability."""
import importlib.util
from pathlib import Path

from app.main import app


def test_user_preferences_schema_uses_camelcase():
    """UserPreferences fields must serialize as camelCase in the OpenAPI schema.

    The Python model now uses snake_case (`auto_save`) with an
    `alias_generator=to_camel` so the wire stays camelCase. Regression guard
    against accidentally flipping `by_alias` defaults.
    """
    schema = app.openapi()
    prefs = schema["components"]["schemas"]["UserPreferences"]
    assert sorted(prefs["properties"].keys()) == [
        "aiSuggestions",
        "autoSave",
        "language",
        "timezone",
        "twoFactor",
    ]


def test_backfill_preferences_migration_parses():
    """`alembic upgrade head` requires every revision file to import cleanly."""
    path = (
        Path(__file__).resolve().parent.parent
        / "alembic"
        / "versions"
        / "f1a7c9d2e8b4_backfill_null_user_preferences.py"
    )
    spec = importlib.util.spec_from_file_location("backfill_migration", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.revision == "f1a7c9d2e8b4"
    assert mod.down_revision == "e9f6a4b2c1d3"
    # Both up/down must be callable.
    assert callable(mod.upgrade)
    assert callable(mod.downgrade)
