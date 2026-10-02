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

async def start_bot():
    global bot_app
    bot_app = create_bot_app()
    if bot_app:
        await bot_app.initialize()
        await bot_app.start()
        # Use polling for local dev (no webhook needed)
        await bot_app.updater.start_polling(drop_pending_updates=True)

async def stop_bot():
    global bot_app
    if bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
