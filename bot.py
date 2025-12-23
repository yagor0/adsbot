import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
CHANNEL_ID = os.getenv('CHANNEL_ID', '-1003626600006')  # Channel ID for sending messages

APP_TWEAK_BASE_URL = 'https://public-api.apptweak.com/api/public/store/keywords/search-results/ads/current'

# Storage for user settings (in production, use a database)
user_settings = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    
    if user_id in user_settings and user_settings[user_id].get('active'):
        await update.message.reply_text(
            '✅ کار تکراری در حال اجرا است!\n\n'
            f"⏰ فاصله زمانی: هر {user_settings[user_id]['interval']} دقیقه\n"
            f"🌍 کشور: {user_settings[user_id]['country']}\n"
            f"🗣️ زبان: {user_settings[user_id]['language']}\n"
            f"🔍 کلمه کلیدی: {user_settings[user_id]['keyword']}\n\n"
            'برای توقف از /stop استفاده کنید.'
        )
    else:
        await update.message.reply_text(
            'سلام! این بات برای جستجوی خودکار تبلیغات اپلیکیشن‌ها استفاده می‌شود.\n\n'
            '📋 ابتدا باید تنظیمات را انجام دهید:\n'
            'از دستور /setup استفاده کنید.\n\n'
            'فرمت:\n'
            '/setup <کلمه_کلیدی> <کشور> <زبان> <فاصله_زمانی_دقیقه>\n\n'
            'مثال:\n'
            '/setup "ki video erstellen" de de 5'
        )

async def setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Setup recurring job with keyword, country, language, and interval."""
    user_id = update.effective_user.id
    
    if not context.args or len(context.args) < 4:
        await update.message.reply_text(
            '❌ فرمت دستور اشتباه است!\n\n'
            'فرمت صحیح:\n'
            '/setup <کلمه_کلیدی> <کشور> <زبان> <فاصله_زمانی_دقیقه>\n\n'
            'مثال:\n'
            '/setup ki video erstellen de de 5\n\n'
            'یعنی هر 5 دقیقه برای کلمه "ki video erstellen" در کشور آلمان (de) و زبان آلمانی (de) جستجو کند.\n\n'
            '⚠️ توجه: کلمه کلیدی می‌تواند چند کلمه باشد (بدون کوتیشن)'
        )
        return
    
    try:
        # Parse arguments - keyword can be multiple words
        # Last 3 args are: country, language, interval
        # Everything before that is the keyword
        if len(context.args) >= 4:
            # Get interval (last argument)
            try:
                interval = int(context.args[-1])
            except ValueError:
                await update.message.reply_text('❌ فاصله زمانی باید یک عدد باشد!')
                return
            
            # Get country and language (second and third from last)
            country = context.args[-3].lower().strip('"\'')
            language = context.args[-2].lower().strip('"\'')
            
            # Everything else is the keyword
            keyword_parts = context.args[:-3]
            keyword = ' '.join(keyword_parts).strip('"\'')
        else:
            await update.message.reply_text(
                '❌ فرمت دستور اشتباه است!\n\n'
                'فرمت صحیح:\n'
                '/setup <کلمه_کلیدی> <کشور> <زبان> <فاصله_زمانی_دقیقه>'
            )
            return
        
        if interval < 1:
            await update.message.reply_text('❌ فاصله زمانی باید حداقل 1 دقیقه باشد!')
            return
        
        # Save settings
        user_settings[user_id] = {
            'keyword': keyword,
            'country': country,
            'language': language,
            'interval': interval,
            'active': True,
            'chat_id': CHANNEL_ID  # Use channel ID instead of user chat
        }
        
        # Remove existing job if any
        job_name = f"ads_job_{user_id}"
        if job_name in [job.name for job in context.application.job_queue.jobs()]:
            context.application.job_queue.get_jobs_by_name(job_name)[0].schedule_removal()
        
        # Create new recurring job
        context.application.job_queue.run_repeating(
            send_ads_list,
            interval=interval * 60,  # Convert minutes to seconds
            first=10,  # Start after 10 seconds
            name=job_name,
            data={'user_id': user_id}
        )
        
        await update.message.reply_text(
            f'✅ تنظیمات با موفقیت انجام شد!\n\n'
            f'🔍 کلمه کلیدی: {keyword}\n'
            f'🌍 کشور: {country}\n'
            f'🗣️ زبان: {language}\n'
            f'⏰ فاصله زمانی: هر {interval} دقیقه\n'
            f'📢 چنل: ADS (ID: {CHANNEL_ID})\n\n'
            f'کار تکراری شروع شد! پیام‌ها به چنل ارسال می‌شوند.\n'
            f'اولین نتیجه بعد از 10 ثانیه ارسال می‌شود.'
        )
        
        logger.info(f"User {user_id} setup: keyword={keyword}, country={country}, language={language}, interval={interval}min")
        
    except ValueError:
        await update.message.reply_text('❌ فاصله زمانی باید یک عدد باشد!')
    except Exception as e:
        await update.message.reply_text(f'❌ خطا در تنظیمات: {str(e)}')
        logger.error(f"Setup error: {e}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the recurring job."""
    user_id = update.effective_user.id
    
    if user_id not in user_settings or not user_settings[user_id].get('active'):
        await update.message.reply_text('❌ هیچ کار تکراری فعالی وجود ندارد!')
        return
    
    # Remove job
    job_name = f"ads_job_{user_id}"
    jobs = context.application.job_queue.get_jobs_by_name(job_name)
    if jobs:
        jobs[0].schedule_removal()
    
    user_settings[user_id]['active'] = False
    
    await update.message.reply_text('✅ کار تکراری متوقف شد!')

