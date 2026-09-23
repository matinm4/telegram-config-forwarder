"""Structured logging with secret redaction (T011)."""
from __future__ import annotations

import logging
import re
from typing import Iterable

MASK = "***"
_PATTERNS = [
    re.compile(r"\d{6,12}:[A-Za-z0-9_-]{20,}"),   # bot token shape
    re.compile(r"\b[0-9a-fA-F]{32}\b"),            # api hash shape
]


class RedactingFilter(logging.Filter):
    """Masks known secret values and secret-like patterns in log records."""

    def __init__(self, secrets: Iterable[str] = ()) -> None:
        super().__init__()
        self._values = sorted({s for s in secrets if s}, key=len,
                              reverse=True)

    def redact(self, text: str) -> str:
        for value in self._values:
            if value:
                text = text.replace(value, MASK)
        for pattern in _PATTERNS:
            text = pattern.sub(MASK, text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self.redact(str(record.msg))
        if record.args:
            try:
                record.args = tuple(
                    self.redact(str(a)) for a in record.args
                )
            except TypeError:
                record.args = ()
        return True


def setup_logging(level: str = "INFO",
                  secrets: Iterable[str] = ()) -> logging.Logger:
    logger = logging.getLogger("forwarder")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
    filt = RedactingFilter(secrets)
    for handler in logger.handlers:
        handler.filters = [f for f in handler.filters
                           if not isinstance(f, RedactingFilter)]
        handler.addFilter(filt)
    return logger
