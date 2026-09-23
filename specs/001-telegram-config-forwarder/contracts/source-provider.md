# قرارداد: ارائه‌دهنده منبع (SourceProvider)

> این فایل به **زبان فارسی** نوشته شده است. نام‌ها و امضاها انگلیسی باقی می‌مانند.

## هدف

انتزاع دریافت پست‌ها از کانال منبع تا تعویض روش (اسکرپ / Telethon) بدون تغییر منطق کسب‌وکار ممکن باشد (مصوب Q1).

## واسط

```python
class SourceProvider(Protocol):
    name: str  # "scrape" | "telethon"

    async def fetch_new_posts(self, source: SourceChannel, since_id: int) -> list[Post]:
        """فقط پست‌های با id بزرگ‌تر از since_id را برمی‌گرداند؛ مرتب صعودی."""
```

## قرارداد ورودی/خروجی

- ورودی: `source` (پیکربندی منبع فعال) و `since_id` (آخرین شناسه پردازش‌شده).
- خروجی: فهرست `Post` با `id` و `channel` معتبر؛ پست سنجاق‌شده در همین لایه فیلتر می‌شود.
- پست بدون متن قابل استخراج با `text=""` برمی‌گردد (تصمیم‌گیری با مرحله استخراج است، نه اینجا).

## قرارداد خطا

- خطای شبکه/timeout: استثنای `SourceFetchError` با `source_id` و `retryable` مشخص.
- منبع نامعتبر/خصوصی بدون دسترسی: استثنای `SourceAccessError` (غیرقابل تلاش مجدد در همین چرخه).
- هیچ استثنایی نباید کل چرخه را متوقف کند؛ فراخواننده ایزوله می‌کند (FR-024).

## پیاده‌سازی‌ها

- `ScrapeSourceProvider`: تطبیق `fast_engine` + `TelegramParser` مرجع؛ بدون اعتبار.
- `TelethonSourceProvider`: با `API_ID`/`API_HASH`/`SESSION_STRING` از محیط؛ فقط وقتی `fetch_mode` آن را بخواهد.
