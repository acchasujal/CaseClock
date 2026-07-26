"""Unit tests for Catalyst environment variable fallback resolution in CatalystRestDatastore."""

import os
import pytest
from backend.app.db.catalyst import CatalystRestDatastore, _env


def test_env_helper_primary_present(monkeypatch):
    monkeypatch.setenv("CATALYST_CLIENT_ID", "primary_val")
    monkeypatch.setenv("CASECLOCK_CLIENT_ID", "fallback_val")
    assert _env("CATALYST_CLIENT_ID", "CASECLOCK_CLIENT_ID") == "primary_val"


def test_env_helper_fallback_present(monkeypatch):
    monkeypatch.delenv("CATALYST_CLIENT_ID", raising=False)
    monkeypatch.setenv("CASECLOCK_CLIENT_ID", "fallback_val")
    assert _env("CATALYST_CLIENT_ID", "CASECLOCK_CLIENT_ID") == "fallback_val"


def test_env_helper_both_missing_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("CATALYST_CLIENT_ID", raising=False)
    monkeypatch.delenv("CASECLOCK_CLIENT_ID", raising=False)
    with pytest.raises(RuntimeError) as exc_info:
        _env("CATALYST_CLIENT_ID", "CASECLOCK_CLIENT_ID")
    assert "'CATALYST_CLIENT_ID' or 'CASECLOCK_CLIENT_ID'" in str(exc_info.value)


def test_env_helper_default_used_when_both_missing(monkeypatch):
    monkeypatch.delenv("CATALYST_API_DOMAIN", raising=False)
    monkeypatch.delenv("CASECLOCK_API_DOMAIN", raising=False)
    assert (
        _env("CATALYST_API_DOMAIN", "CASECLOCK_API_DOMAIN", default="https://api.catalyst.zoho.in")
        == "https://api.catalyst.zoho.in"
    )


def test_from_env_with_caseclock_prefix(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: None)
    # Clear all CATALYST_* vars
    for key in [
        "CATALYST_AUTH", "CATALYST_OPTIONS",
        "CATALYST_CLIENT_ID", "CATALYST_CLIENT_SECRET", "CATALYST_REFRESH_TOKEN",
        "CATALYST_PROJECT_ID", "CATALYST_PROJECT_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)

    # Set CASECLOCK_* vars
    monkeypatch.setenv("CASECLOCK_CLIENT_ID", "cc_client_123")
    monkeypatch.setenv("CASECLOCK_CLIENT_SECRET", "cc_secret_456")
    monkeypatch.setenv("CASECLOCK_REFRESH_TOKEN", "cc_refresh_789")
    monkeypatch.setenv("CASECLOCK_PROJECT_ID", "cc_proj_999")

    ds = CatalystRestDatastore.from_env()

    assert ds.auth["client_id"] == "cc_client_123"
    assert ds.auth["client_secret"] == "cc_secret_456"
    assert ds.auth["refresh_token"] == "cc_refresh_789"
    assert ds.project_id == "cc_proj_999"
    assert ds.project_key == "cc_proj_999"


def test_from_env_primary_overrides_fallback(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **kw: None)
    monkeypatch.delenv("CATALYST_AUTH", raising=False)
    monkeypatch.delenv("CATALYST_OPTIONS", raising=False)

    monkeypatch.setenv("CATALYST_CLIENT_ID", "cat_client_123")
    monkeypatch.setenv("CASECLOCK_CLIENT_ID", "cc_client_123")

    monkeypatch.setenv("CASECLOCK_CLIENT_SECRET", "cc_secret_456")
    monkeypatch.setenv("CASECLOCK_REFRESH_TOKEN", "cc_refresh_789")
    monkeypatch.setenv("CASECLOCK_PROJECT_ID", "cc_proj_999")

    ds = CatalystRestDatastore.from_env()
    assert ds.auth["client_id"] == "cat_client_123"

