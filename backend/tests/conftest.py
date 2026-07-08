"""Root pytest configuration and shared test-runtime patches.

Patches are applied before integration test modules import ``TestClient(app)``,
preventing multi-minute PostgreSQL connection timeouts during app lifespan when
Postgres is not running locally.
"""

from __future__ import annotations

import pytest

from tests.constants import TEST_PASSWORD, TEST_PASSWORD_HASH

__all__ = ["TEST_PASSWORD", "TEST_PASSWORD_HASH"]


def _patch_database_lifecycle_for_tests() -> None:
    """Bypass real PostgreSQL connectivity checks during test app startup."""
    import app.db.session as db_session
    import app.main as main
    import app.services.index_bootstrap_service as bootstrap_module

    db_session.check_database_connection = lambda: True  # type: ignore[method-assign]
    main.check_database_connection = lambda: True  # type: ignore[method-assign]
    db_session.engine.dispose = lambda: None  # type: ignore[method-assign]
    bootstrap_module.bootstrap_search_index = lambda *args, **kwargs: 0  # type: ignore[method-assign]


def pytest_configure(config: pytest.Config) -> None:
    """Apply global test patches before test module collection imports the app."""
    _patch_database_lifecycle_for_tests()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-mark tests by directory for selective execution."""
    for item in items:
        path = str(item.path)
        if "/integration/" in path.replace("\\", "/"):
            item.add_marker(pytest.mark.integration)
        elif "/unit/" in path.replace("\\", "/"):
            item.add_marker(pytest.mark.unit)
