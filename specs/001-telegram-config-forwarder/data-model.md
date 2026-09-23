# مدل داده: سامانه خودکار جمع‌آوری و انتشار کانفیگ تلگرام

**تاریخ**: 2026-09-23
**مبنا**: `spec.md` + `research.md`

> **قانون زبان (الزامی)**: این فایل به **زبان فارسی** نوشته شده است. نام فیلدها و شناسه‌ها انگلیسی باقی می‌مانند.

## ۱. کانال منبع (SourceChannel)

- فیلدها: `id` (شناسه پایدار متنی)، `username` (نام کاربری تمیز تلگرام)، `enabled` ( boolean )، `fetch_mode` (مقادیر `scrape` | `telethon` | `auto`)، `proxy` (اختیاری)، `last_processed_id` (عدد، وضعیت زمان اجرا).
- ارتباط: یک منبع، چند `Post` دارد.
- اعتبارسنجی: `username` باید پس از تمیزسازی ناتهی باشد؛ `fetch_mode` فقط یکی از سه مقدار مجاز.
- گذار وضعیت: `active` ⇄ `disabled` (با پیکربندی)؛ `error` موقت پس از خطا (شمارش و ادامه).

## ۲. پست (Post)

- فیلدها: `id` (شناسه عددی تلگرام در کنار `channel`)، `channel`، `url`، `text`، `date_iso`، `is_pinned`، `is_forwarded`، `media_types` (فهرست).
- ارتباط: هر پست صفر تا چند `ExtractedConfig` تولید می‌کند؛ پست سنجاق‌شده فیلتر می‌شود.
- اعتبارسنجی: `id > 0`؛ کلید یکتایی `(channel, id)`؛ پست جدید یعنی `id > last_processed_id` همان منبع (FR-004).
- گذار وضعیت: `fetched` → `parsed` → `processed` | `skipped` (بدون متن قابل استخراج / تکراری / سنجاق‌شده).

## ۳. کانفیگ استخراج‌شده (ExtractedConfig)

- فیلدها: `raw` (رشته دقیق کانفیگ)، `protocol` (مثل `vless` | `vmess` | `trojan` | `ss` | `ssr` | `hysteria2` | `tuic` | `wireguard` | `unknown`)، `source_ref` (ارجاع `(channel, post_id)`)، `exact_hash` (هش تطبیق دقیق)، `is_valid`، `quarantined` ( boolean ).
- ارتباط: به یک `TestResult` و صفر یا یک `Location`؛ به یک یا چند مقصد از طریق `DistributionState` می‌رسد.
- اعتبارسنجی: `raw` ناتهی؛ تطبیق تکراری با **تطبیق دقیق رشته** روی `raw` بدون نرمال‌سازی (مصوب Q5)؛ کانفیگ بدقالب `is_valid=false` و کنار گذاشته می‌شود.
- گذار وضعیت: `extracted` → `deduped` → `cleaned` → `tested` | `quarantined` | `dropped`.

## ۴. قانون پالایش متن (FilterRule)

- فیلدها: `type` (مقادیر `exact` | `regex`)، `pattern` (عبارت یا الگو)، `scope` (مقادیر `text` | `caption` | `both`)، `enabled`.
- ارتباط: روی متن هر کانفیگ پیش از قالب‌بندی اعمال می‌شود (ترکیبی، مصوب Q3).
- اعتبارسنجی: `pattern` ناتهی؛ الگوی `regex` باید کامپایل شود وگرنه قانون غیرفعال و خطا ثبت می‌شود (افت تدریجی).

## ۵. موقعیت (Location)

- فیلدها: `country_code` (دو حرفی ISO یا `null`)، `region` (اختیاری)، `source` (مقادیر `geoip` | `fallback`)، `display` (رشته نمایشی یا مقدار جایگزین قابل تنظیم مثل `Unknown`).
- ارتباط: هر کانفیگ حداکثر یک موقعیت دارد.
- اعتبارسنجی: در صورت نبود پاسخ GeoIP، الزاماً مقدار جایگزین درج می‌شود و خط لوله متوقف نمی‌شود (FR-012).

## ۶. نتیجه تست (TestResult)

- فیلدها: `status` (مقادیر `success` | `failed` | `timeout` | `skipped`)، `latency_ms` (عدد صحیح یا `null`؛ فقط تاخیر application-level، هرگز ICMP)، `checked_at`، `error_class` (اختیاری، بدون secret).
- ارتباط: یک نتیجه سراسری برای هر کانفیگ که بین همه مقصدها مشترک است (مصوب Q4).
- اعتبارسنجی: `latency_ms` فقط وقتی ثبت می‌شود که `status=success`؛ timeout با آستانه قابل تنظیم از `failed` متمایز می‌شود.
- گذار وضعیت: `pending` → `success` | `failed` | `timeout` | `skipped` (قابلیت غیرفعال).

## ۷. کانال مقصد (Destination)

- فیلدها: `id` (شناسه پایدار)، `chat` (شناسه چت/کانال)، `enabled`، `sender` (مقادیر `bot_api` | `telethon` | `auto`)، `message_template` (ارجاع به قالب)، `rules` (قوانین مستقل: فیلتر اضافه، افزودن نام کاربری)، `quarantine` ( boolean : آیا این مقصدِ قرنطینه است).
- ارتباط: پیام‌های `FormattedMessage` را دریافت می‌کند؛ حداقل یک مقصد قرنطینه باید قابل تعریف باشد (FR-014).
- اعتبارسنجی: `chat` ناتهی؛ حداکثر یک مقصد قرنطینه فعال؛ قالب پیام باید معتبر باشد.

## ۸. وضعیت توزیع (DistributionState)

- فیلدها: `strategy` (پیش‌فرض `round_robin`؛ گزینه‌ها `broadcast` | `balanced` | `source_based` | `per_destination`)، `cursor` (موقعیت چرخشی)، `per_destination_counters`.
- ارتباط: نگاشت هر کانفیگ (غیرقرنطینه‌ای) به فهرست مقصدهای هدف.
- اعتبارسنجی: `cursor` بین اجراها پایدار است تا تکرار اجرا توزیع را به‌هم نریزد (اصل VIII).

## ۹. پیام نهایی (FormattedMessage)

- فیلدها: `config_ref`، `destination_id`، `body` (متن قالب‌بندی‌شده شامل کانفیگ، موقعیت، وضعیت تست، تاخیر در صورت وجود، نام کاربری مقصد)، `send_status` (مقادیر `sent` | `failed` | `pending`)، `sent_at`.
- اعتبارسنجی: طول پیام در سقف تلگرام؛ هیچ secret در `body` نیست (اصل XIII).

## ۱۰. وضعیت اجرا (RunState) — persisted در `state/state.json`

- فیلدها: `last_processed_id` به‌ازای هر منبع، `published_hashes` (مجموعه هش دقیق)، `distribution_cursor`، `distribution_counters` (شمارنده‌های استراتژی متوازن)، `consecutive_failures` (شمارنده خطاهای پیاپی هر منبع/فرستنده برای آستانه fallback)، `runs` (تاریخچه خلاصه: زمان، شمارش‌ها، خطاها)، `schema_version`.
- اعتبارسنجی: نوشتن اتمیک (فایل موقت + جابه‌جایی)؛ کامیت فقط پس از اتمام موفق چرخه؛ بارگذاری با مقدار پیش‌فرض امن در صورت نبود فایل (اجرای اول).
