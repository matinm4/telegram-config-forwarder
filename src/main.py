"""CLI entrypoint with production wiring and observability (T030/T055)."""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import shutil
import sys

if sys.platform == "win32":  # کنسول ویندوز برای متن فارسی
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - best effort only
        pass

from src.config_loader import ConfigError, Secrets, load_config
from src.distribution.distributor import Distributor
from src.location.geoip import GeoIpLocator
from src.logging_setup import setup_logging
from src.persistence.state_store import StateStore
from src.pipeline import run_once
from src.providers.bot_sender import BotApiSender
from src.providers.scrape_source import ScrapeSourceProvider
from src.testing.xray_tester import XrayTester

log = logging.getLogger("forwarder")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="سامانه خودکار جمع‌آوری و انتشار کانفیگ تلگرام")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--state", default="state/state.json")
    parser.add_argument("--once", action="store_true",
                        help="اجرای یک چرخه کامل و خروج")
    parser.add_argument("--summary-file", default=None,
                        help="مسیر فایل خلاصه اجرا (مثل GITHUB_STEP_SUMMARY)")
    return parser


def build_components(config, secrets: Secrets):
    """Wire real providers/senders/tester/locator from config + secrets."""
    providers = {"scrape": ScrapeSourceProvider()}
    if all((secrets.api_id, secrets.api_hash, secrets.session_string)):
        from src.providers.telethon_source import TelethonSourceProvider
        providers["telethon"] = TelethonSourceProvider(
            secrets.api_id, secrets.api_hash, secrets.session_string)
    senders = {"bot_api": BotApiSender(secrets.bot_token)}
    if all((secrets.api_id, secrets.api_hash, secrets.session_string)):
        from src.providers.telethon_sender import TelethonSender
        senders["telethon"] = TelethonSender(
            secrets.api_id, secrets.api_hash, secrets.session_string)
    tester = None
    if config.testing.enabled:
        tester = XrayTester(timeout_s=config.testing.timeout_s,
                              max_concurrency=config.concurrency.test_limit,
                              max_attempts=config.retry.max_attempts,
                              backoff_s=tuple(config.retry.backoff_s))
    locator = None
    if config.location.enabled:
        locator = GeoIpLocator(
            fallback_display=config.location.fallback_display,
            db_path="GeoLite2-City.mmdb")
    return providers, senders, tester, locator


def write_summary(summary: dict, path: str | None) -> None:
    lines = ["## خلاصه اجرا",
             f"- دریافت: {summary['fetched_posts']}",
             f"- استخراج: {summary['extracted']}",
             f"- ارسال موفق: {summary['sent']}",
             f"- ناموفق: {summary['failed']}",
             f"- تکراری ردشده: {summary['skipped_duplicates']}"]
    text = "\n".join(lines)
    print(text.replace("## خلاصه اجرا\n", ""))
    target = path or os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        try:
            with open(target, "a", encoding="utf-8") as fh:
                fh.write(text + "\n")
        except OSError:
            log.warning("نوشتن خلاصه اجرا ممکن نشد.")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        secrets = Secrets.from_env()
    except ConfigError as exc:
        print(f"خطا: {exc}", file=sys.stderr)
        return 2
    setup_logging(config.logging.level, secrets.values())
    if not shutil.which("xray") and config.testing.enabled:
        log.warning("باینری Xray یافت نشد؛ تست‌ها رد می‌شوند.")
    store = StateStore(args.state)
    providers, senders, tester, locator = build_components(config,
                                                           secrets)
    distributor = Distributor(strategy=config.distribution.strategy,
                              cursor=store.state.distribution_cursor)
    try:
        summary = asyncio.run(run_once(config, secrets, store,
                                       providers, senders, tester,
                                       locator, None, distributor))
    except Exception:  # noqa: BLE001 - top-level guard with clean exit
        log.exception("اجرای چرخه با خطای غیرمنتظره متوقف شد.")
        return 1
    write_summary(summary, args.summary_file)
    if summary["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
