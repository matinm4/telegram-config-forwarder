"""Unit tests for config loading and secrets handling (T006)."""
import os
import pytest
import yaml

from src.config_loader import load_config, Secrets, ConfigError


MINIMAL = {
    "version": 1,
    "schedule": {"interval_hours": 3},
    "sources": [{"id": "s1", "username": "ch1", "enabled": True,
                 "fetch_mode": "auto", "proxy": None}],
    "destinations": [
        {"id": "main", "chat": "@c1", "enabled": True,
         "sender": "auto", "quarantine": False},
        {"id": "q", "chat": "@cq", "enabled": True,
         "sender": "auto", "quarantine": True},
    ],
    "distribution": {"strategy": "round_robin"},
    "filtering": {"enabled": True, "rules": [],
                  "append_destination_username": True},
    "location": {"enabled": True, "fallback_display": "Unknown"},
    "testing": {"enabled": True, "timeout_s": 15, "xray_version": "v25.9.1"},
    "fallback": {"source_fallback_enabled": True,
                 "sender_fallback_enabled": True, "after_failures": 2},
    "logging": {"level": "INFO"},
}


def _write(tmp_path, data):
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    return str(p)


def test_valid_config_loads(tmp_path):
    cfg = load_config(_write(tmp_path, MINIMAL))
    assert cfg.schedule.interval_hours == 3
    assert cfg.distribution.strategy == "round_robin"
    assert len(cfg.sources) == 1


def test_bad_fetch_mode_rejected(tmp_path):
    bad = dict(MINIMAL)
    bad["sources"] = [{"id": "s1", "username": "ch1", "enabled": True,
                       "fetch_mode": "carrier_pigeon", "proxy": None}]
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, bad))


def test_two_quarantines_rejected(tmp_path):
    bad = dict(MINIMAL)
    bad["destinations"] = [
        {"id": "q1", "chat": "@a", "enabled": True,
         "sender": "auto", "quarantine": True},
        {"id": "q2", "chat": "@b", "enabled": True,
         "sender": "auto", "quarantine": True},
    ]
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, bad))


def test_missing_file_raises_persian(tmp_path):
    with pytest.raises(ConfigError) as exc:
        load_config(str(tmp_path / "nope.yaml"))
    assert "پیکربندی" in str(exc.value)


def test_secrets_require_bot_token(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(ConfigError):
        Secrets.from_env()


def test_secrets_never_from_file(tmp_path, monkeypatch):
    # config file must not carry secrets: unknown secret-like keys are rejected
    bad = dict(MINIMAL)
    bad["bot_token"] = "SHOULD-NOT-BE-HERE"  # noqa: S105
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, bad))
    monkeypatch.setenv("BOT_TOKEN", "dummy")  # noqa: S105
    assert Secrets.from_env().bot_token == "dummy"


def test_optional_secrets_default_none(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "dummy")  # noqa: S105
    for k in ("API_ID", "API_HASH", "SESSION_STRING",
              "MAXMIND_LICENSE_KEY"):
        monkeypatch.delenv(k, raising=False)
    s = Secrets.from_env()
    assert s.api_id is None and s.session_string is None


def test_retry_and_concurrency_defaults(tmp_path):
    cfg = load_config(_write(tmp_path, MINIMAL))
    assert cfg.retry.max_attempts == 3
    assert cfg.retry.backoff_s == [1, 2, 4]
    assert cfg.concurrency.source_limit == 4
    assert cfg.concurrency.test_limit == 4


def test_retry_custom_and_invalid(tmp_path):
    custom = dict(MINIMAL)
    custom["retry"] = {"max_attempts": 5, "backoff_s": [2, 4]}
    assert load_config(_write(tmp_path, custom)).retry.max_attempts == 5
    bad = dict(MINIMAL)
    bad["retry"] = {"max_attempts": 0, "backoff_s": [1]}
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, bad))
    empty = dict(MINIMAL)
    empty["retry"] = {"max_attempts": 3, "backoff_s": []}
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, empty))
