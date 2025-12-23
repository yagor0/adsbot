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

APP_TWEAK_BASE_URL = 'https://public-api.apptweak.com/api/public/store/keywords/search-results/ads/current'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        'سلام! این بات برای جستجوی تبلیغات اپلیکیشن‌ها در App Store استفاده می‌شود.\n\n'
        'برای استفاده، یک کلمه کلیدی را ارسال کنید.\n\n'
        'مثال: ki video erstellen'
    )

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test command with default keyword."""
    keyword = ' '.join(context.args) if context.args else 'ki video erstellen'
    
    # Create a message-like object for search_ads
    class FakeMessage:
        def __init__(self, text):
            self.text = text
    
    # Temporarily replace the message
    original_message = update.message
    update.message = FakeMessage(keyword)
    
    try:
        await search_ads(update, context)
    finally:
        update.message = original_message

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
    application.add_handler(CommandHandler("test", test))
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

