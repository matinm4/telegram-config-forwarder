"""Unit tests for combined exact+regex cleaning (T032, Q3/C)."""
from src.filtering.cleaner import Cleaner
from src.models import FilterRule


def _cleaner():
    return Cleaner([
        FilterRule(type="exact", pattern="تبلیغات", scope="both",
                   enabled=True),
        FilterRule(type="regex", pattern=r"@\w+", scope="text",
                   enabled=True),
        FilterRule(type="exact", pattern="off-rule", scope="both",
                   enabled=False),
        FilterRule(type="regex", pattern="([broken", scope="both",
                   enabled=True),
    ])


def test_exact_removed():
    assert "تبلیغات" not in _cleaner().clean("متن تبلیغات خوب", "text")


def test_regex_removed():
    assert "@spam" not in _cleaner().clean("hey @spam hi", "text")


def test_disabled_rule_ignored():
    assert "off-rule" in _cleaner().clean("keep off-rule", "text")


def test_broken_regex_skipped_safely():
    assert _cleaner().clean("plain text", "text") == "plain text"


def test_scope_caption():
    assert "@spam" in _cleaner().clean("hey @spam", "caption")
    out = Cleaner([FilterRule(type="exact", pattern="x", scope="caption",
                              enabled=True)]).clean("ax b", "caption")
    assert out == "a b"