async def send_ads_list(context: ContextTypes.DEFAULT_TYPE):
    """Send list of ads for scheduled job."""
    job = context.job
    user_id = job.data['user_id']
    
    if user_id not in user_settings or not user_settings[user_id].get('active'):
        return
    
    settings = user_settings[user_id]
    keyword = settings['keyword']
    country = settings['country']
    language = settings['language']
    chat_id = settings['chat_id']
    
    try:
        # Prepare API request parameters
        params = {
            'keyword': keyword,
            'language': language,
            'country': country,
            'device': 'iphone'
        }
        
        headers = {
            'X-Apptweak-Key': APP_TWEAK_API_KEY
        }
        
        logger.info(f"Job running for user {user_id}: keyword={keyword}")
        
        # Make API request
        response = requests.get(APP_TWEAK_BASE_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Find all ad results
        ads_found = []
        if 'result' in data and isinstance(data['result'], list):
            for item in data['result']:
                if item.get('is_ad') == True:
                    application_id = item.get('application_id')
                    if application_id:
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
            
            # Send in chunks if too many
            for i, ad in enumerate(ads_found, 1):
                message += f"{i}. 🔗 {ad['url']}\n"
            
            # Split message if too long (Telegram limit is 4096 chars)
            if len(message) > 4000:
                # Send first part
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message[:4000] + "\n\n... (ادامه در پیام بعدی)"
                )
                # Send remaining ads
                remaining = message[4000:]
                for ad in ads_found[len(ads_found)//2:]:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"🔗 {ad['url']}"
                    )
            else:
                await context.bot.send_message(chat_id=chat_id, text=message)
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ هیچ تبلیغی برای کلمه کلیدی '{keyword}' پیدا نشد."
            )
            
    except Exception as e:
        logger.error(f"Error in scheduled job for user {user_id}: {e}")
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"❌ خطا در دریافت نتایج: {str(e)}"
            )
        except Exception as send_error:
            logger.error(f"Error sending error message to channel: {send_error}")

async def search_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle keyword search and return first ad result."""
    keyword = update.message.text.strip()
    
    if not keyword:
        await update.message.reply_text('لطفاً یک کلمه کلیدی ارسال کنید.')
        return
    
    try:
        # Prepare API request parameters
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
        
        # Make API request
        response = requests.get(APP_TWEAK_BASE_URL, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Find first ad result
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
            
            # No ad found
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
    """Log the error and send a telegram message to notify the developer."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید."
        )

def main():
    """Start the bot."""
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setup", setup))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_ads))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Bot is starting...")
    port = int(os.getenv('PORT', 8000))
    
    # For Railway deployment, use webhook or polling
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # Use polling for Railway (or set up webhook if you have a domain)
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    else:
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

