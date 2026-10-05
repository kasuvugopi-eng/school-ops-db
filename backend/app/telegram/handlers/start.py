from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select, update as sql_update
from app.database import async_sessionmaker_instance
from app.models.user import User
from app.models.invite_token import InviteToken
from app.services.audit_service import log_event
from datetime import datetime, timezone

import logging
logger = logging.getLogger("uvicorn.error")

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    chat_id = str(update.effective_chat.id)
    logger.info(f"Received /start from Telegram chat_id: {chat_id}")
    await update.message.reply_text(
        f"👋 Welcome to School Ops Bot!\n\n"
        f"🆔 Your Telegram Chat ID is: `{chat_id}`\n\n"
        f"📋 Quick Setup:\n"
        f"1. Copy your Chat ID: `{chat_id}`\n"
        f"2. Paste it in your SchoolOps Web App profile page (http://localhost:3000/dashboard/profile) to connect instant alerts!\n\n"
        f"Commands:\n"
        f"/link <CODE> - Link using invite code\n"
        f"/status - View your assignment status\n"
        f"/help - Show this help"
    )

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_start(update, context)

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /link <code> command to link Telegram to web account."""
    chat_id = str(update.effective_chat.id)
    args = context.args
    
    if not args or len(args) < 1:
        await update.message.reply_text("Usage: /link <your-linking-code>\nGet your code from the web app settings.")
        return
    
    link_code = args[0].strip()
    
    async with async_sessionmaker_instance() as db:
        # Find user by invite token or linking code
        # For simplicity, we use the invite token as the linking code
        result = await db.execute(
            select(InviteToken).where(
                InviteToken.token == link_code,
                InviteToken.used_at != None  # Token must be already used (user registered)
            )
        )
        invite = result.scalar_one_or_none()
        
        if not invite or not invite.used_by:
            await update.message.reply_text("❌ Invalid or unused linking code. Please register on the web app first, then use your invite token.")
            return
        
        # Check if this chat_id is already linked to another user
        existing = await db.execute(
            select(User).where(User.telegram_chat_id == chat_id)
        )
        if existing.scalar_one_or_none():
            await update.message.reply_text("⚠️ This Telegram account is already linked to a user. Contact your admin if this is wrong.")
            return
        
        # Link the user
        await db.execute(
            sql_update(User).where(User.id == invite.used_by).values(
                telegram_chat_id=chat_id,
                telegram_linked_at=datetime.now(timezone.utc)
            )
        )
        
        # Get user info for confirmation
        user_result = await db.execute(select(User).where(User.id == invite.used_by))
        user = user_result.scalar_one()
        
        await log_event(
            db, event_type="telegram.linked",
            school_id=user.school_id, actor_id=user.id,
            details={"chat_id": chat_id}
        )
        await db.commit()
        
        await update.message.reply_text(
            f"✅ Account linked successfully!\n"
            f"Name: {user.full_name}\n"
            f"Role: {user.role.value}\n\n"
            f"You can now interact with the school system through this chat."
        )
