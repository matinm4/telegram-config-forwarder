"""Build config records without touching the match string (T025)."""
from __future__ import annotations

import hashlib

from src.extraction.protocol_parser import parse_link
from src.models import ExtractedConfig


def exact_hash_of(raw: str) -> str:
    """Exact-match identity (Q5/A): no normalization of any kind."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_record(raw: str, channel: str, post_id: int) -> ExtractedConfig:
    cfg = parse_link(raw, channel, post_id)
    cfg.exact_hash = exact_hash_of(raw)
    return cfg
