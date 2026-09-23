# قرارداد: ارسال‌کننده مقصد (DestinationSender)

> این فایل به **زبان فارسی** نوشته شده است. نام‌ها و امضاها انگلیسی باقی می‌مانند.

## هدف

انتزاع ارسال پیام تا تعویض مسیر (Bot API / Telethon) بدون تغییر منطق کسب‌وکار ممکن باشد.

## واسط

```python
class DestinationSender(Protocol):
    name: str  # "bot_api" | "telethon"

    async def send(self, destination: Destination, body: str) -> SendResult:
        """متن آماده را به مقصد ارسال می‌کند."""
```

## قرارداد ورودی/خروجی

- ورودی: `destination` فعال و `body` قالب‌بندی‌شده نهایی (بدون secret).
- خروجی: `SendResult(ok: bool, message_id: str | None, error_class: str | None)`.
- ترتیب ارسال در هر مقصد حفظ می‌شود؛ محدودیت نرخ تلگرام با انتظار مؤدبانه رعایت می‌شود.

## قرارداد خطا

- خطای موقت (429/5xx/timeout): `ok=False` با `error_class="retryable"`؛ فراخواننده تا سقف قابل تنظیم تلاش مجدد می‌کند.
- خطای قطعی (chat نامعتبر، مسدود بودن): `ok=False` با `error_class="permanent"`؛ بدون تلاش مجدد در همین چرخه و ثبت در لاگ.
- شکست ارسال به یک مقصد، ارسال به مقصدهای دیگر را متوقف نمی‌کند.

## پیاده‌سازی‌ها

- `BotApiSender` (مسیر اصلی): HTTPS مستقیم با `BOT_TOKEN` از محیط.
- `TelethonSender` (جایگزین): با `API_ID`/`API_HASH`/`SESSION_STRING` از محیط؛ حالت `auto` یعنی تلاش با اصلی و سپس جایگزین.
