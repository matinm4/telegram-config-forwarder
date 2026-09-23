"""Pydantic data models for all pipeline entities (T009)."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

FetchMode = Literal["scrape", "telethon", "auto"]
SenderKind = Literal["bot_api", "telethon", "auto"]
Strategy = Literal["round_robin", "broadcast", "balanced",
                   "source_based", "per_destination"]
FilterType = Literal["exact", "regex"]
FilterScope = Literal["text", "caption", "both"]
TestStatus = Literal["success", "failed", "timeout", "skipped"]
SendStatus = Literal["sent", "failed", "pending"]


class SourceChannel(BaseModel):
    id: str
    username: str
    enabled: bool = True
    fetch_mode: FetchMode = "auto"
    proxy: Optional[str] = None


class Post(BaseModel):
    id: int = Field(gt=0)
    channel: str
    url: str = ""
    text: str = ""
    date_iso: Optional[str] = None
    is_pinned: bool = False
    is_forwarded: bool = False
    media_types: list[str] = Field(default_factory=list)


class ExtractedConfig(BaseModel):
    raw: str
    protocol: str = "unknown"
    source_channel: str = ""
    source_post_id: int = 0
    exact_hash: str = ""
    is_valid: bool = True


class FilterRule(BaseModel):
    type: FilterType = "exact"
    pattern: str
    scope: FilterScope = "both"
    enabled: bool = True


class Location(BaseModel):
    country_code: Optional[str] = None
    region: Optional[str] = None
    source: str = "fallback"
    display: str = "Unknown"


class TestResult(BaseModel):
    status: TestStatus = "skipped"
    latency_ms: Optional[int] = None
    checked_at: str = ""
    error_class: Optional[str] = None


class Destination(BaseModel):
    id: str
    chat: str
    enabled: bool = True
    sender: SenderKind = "auto"
    message_template: str = "default"
    quarantine: bool = False
    append_username: bool = True
    rules: list[FilterRule] = Field(default_factory=list)


class DistributionState(BaseModel):
    strategy: Strategy = "round_robin"
    cursor: int = 0
    counters: dict[str, int] = Field(default_factory=dict)


class FormattedMessage(BaseModel):
    config_raw: str
    destination_id: str
    body: str
    send_status: SendStatus = "pending"
    sent_at: Optional[str] = None


class RunRecord(BaseModel):
    started_at: str
    finished_at: str = ""
    fetched_posts: int = 0
    extracted: int = 0
    tested: int = 0
    failed: int = 0
    sent: int = 0
    errors: list[str] = Field(default_factory=list)


class RunState(BaseModel):
    schema_version: int = 1
    last_processed_id: dict[str, int] = Field(default_factory=dict)
    published_hashes: list[str] = Field(default_factory=list)
    distribution_cursor: int = 0
    distribution_counters: dict[str, int] = Field(default_factory=dict)
    consecutive_failures: dict[str, int] = Field(default_factory=dict)
    runs: list[RunRecord] = Field(default_factory=list)
