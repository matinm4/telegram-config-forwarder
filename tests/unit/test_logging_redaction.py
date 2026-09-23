"""Unit tests for secret redaction in logs (T007)."""
import logging

from src.logging_setup import RedactingFilter, setup_logging

FAKE_TOKEN = "FAKE_BOT_TOKEN_VALUE_12345"  # noqa: S105 - test fixture only


def _record(msg):
    return logging.LogRecord("t", logging.INFO, __file__, 10, msg, None, None)


def test_explicit_secret_masked():
    f = RedactingFilter(secrets=[FAKE_TOKEN])
    rec = _record(f"sending with {FAKE_TOKEN} now")
    assert f.filter(rec) is True
    assert FAKE_TOKEN not in rec.getMessage()
    assert "***" in rec.getMessage()


def test_bot_token_pattern_masked():
    f = RedactingFilter(secrets=[])
    token = "123456789:AAHfiqakKJlmnopqrstuvwxyz012345"  # noqa: S105
    rec = _record(f"use {token} here")
    f.filter(rec)
    assert token not in rec.getMessage()


def test_clean_message_untouched():
    f = RedactingFilter(secrets=[FAKE_TOKEN])
    rec = _record("processed 5 posts, sent 3")
    f.filter(rec)
    assert rec.getMessage() == "processed 5 posts, sent 3"


def test_setup_logging_returns_logger_with_filter():
    logger = setup_logging(level="INFO", secrets=[FAKE_TOKEN])
    assert any(isinstance(flt, RedactingFilter)
               for h in logger.handlers for flt in h.filters)
