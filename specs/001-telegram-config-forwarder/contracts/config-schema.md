# قرارداد: اسکیمای پیکربندی مرکزی (config.yaml)

> این فایل به **زبان فارسی** نوشته شده است. کلیدها انگلیسی باقی می‌مانند. اسرار هرگز اینجا نیستند (FR-029).

## ساختار سطح بالا

```yaml
version: 1
schedule:
  interval_hours: 3        # پیش‌فرض هر ۳ ساعت
sources:                   # فهرست کانال‌های منبع
  - id: "src1"
    username: "example_channel"
    enabled: true
    fetch_mode: "auto"     # scrape | telethon | auto
    proxy: null          # اختیاری، مثل socks5://127.0.0.1:10808
destinations:              # فهرست مقصدها
  - id: "main"
    chat: "@my_channel"
    enabled: true
    sender: "auto"         # bot_api | telethon | auto
    quarantine: false
  - id: "quarantine"
    chat: "@my_quarantine"
    enabled: true
    sender: "auto"
    quarantine: true       # حداکثر یک مقصد قرنطینه فعال
distribution:
  strategy: "round_robin"  # پیش‌فرض چرخشی (مصوب Q3)
filtering:
  enabled: true
  rules:                   # ترکیبی دقیق + الگو (مصوب Q3)
    - { type: "exact", pattern: "تبلیغات", scope: "both", enabled: true }
    - { type: "regex", pattern: "@\\w+", scope: "text", enabled: false }
  append_destination_username: true
location:
  enabled: true
  fallback_display: "Unknown"
testing:
  enabled: true
  timeout_s: 15
  xray_version: "v25.9.1"  # نسخه پین‌شده باینری
fallback:
  source_fallback_enabled: true
  sender_fallback_enabled: true
  after_failures: 2      # گذر به مسیر جایگزین پس از N خطای پیاپی قابل تلاش
retry:
  max_attempts: 3        # حداکثر تلاش برای خطای قابل تلاش (FR-033)
  backoff_s: [1, 2, 4]   # فاصله نمایی به ثانیه
concurrency:
  source_limit: 4        # حداکثر منابع هم‌زمان
  test_limit: 4          # حداکثر تست‌های Xray هم‌زمان
logging:
  level: "INFO"            # بدون چاپ secret در هیچ سطحی
```

## قرارداد

- همه رفتارهای اختیاری کلید صریح با مقدار پیش‌فرض مستند دارند (اصل III قانون اساسی).
- اعتبارسنجی در شروع اجرا انجام می‌شود؛ پیکربندی نامعتبر با پیام خطای فارسیِ بدون secret متوقف می‌شود.
- متغیرهای محیطی موردنیاز: `BOT_TOKEN`، (در صورت نیاز) `API_ID`، `API_HASH`، `SESSION_STRING`، و (در صورت فعال بودن موقعیت) `MAXMIND_LICENSE_KEY` برای دانلود پایگاه GeoIP — فقط از GitHub Secrets.
