# سامانه خودکار جمع‌آوری و انتشار کانفیگ تلگرام

[فارسی](#فارسی) | [English](#english)

---

## فارسی

سیستم خودکاری که کانال‌های منبع تلگرام را می‌خواند، کانفیگ‌های تازه را استخراج و پردازش می‌کند و به مقصدهای تعیین‌شده می‌فرستد. اجرای اصلی هر ۳ ساعت یک‌بار در GitHub Actions انجام می‌شود؛ بدون نیاز به روشن بودن رایانه شخصی.

**قابلیت‌ها:** چند منبع و چند مقصد، حذف امضا/تبلیغ با قوانین ترکیبی، تشخیص موقعیت، تست اتصال با Xray (با تاخیر واقعی مسیر)، توزیع چرخشی، مقصد قرنطینه برای کانفیگ‌های ناموفق، مسیر جایگزین Telethon، جلوگیری از انتشار تکراری، لاگ بدون secret.

**شروع سریع:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
# ویرایش config.yaml + تنظیم BOT_TOKEN
python -m src.main --config config.yaml --once
pytest tests/ -q
```

مستندات: [راهنمای فارسی پیکربندی](docs/CONFIGURATION.fa.md) | [معماری](docs/ARCHITECTURE.md) | [عیب‌یابی](docs/TROUBLESHOOTING.md)

**امنیت:** توکن‌ها و نشست‌ها فقط از متغیر محیطی (در تولید: GitHub Secrets) خوانده می‌شوند و هرگز در مخزن یا لاگ قرار نمی‌گیرند.

---

## English

An automated system that reads Telegram source channels, extracts and processes fresh configs, and forwards them to configured destinations. Production runs every 3 hours on GitHub Actions — no personal computer needed.

**Features:** multiple sources/destinations, combined signature/ad filtering, location detection, Xray connectivity testing (real path latency), round-robin distribution, quarantine destination for failed configs, Telethon fallback, duplicate-free publishing, secret-free logging.

**Quickstart:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
# edit config.yaml + set BOT_TOKEN
python -m src.main --config config.yaml --once
pytest tests/ -q
```

Docs: [Persian configuration guide](docs/CONFIGURATION.fa.md) | [Architecture](docs/ARCHITECTURE.md) | [Troubleshooting](docs/TROUBLESHOOTING.md)

**Security:** tokens and sessions are read only from the environment (in production: GitHub Secrets) and never stored in the repo or printed in logs.
