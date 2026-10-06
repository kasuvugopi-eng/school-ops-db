from telegram.ext import Application, CommandHandler, MessageHandler, filters
from app.config import settings

bot_app = None

def create_bot_app() -> Application | None:
    """Create the bot application. Returns None if token not configured."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    from app.telegram.handlers import start, student, teacher, fallback
    
    from telegram.ext import CallbackQueryHandler
    
    # Command handlers
    app.add_handler(CommandHandler("start", start.handle_start))
    app.add_handler(CommandHandler("link", start.handle_link))
    app.add_handler(CommandHandler("status", student.handle_status))
    app.add_handler(CommandHandler("help", start.handle_help))
    app.add_handler(CommandHandler("cancel_assignment", teacher.handle_cancel_assignment))
    app.add_handler(CommandHandler("cancel", teacher.handle_cancel_assignment))

    # Inline button callback handler
    app.add_handler(CallbackQueryHandler(teacher.handle_callback_query))
    
    # Natural language message handler
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        fallback.handle_message
    ))
    
    async def handle_media_upload(update, context):
        from app.telegram.handlers.fallback import resolve_user
        from app.database import async_sessionmaker_instance
        from app.models.enums import UserRole
        from app.telegram.handlers import student, teacher
        
        chat_id = str(update.effective_chat.id)
        async with async_sessionmaker_instance() as db:
            user = await resolve_user(chat_id, db)
            if not user:
                await update.message.reply_text("⚠️ Your account is not linked. Use /link <CODE> to connect your school account.")
                return
            if user.role == UserRole.TEACHER:
                await teacher.handle_teacher_file(update, context, user)
            else:
                await student.handle_file_submission(update, context)

    # Photo/document/voice note/audio handler
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL | filters.VOICE | filters.AUDIO,
        handle_media_upload
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
        await bot_app.updater.start_polling(drop_pending_updates=False)
        logger.info("🤖 Telegram bot polling started successfully for @school_ops_tetris_bot.")

async def stop_bot():
    global bot_app
    if bot_app:
        if bot_app.updater and bot_app.updater.running:
            await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

async def send_telegram_message(chat_id: str, text: str, reply_markup=None):
    global bot_app
    bot_instance = bot_app.bot if (bot_app and bot_app.bot) else None
    if not bot_instance and settings.TELEGRAM_BOT_TOKEN:
        from telegram import Bot
        bot_instance = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        
    if bot_instance:
        try:
            await bot_instance.send_message(chat_id=chat_id, text=text, parse_mode="Markdown", reply_markup=reply_markup)
            logger.info(f"Successfully sent Telegram notification to chat_id {chat_id}")
        except Exception as e:
            # Fallback without Markdown if markdown parsing fails
            try:
                await bot_instance.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
                logger.info(f"Successfully sent Telegram notification (plain text) to chat_id {chat_id}")
            except Exception as ex:
                logger.error(f"Failed to send telegram message to {chat_id}: {ex}")
