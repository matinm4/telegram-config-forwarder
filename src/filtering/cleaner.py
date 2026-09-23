"""Combined exact + optional-regex text cleaning (T034, Q3/C)."""
from __future__ import annotations

import logging
import re

from src.models import FilterRule

log = logging.getLogger("forwarder")


class Cleaner:
    """Applies enabled filter rules to a text scope."""

    def __init__(self, rules: list[FilterRule] | None = None) -> None:
        self._rules = [r for r in (rules or []) if r.enabled]
        self._regex: list[tuple[FilterRule, re.Pattern]] = []
        for rule in self._rules:
            if rule.type != "regex":
                continue
            try:
                self._regex.append((rule, re.compile(rule.pattern)))
            except re.error:
                log.warning("الگوی regex نامعتبر نادیده گرفته شد.")

    def clean(self, text: str, scope: str = "text") -> str:
        out = text or ""
        for rule in self._rules:
            if rule.type != "exact" or rule.scope not in (scope, "both"):
                continue
            out = out.replace(rule.pattern, "")
        for rule, pattern in self._regex:
            if rule.scope not in (scope, "both"):
                continue
            try:
                out = pattern.sub("", out)
            except re.error:
                continue
        return re.sub(r"[ \t]{2,}", " ", out).strip()
