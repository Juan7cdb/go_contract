"""Shared pytest fixtures and fakes for the backend test suite.

`FakeAsyncSession` is the union of the surfaces previously inlined in
`test_profile.py` and `test_billing.py` — exposing:

- `add(obj)` (records the object, assigns a fake id if missing, stores it
  keyed by `(type, id)` so subsequent `get()` calls see the same row)
- `delete(obj)` (no-op, used by profile account-deletion path)
- `get(Model, pk)` / `scalar(stmt)` (with a `set_scalar(sql_hint, value)`
  registration helper) / lifecycle no-ops (`flush` / `commit` / `rollback`
  / `close`)
- `seed(Model, obj)` / `set_scalar(key, value)` registration helpers for
  tests that need a specific state before the request

Tests that previously imported this class inline now `from tests.conftest
import FakeAsyncSession` (pytest auto-loads conftest.py, so the import
path works without any sys.path tweaks).
"""
from __future__ import annotations

from typing import Any


class FakeAsyncSession:
    """In-memory stand-in for `sqlalchemy.ext.asyncio.AsyncSession`.

    Supports both the profile router's tiny surface (`add` + `delete` +
    lifecycle no-ops) and the billing webhook's richer surface (`get` /
    `scalar` with registered handlers, `seed` for setup).
    """

    def __init__(self) -> None:
        self.store: dict[tuple[type, Any], Any] = {}
        self.added: list[Any] = []
        # Map of "select description" → callable(self) -> object. Tests
        # can inject specific scalar() responses keyed by repr of stmt.
        self.scalar_handlers: dict[str, Any] = {}
        self._auto_id = 1000

    # ---- registration helpers (used by tests) -----------------------------

    def seed(self, model: type, obj: Any) -> None:
        self.store[(model, obj.id)] = obj

    def set_scalar(self, key: str, value: Any) -> None:
        self.scalar_handlers[key] = value

    # ---- AsyncSession surface --------------------------------------------

    def add(self, obj: Any) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = self._auto_id
            self._auto_id += 1
        # Replace existing rows by (type, id) so subsequent get() sees updates.
        self.store[(type(obj), obj.id)] = obj
        self.added.append(obj)

    async def get(self, model: type, pk: Any) -> Any:
        return self.store.get((model, pk))

    async def scalar(self, stmt: Any) -> Any:
        # Resolve by inspecting the compiled SQL for a hint. Test code
        # registers handlers under string keys it expects to appear.
        try:
            sql = str(stmt)
        except Exception:  # noqa: BLE001
            sql = ""
        for key, value in self.scalar_handlers.items():
            if key in sql:
                if callable(value):
                    return value()
                return value
        return None

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def delete(self, obj: Any) -> None:
        return None
