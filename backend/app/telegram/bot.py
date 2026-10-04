from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.config import settings

bot_app = None

def create_bot_app() -> Application | None:
    """Create the bot application. Returns None if token not configured."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    from app.telegram.handlers import start, student, teacher, fallback
    
    # Command handlers
    app.add_handler(CommandHandler("start", start.handle_start))
    app.add_handler(CommandHandler("link", start.handle_link))
    app.add_handler(CommandHandler("status", student.handle_status))
    app.add_handler(CommandHandler("help", start.handle_help))
    
    # Natural language message handler
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        fallback.handle_message
    ))
    
    # Photo/document handler
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        student.handle_file_submission
    ))
    
    return app

import logging
logger = logging.getLogger("uvicorn.error")

async def start_bot(app=None):
    global bot_app
    bot_app = create_bot_app()
    if not bot_app:
        logger.warning("TELEGRAM_BOT_TOKEN is empty. Skipping Telegram bot.")
        return
        
    await bot_app.initialize()
    await bot_app.start()
    
    webhook_route_exists = False
    if app:
        webhook_route_exists = any("webhook" in getattr(r, "path", "").lower() for r in app.routes)
        
    if settings.TELEGRAM_WEBHOOK_URL and webhook_route_exists:
        await bot_app.bot.set_webhook(
            url=settings.TELEGRAM_WEBHOOK_URL,
            secret_token=settings.TELEGRAM_SECRET_TOKEN
        )
    else:
        await bot_app.updater.start_polling(drop_pending_updates=True)

async def stop_bot():
    global bot_app
    if bot_app:
        if bot_app.updater and bot_app.updater.running:
            await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

async def send_telegram_message(chat_id: str, text: str):
    global bot_app
    if bot_app and bot_app.bot:
        try:
            await bot_app.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send telegram message to {chat_id}: {e}")
