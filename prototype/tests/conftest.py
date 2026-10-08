"""
Shared fixtures for the Unit 7 test suite (integration, system and acceptance tests).

Every test runs against its own temporary database, so the real helpdesk.db is never
read, changed or deleted.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # the prototype folder

import models  # noqa: E402


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "DB_PATH", tmp_path / "test.db")
    models.init_db()
    import app as app_module
    app_module.app.config.update(TESTING=True)
    return app_module


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


@pytest.fixture()
def login(client):
    def _login(username):
        return client.post("/login", data={"username": username})
    return _login


@pytest.fixture()
def submit(client):
    def _submit(description):
        return client.post("/submit", data={"description": description})
    return _submit


@pytest.fixture()
def db(app_module):
    def _query(sql, params=()):
        conn = models.get_connection()
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()
    return _query


@pytest.fixture()
def rendered(app_module):
    """Records the template name and data of every page rendered, so a test can check
    what the page received without depending on the exact HTML."""
    from flask import template_rendered
    captured = []

    def _record(sender, template, context, **extra):
        captured.append((template.name, dict(context)))

    template_rendered.connect(_record, app_module.app)
    yield captured
    template_rendered.disconnect(_record, app_module.app)
