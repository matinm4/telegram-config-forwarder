"""Unit tests for exact-match deduplication (T019, FR-003/Q5)."""
from src.extraction.normalizer import exact_hash_of

A = "vless://u@example.com:443#n"


def test_same_string_same_hash():
    assert exact_hash_of(A) == exact_hash_of(A)


def test_whitespace_difference_is_not_duplicate():
    # مصوب Q5: تطبیق دقیق بدون نرمال‌سازی
    assert exact_hash_of(A) != exact_hash_of(A + " ")
    assert exact_hash_of(A) != exact_hash_of(" " + A)


def test_different_configs_differ():
    assert exact_hash_of(A) != exact_hash_of(A.replace("443", "8443"))


def test_hash_stable_hex():
    h = exact_hash_of(A)
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)
