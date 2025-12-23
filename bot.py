import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
APP_TWEAK_API_KEY = os.getenv('APP_TWEAK_API_KEY', 'CGXefdBhfEpuAJQ-sIf8sEJmi18')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8569195623:AAFrobmCrcnnLzrg-SzXGcRiIxXNzIEdlT4')
ADMIN_ID = int(os.getenv('ADMIN_ID', '295984673'))
CHANNEL_ID = os.getenv('CHANNEL_ID', '-1003626600006')

APP_TWEAK_BASE_URL = 'https://public-api.apptweak.com/api/public/store/keywords/search-results/ads/current'

# Storage for user settings
user_settings = {}
user_waiting_input = {}  # Track users waiting for input

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send main menu with buttons."""
    user_id = update.effective_user.id
    
    # Initialize user settings if not exists
    if user_id not in user_settings:
        user_settings[user_id] = {
            'keyword': None,
            'country': 'de',
            'language': 'de',
            'interval': 5,
            'active': False
        }
    
    settings = user_settings[user_id]
    
    # Create status message
    status = "📋 تنظیمات فعلی:\n\n"
    status += f"🔍 کلمه کلیدی: {settings['keyword'] or '❌ تنظیم نشده'}\n"
    status += f"🌍 کشور: {settings['country'].upper()}\n"
    status += f"🗣️ زبان: {settings['language'].upper()}\n"
    status += f"⏰ فاصله: هر {settings['interval']} دقیقه\n\n"
    
    if settings['active']:
        status += "✅ کار تکراری در حال اجرا است!"
    else:
        status += "⏸️ کار تکراری متوقف است"
    
    # Create keyboard
    keyboard = [
        [InlineKeyboardButton("🔍 ست کردن کلمه کلیدی", callback_data="set_keyword")],
        [InlineKeyboardButton("🌍 ست کردن کشور", callback_data="set_country")],
        [InlineKeyboardButton("🗣️ ست کردن زبان", callback_data="set_language")],
    ]
    
    # Add manual search button
    if settings.get('keyword'):
        keyboard.append([InlineKeyboardButton("🔎 جستجوی دستی (الان)", callback_data="manual_search")])
    
    # Add start/stop button
    if settings['active']:
        keyboard.append([InlineKeyboardButton("⏸️ توقف", callback_data="stop_job")])
    else:
        keyboard.append([InlineKeyboardButton("▶️ شروع (هر 5 دقیقه)", callback_data="start_job")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(status, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(status, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "set_keyword":
        user_waiting_input[user_id] = 'keyword'
        await query.edit_message_text(
            "🔍 لطفاً کلمه کلیدی را ارسال کنید:\n\n"
            "مثال: ki video erstellen"
        )
    
    elif query.data == "set_country":
        # Show country options
        keyboard = [
            [InlineKeyboardButton("🇩🇪 آلمان (de)", callback_data="country_de")],
            [InlineKeyboardButton("🇺🇸 آمریکا (us)", callback_data="country_us")],
            [InlineKeyboardButton("🇬🇧 انگلیس (gb)", callback_data="country_gb")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🌍 کشور را انتخاب کنید:", reply_markup=reply_markup)
    
    elif query.data == "set_language":
        # Show language options
        keyboard = [
            [InlineKeyboardButton("🇩🇪 آلمانی (de)", callback_data="lang_de")],
            [InlineKeyboardButton("🇺🇸 انگلیسی (en)", callback_data="lang_en")],
            [InlineKeyboardButton("🇬🇧 انگلیسی UK (en)", callback_data="lang_en")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🗣️ زبان را انتخاب کنید:", reply_markup=reply_markup)
    
    elif query.data.startswith("country_"):
        country = query.data.split("_")[1]
        if user_id not in user_settings:
            user_settings[user_id] = {'country': country, 'language': 'de', 'keyword': None, 'interval': 5, 'active': False}
        else:
            user_settings[user_id]['country'] = country
        await start(update, context)
    
    elif query.data.startswith("lang_"):
        language = query.data.split("_")[1]
        if user_id not in user_settings:
            user_settings[user_id] = {'country': 'de', 'language': language, 'keyword': None, 'interval': 5, 'active': False}
        else:
            user_settings[user_id]['language'] = language
        await start(update, context)
    
    elif query.data == "start_job":
        settings = user_settings.get(user_id, {})
        
        if not settings.get('keyword'):
            await query.edit_message_text(
                "❌ ابتدا کلمه کلیدی را تنظیم کنید!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]])
            )
            return
        
        # Start the job
        settings['active'] = True
        settings['interval'] = 5  # Fixed 5 minutes
        settings['chat_id'] = CHANNEL_ID
        
        job_name = f"ads_job_{user_id}"
        job_queue = context.application.job_queue
        
        # Ensure job_queue is started
        if job_queue is None:
            logger.error("Job queue is None!")
            await query.edit_message_text("❌ خطا: Job queue در دسترس نیست!")
            return
        
        # Start job_queue if not already started
        try:
            if not hasattr(job_queue, '_running') or not job_queue._running:
                job_queue.start()
                logger.info("Job queue started")
        except Exception as e:
            logger.warning(f"Job queue start check: {e}")
        
        # Remove existing job if any
        try:
            existing_jobs = job_queue.get_jobs_by_name(job_name)
            if existing_jobs:
                logger.info(f"Removing existing job: {job_name}")
                existing_jobs[0].schedule_removal()
        except Exception as e:
            logger.warning(f"Error removing existing job: {e}")
        
        # Send first result immediately
        await query.edit_message_text(
            f"✅ کار تکراری شروع شد!\n\n"
            f"🔍 کلمه کلیدی: {settings['keyword']}\n"
            f"🌍 کشور: {settings['country'].upper()}\n"
            f"🗣️ زبان: {settings['language'].upper()}\n"
            f"⏰ هر 5 دقیقه یکبار\n\n"
            f"🔎 در حال جستجو..."
        )
        
        # Execute search immediately (first request)
        try:
            await execute_search(user_id, settings, context.bot)
            logger.info(f"Immediate search completed for user {user_id}")
        except Exception as e:
            logger.error(f"Error in immediate search: {e}")
        
        # Create recurring job - start after 5 minutes, then repeat every 5 minutes
        try:
            scheduled_job = job_queue.run_repeating(
                send_ads_list,
                interval=5 * 60,  # 5 minutes in seconds
                first=5 * 60,  # Start after 5 minutes (not immediately)
                name=job_name,
                data={'user_id': user_id}
            )
            logger.info(f"Recurring job scheduled: {job_name}")
            logger.info(f"Job will run in: {scheduled_job.next_t} seconds")
            logger.info(f"Job interval: {scheduled_job.interval} seconds")
            logger.info(f"Job active: {scheduled_job.enabled}")
        except Exception as e:
            logger.error(f"Error scheduling job: {e}")
            await query.edit_message_text(f"❌ خطا در تنظیم کار تکراری: {str(e)}")
            return
        
        await query.edit_message_text(
            f"✅ کار تکراری شروع شد!\n\n"
            f"🔍 کلمه کلیدی: {settings['keyword']}\n"
            f"🌍 کشور: {settings['country'].upper()}\n"
            f"🗣️ زبان: {settings['language'].upper()}\n"
            f"⏰ هر 5 دقیقه یکبار\n\n"
            f"✅ اولین جستجو انجام شد!\n"
            f"⏳ جستجوی بعدی: 5 دقیقه دیگر",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]])
        )
        
        logger.info(f"Job started for user {user_id}")
    
    elif query.data == "stop_job":
        if user_id in user_settings:
            user_settings[user_id]['active'] = False
        
        job_name = f"ads_job_{user_id}"
        try:
            jobs = context.application.job_queue.get_jobs_by_name(job_name)
            if jobs:
                jobs[0].schedule_removal()
        except:
            pass
        
        await query.edit_message_text(
            "✅ کار تکراری متوقف شد!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]])
        )
    
    elif query.data == "manual_search":
        settings = user_settings.get(user_id, {})
        
        if not settings.get('keyword'):
            await query.edit_message_text(
                "❌ ابتدا کلمه کلیدی را تنظیم کنید!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]])
            )
            return
        
        await query.edit_message_text("🔎 در حال جستجو...")
        
        try:
            await execute_search(user_id, settings, context.bot)
            await query.edit_message_text(
                "✅ جستجو انجام شد و نتایج به چنل ارسال شد!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]])
            )
        except Exception as e:
            logger.error(f"Error in manual search: {e}")
            await query.edit_message_text(
                f"❌ خطا در جستجو: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]])
            )
    
    elif query.data == "back_to_menu":
        await start(update, context)

async def execute_search(user_id, settings, bot):
    """Execute search and send results to channel."""
    keyword = settings.get('keyword')
    country = settings.get('country', 'de')
    language = settings.get('language', 'de')
    chat_id = settings.get('chat_id', CHANNEL_ID)
    
    if not keyword:
        return
    
    params = {
        'keyword': keyword,
        'language': language,
        'country': country,
        'device': 'iphone'
    }
    
    headers = {
        'X-Apptweak-Key': APP_TWEAK_API_KEY
    }
    
    logger.info(f"Searching: keyword={keyword}, country={country}, language={language}")
    
    response = requests.get(APP_TWEAK_BASE_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    
    # Find all ad results (only ads with is_ad == True, remove duplicates)
    ads_found = []
    seen_app_ids = set()  # Track seen application IDs to avoid duplicates
    
    if 'result' in data and isinstance(data['result'], list):
        for item in data['result']:
            # Only process items where is_ad is explicitly True
            if item.get('is_ad') == True:
                application_id = item.get('application_id')
                if application_id and application_id not in seen_app_ids:
                    seen_app_ids.add(application_id)
                    app_url = f"https://apps.apple.com/app/id{application_id}"
                    ads_found.append({
                        'url': app_url,
                        'app_id': application_id
                    })
    
    # Send results
    if ads_found:
        message = f"🔍 نتایج جستجو برای: {keyword}\n"
        message += f"🌍 کشور: {country.upper()} | 🗣️ زبان: {language.upper()}\n"
        message += f"📊 تعداد تبلیغات: {len(ads_found)}\n\n"
        
        for i, ad in enumerate(ads_found, 1):
            message += f"{i}. 🔗 {ad['url']}\n"
        
        # Split message if too long
        if len(message) > 4000:
            await bot.send_message(
                chat_id=chat_id,
                text=message[:4000] + "\n\n... (ادامه در پیام بعدی)"
            )
            for ad in ads_found[len(ads_found)//2:]:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"🔗 {ad['url']}"
                )
        else:
            await bot.send_message(chat_id=chat_id, text=message)
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=f"❌ هیچ تبلیغی برای کلمه کلیدی '{keyword}' پیدا نشد."
        )

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for keyword."""
    user_id = update.effective_user.id
    
    if user_id in user_waiting_input:
        input_type = user_waiting_input[user_id]
        text = update.message.text.strip()
        
        if input_type == 'keyword':
            if user_id not in user_settings:
                user_settings[user_id] = {'country': 'de', 'language': 'de', 'keyword': text, 'interval': 5, 'active': False}
            else:
                user_settings[user_id]['keyword'] = text
            
            del user_waiting_input[user_id]
            await update.message.reply_text(f"✅ کلمه کلیدی تنظیم شد: {text}")
            await start(update, context)
        return
    
    # If not waiting for input, treat as regular search
    await search_ads(update, context)

