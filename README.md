# Telegram Bot for AppTweak Ads Search

این بات تلگرام برای جستجوی تبلیغات اپلیکیشن‌ها در App Store با استفاده از AppTweak API ساخته شده است.

## ویژگی‌ها

- جستجوی کلمات کلیدی در App Store
- پیدا کردن اولین تبلیغ (ad) برای کلمه کلیدی
- برگرداندن لینک اپلیکیشن به فرمت `https://apps.apple.com/app/id{application_id}`

## تنظیمات

متغیرهای محیطی مورد نیاز:

- `TELEGRAM_BOT_TOKEN`: توکن بات تلگرام
- `APP_TWEAK_API_KEY`: کلید API AppTweak
- `ADMIN_ID`: شناسه عددی ادمین (اختیاری)
- `PORT`: پورت برای اجرا (پیش‌فرض: 8000)

## نصب و اجرا

```bash
pip install -r requirements.txt
python bot.py
```

## استقرار روی Railway

### مراحل استقرار:

1. **آماده‌سازی پروژه:**
   - پروژه را به یک repository در GitHub push کنید

2. **ایجاد پروژه در Railway:**
   - به [Railway](https://railway.com/new) بروید
   - روی "New Project" کلیک کنید
   - "Deploy from GitHub repo" را انتخاب کنید
   - repository خود را انتخاب کنید

3. **تنظیم متغیرهای محیطی:**
   در بخش Variables پروژه، متغیرهای زیر را اضافه کنید:
   ```
   TELEGRAM_BOT_TOKEN=8569195623:AAFrobmCrcnnLzrg-SzXGcRiIxXNzIEdlT4
   APP_TWEAK_API_KEY=CGXefdBhfEpuAJQ-sIf8sEJmi18
   ADMIN_ID=295984673
   ```

4. **Deploy:**
   - Railway به صورت خودکار پروژه را build و deploy می‌کند
   - در بخش Deployments می‌توانید لاگ‌ها را مشاهده کنید

5. **بررسی:**
   - بات باید به صورت خودکار شروع به کار کند
   - در تلگرام بات را پیدا کرده و `/start` را بزنید

## استفاده

1. بات را در تلگرام پیدا کنید و `/start` را بزنید
2. یک کلمه کلیدی را ارسال کنید
3. بات اولین تبلیغ را پیدا کرده و لینک را برمی‌گرداند

