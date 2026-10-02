from telegram import Update
from telegram.ext import ContextTypes

async def handle_teacher_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle teacher messages (feedback, approvals via Telegram)."""
    await update.message.reply_text(
        "📋 For detailed assignment management, please use the web dashboard.\n"
        "Quick actions available via chat:\n"
        "- Reply to student notifications to send feedback\n"
    )