async def send_ads_list(context: ContextTypes.DEFAULT_TYPE):
    """Send list of ads for scheduled job."""
    job = context.job
    user_id = job.data['user_id']
    
    logger.info(f"Scheduled job running for user {user_id}")
    
    if user_id not in user_settings:
        logger.warning(f"User {user_id} not found in settings")
        return
    
    if not user_settings[user_id].get('active'):
        logger.info(f"Job for user {user_id} is not active, skipping")
        return
    
    settings = user_settings[user_id]
    
    logger.info(f"Executing scheduled search for user {user_id}, keyword: {settings.get('keyword')}")
    
    try:
        await execute_search(user_id, settings, context.bot)
        logger.info(f"Scheduled search completed successfully for user {user_id}")
    except Exception as e:
        logger.error(f"Error in scheduled job for user {user_id}: {e}")
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"❌ خطا در دریافت نتایج: {str(e)}"
            )
        except Exception as send_error:
            logger.error(f"Error sending error message: {send_error}")

async def search_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle keyword search and return first ad result."""
    keyword = update.message.text.strip()
    
    if not keyword:
        await update.message.reply_text('لطفاً یک کلمه کلیدی ارسال کنید.')
        return
    
    try:
        params = {
            'keyword': keyword,
            'language': 'de',
            'country': 'de',
            'device': 'iphone'
        }
        
        headers = {
            'X-Apptweak-Key': APP_TWEAK_API_KEY
        }
        
        logger.info(f"Searching for keyword: {keyword}")
        
        response = requests.get(APP_TWEAK_BASE_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'result' in data and isinstance(data['result'], list):
            for item in data['result']:
                if item.get('is_ad') == True:
                    application_id = item.get('application_id')
                    if application_id:
                        app_url = f"https://apps.apple.com/app/id{application_id}"
                        await update.message.reply_text(
                            f"✅ اولین تبلیغ پیدا شد:\n\n"
                            f"🔗 {app_url}\n\n"
                            f"📱 Application ID: {application_id}"
                        )
                        return
            
            await update.message.reply_text(
                f"❌ هیچ تبلیغی برای کلمه کلیدی '{keyword}' پیدا نشد."
            )
        else:
            await update.message.reply_text(
                "❌ پاسخ API نامعتبر است. لطفاً دوباره تلاش کنید."
            )
            
    except requests.exceptions.Timeout:
        await update.message.reply_text(
            "⏱️ درخواست به API زمان‌بر شد. لطفاً دوباره تلاش کنید."
        )
        logger.error("API request timeout")
    except requests.exceptions.RequestException as e:
        await update.message.reply_text(
            f"❌ خطا در ارتباط با API: {str(e)}"
        )
        logger.error(f"API request error: {e}")
    except Exception as e:
        await update.message.reply_text(
            f"❌ خطای غیرمنتظره: {str(e)}"
        )
        logger.error(f"Unexpected error: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log the error."""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
