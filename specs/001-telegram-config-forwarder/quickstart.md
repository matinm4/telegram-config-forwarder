# راهنمای اعتبارسنجی سریع (Quickstart)

**تاریخ**: 2026-09-23
**مبنا**: `spec.md` + `plan.md` (پس از تکمیل)

> **قانون زبان (الزامی)**: این فایل به **زبان فارسی** نوشته شده است. دستورها و مسیرها انگلیسی باقی می‌مانند.

## پیش‌نیازها

- Python 3.12 به‌همراه `pip`؛ دسترسی اینترنت؛ یک کانال منبع عمومی آزمایشی و دو کانال مقصد آزمایشی (یکی عادی، یکی قرنطینه).
- متغیرهای محیطی آزمایشی (مقادیر واقعی فقط از GitHub Secrets در تولید): `BOT_TOKEN` و در صورت تست Telethon `API_ID`/`API_HASH`/`SESSION_STRING`.

## راه‌اندازی

```bash
python -m venv .venv
source .venv/bin/activate  # ویندوز: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

## سناریوهای اعتبارسنجی

### ۱. جریان پایه MVP (داستان کاربر ۱)

```bash
pytest tests/integration/test_pipeline_mvp.py -v
python -m src.main --config config.yaml --once
```

- نتیجه مورد انتظار: کانفیگ‌های جدید منبع آزمایشی در مقصد عادی ظاهر می‌شوند؛ اجرای دوم بدون پست جدید، صفر ارسال دارد (رجوع به [مدل داده](data-model.md) بخش وضعیت اجرا).

### ۲. پالایش و قالب پیام (داستان کاربر ۲)

```bash
pytest tests/unit/test_filtering.py tests/unit/test_formatting.py -v
```

- نتیجه مورد انتظار: عبارت‌های قانون نمونه حذف شده‌اند و نام کاربری مقصد در پیام درج شده است (رجوع به [قرارداد قالب پیام](contracts/message-format.md)).

### ۳. موقعیت و تست با افت تدریجی (داستان کاربر ۳)

```bash
pytest tests/integration/test_testing_location.py -v
python -m src.main --config config.yaml --once --disable testing
```

- نتیجه مورد انتظار: با تست فعال، پیام شامل موقعیت و وضعیت است؛ کانفیگ ناموفق به مقصد قرنطینه می‌رود؛ با تست غیرفعال، چرخه بدون توقف و بدون برچسب تست اجرا می‌شود.

### ۴. توزیع چندمقصدی (داستان کاربر ۴)

```bash
pytest tests/unit/test_distribution.py -v
```

- نتیجه مورد انتظار: با دو مقصد و استراتژی چرخشی، چهار کانفیگ به‌صورت ۲-۲ تقسیم می‌شوند و مکان‌نمای توزیع در `state/state.json` پیش می‌رود.

### ۵. بهره‌برداری خودکار (داستان کاربر ۵)

```bash
act -j run  # اجرای محلی گردش کار در صورت نصب act (اختیاری)
```

- نتیجه مورد انتظار: گردش کار زمان‌بندی‌شده و اجرای دستی هر دو کار می‌کنند؛ `state/state.json` کامیت می‌شود؛ هیچ secret در لاگ نیست (رجوع به [اسکیمای پیکربندی](contracts/config-schema.md)).

## پیوندها

- واسط‌ها: [ارائه‌دهنده منبع](contracts/source-provider.md)، [ارسال‌کننده مقصد](contracts/destination-sender.md)، [آزمون‌کننده](contracts/config-tester.md)
- جزئیات تحقیق: [research.md](research.md)
