"""Central configuration loading and validation (T010).

Secrets are NEVER read from the config file - only from the environment.
All user-facing errors are in Persian and never echo secret values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.models import Destination, FilterRule, SourceChannel


class ConfigError(Exception):
    """Raised for any configuration problem (file or environment)."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Schedule(StrictModel):
    interval_hours: int = Field(default=3, gt=0, le=168)


class Distribution(StrictModel):
    strategy: str = "round_robin"


class Filtering(StrictModel):
    enabled: bool = True
    rules: list[FilterRule] = Field(default_factory=list)
    append_destination_username: bool = True


class LocationCfg(StrictModel):
    enabled: bool = True
    fallback_display: str = "Unknown"


class Testing(StrictModel):
    enabled: bool = True
    timeout_s: int = Field(default=15, gt=0, le=300)
    xray_version: str = "v25.9.1"


class Fallback(StrictModel):
    source_fallback_enabled: bool = True
    sender_fallback_enabled: bool = True
    after_failures: int = Field(default=2, ge=1, le=10)


class Retry(StrictModel):
    max_attempts: int = Field(default=3, ge=1, le=5)
    backoff_s: list[int] = Field(default_factory=lambda: [1, 2, 4],
                                 min_length=1)


class Concurrency(StrictModel):
    source_limit: int = Field(default=4, ge=1, le=16)
    test_limit: int = Field(default=4, ge=1, le=16)


class LoggingCfg(StrictModel):
    level: str = "INFO"


class AppConfig(StrictModel):
    version: int = 1
    schedule: Schedule = Schedule()
    sources: list[SourceChannel] = Field(default_factory=list)
    destinations: list[Destination] = Field(default_factory=list)
    distribution: Distribution = Distribution()
    filtering: Filtering = Filtering()
    location: LocationCfg = LocationCfg()
    testing: Testing = Testing()
    fallback: Fallback = Fallback()
    retry: Retry = Retry()
    concurrency: Concurrency = Concurrency()
    logging: LoggingCfg = LoggingCfg()


@dataclass(frozen=True)
class Secrets:
    bot_token: str
    api_id: Optional[str] = None
    api_hash: Optional[str] = None
    session_string: Optional[str] = None
    maxmind_license_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Secrets":
        token = os.environ.get("BOT_TOKEN")
        if not token:
            raise ConfigError("پیکربندی: متغیر محیطی BOT_TOKEN یافت نشد.")
        return cls(
            bot_token=token,
            api_id=os.environ.get("API_ID"),
            api_hash=os.environ.get("API_HASH"),
            session_string=os.environ.get("SESSION_STRING"),
            maxmind_license_key=os.environ.get("MAXMIND_LICENSE_KEY"),
        )

    def values(self) -> list[str]:
        out = [self.bot_token]
        for v in (self.api_id, self.api_hash, self.session_string,
                  self.maxmind_license_key):
            if v:
                out.append(v)
        return out


def load_config(path: str) -> AppConfig:
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except FileNotFoundError as exc:
        raise ConfigError(f"پیکربندی: فایل {path} یافت نشد.") from exc
    except yaml.YAMLError as exc:
        raise ConfigError("پیکربندی: فایل YAML معتبر نیست.") from exc
    try:
        cfg = AppConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError("پیکربندی: مقادیر نامعتبر است.") from exc
    active_quarantines = [d.id for d in cfg.destinations
                          if d.enabled and d.quarantine]
    if len(active_quarantines) > 1:
        raise ConfigError("پیکربندی: حداکثر یک مقصد قرنطینه فعال مجاز است.")
    usernames = [s.username.strip().lstrip("@").lower()
                 for s in cfg.sources if s.enabled]
    if any(not u for u in usernames):
        raise ConfigError("پیکربندی: نام کاربری منبع نمی‌تواند خالی باشد.")
    return cfg
