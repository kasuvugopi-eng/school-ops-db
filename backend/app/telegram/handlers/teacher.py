import uuid
import os
import tempfile
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from app.database import async_sessionmaker_instance
from app.models.user import User
from app.models.grade_class import GradeClass
from app.models.enums import UserRole, AssignmentTargetType, AssignmentState
from app.agents.document_parser import parse_assignment_document, extract_text
from app.services.assignment_service import create_assignment

TEACHER_DRAFTS = {}

async def process_teacher_assignment_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, raw_text: str = None, file_path: str = None, mime_type: str = None):
    chat_id = str(update.effective_chat.id)
    
    # 1. If currently in an interactive dialogue step:
    if chat_id in TEACHER_DRAFTS:
        draft = TEACHER_DRAFTS[chat_id]
        user_input = (update.message.text or "").strip()
        
        if user_input.lower() in ["cancel", "stop", "exit"]:
            del TEACHER_DRAFTS[chat_id]
            await update.message.reply_text("❌ Assignment creation cancelled.")
            return

        step = draft.get("step")
        
        async with async_sessionmaker_instance() as db:
            # STEP: SELECT_CLASS
            if step == "SELECT_CLASS":
                classes = draft["classes"]
                selected_class = None
                
                if user_input.isdigit():
                    idx = int(user_input) - 1
                    if 0 <= idx < len(classes):
                        selected_class = classes[idx]
                    elif idx == len(classes): # 'All Classes' option
                        selected_class = "ALL"
                else:
                    # Match by name string
                    for c in classes:
                        if c.name.lower() in user_input.lower() or (c.grade_level and c.grade_level.lower() in user_input.lower()):
                            selected_class = c
                            break
                            
                if not selected_class:
                    await update.message.reply_text("⚠️ Invalid selection. Please reply with the number corresponding to your choice.")
                    return
                    
                draft["selected_class"] = selected_class
                
                # Check if due date is needed
                if not draft["parsed"].due_date:
                    draft["step"] = "CONFIRM_DUE_DATE"
                    default_due = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
                    draft["suggested_due"] = default_due
                    await update.message.reply_text(
                        f"📅 *Due Date missing.*\n"
                        f"Shall I set the due date to 1 week from now (*{default_due}*)?\n\n"
                        f"• Reply *'ok'* to accept\n"
                        f"• Or type your own date (e.g. `2026-10-15 18:00`)",
                        parse_mode="Markdown"
                    )
                    return
                else:
                    draft["step"] = "CONFIRM_APPROVAL"
                    await show_approval_summary(update, draft)
                    return

            # STEP: CONFIRM_DUE_DATE
            elif step == "CONFIRM_DUE_DATE":
                if user_input.lower() in ["ok", "yes", "y", "sure"]:
                    draft["parsed"].due_date = draft["suggested_due"]
                else:
                    draft["parsed"].due_date = user_input
                    
                draft["step"] = "CONFIRM_APPROVAL"
                await show_approval_summary(update, draft)
                return

            # STEP: CONFIRM_APPROVAL
            elif step == "CONFIRM_APPROVAL":
                if user_input.lower() in ["approve", "ok", "yes", "publish", "confirm"]:
                    selected_class = draft["selected_class"]
                    parsed = draft["parsed"]
                    
                    # Parse due date
                    due_dt = None
                    if parsed.due_date:
                        try:
                            if "T" in parsed.due_date:
                                due_dt = datetime.fromisoformat(parsed.due_date)
                            else:
                                due_dt = datetime.strptime(parsed.due_date, "%Y-%m-%d %H:%M")
                        except Exception:
                            due_dt = datetime.now(timezone.utc) + timedelta(days=7)
                    else:
                        due_dt = datetime.now(timezone.utc) + timedelta(days=7)
                        
                    target_class_id = selected_class.id if hasattr(selected_class, 'id') else classes[0].id
                    
                    assignment_data = {
                        "title": parsed.title or "New Assignment",
                        "subject": parsed.subject or "General",
                        "instructions": parsed.instructions or raw_text or "See details",
                        "due_date": due_dt,
                        "target_type": AssignmentTargetType.CLASS,
                        "state": AssignmentState.ACTIVE
                    }
                    
                    created = await create_assignment(db, assignment_data, target_class_id, user)
                    
                    target_name = selected_class.name if hasattr(selected_class, 'name') else "Selected Class"
                    await update.message.reply_text(
                        f"🎉 *Assignment Published Successfully!*\n\n"
                        f"📌 *Title*: {created.title}\n"
                        f"🎯 *Target*: {target_name}\n"
                        f"🔔 Notifications have been sent to all enrolled students via Telegram!",
                        parse_mode="Markdown"
                    )
                    del TEACHER_DRAFTS[chat_id]
                    return
                else:
                    del TEACHER_DRAFTS[chat_id]
                    await update.message.reply_text("❌ Assignment creation cancelled.")
                    return

    # 2. Starting a NEW draft assignment (Text message or Document upload)
    await update.message.reply_text("🔍 Analyzing document/assignment text with AI... Please wait.")
    
    extracted_text = ""
    if file_path:
        extracted_text = extract_text(file_path, mime_type or "text/plain")
    else:
        extracted_text = raw_text or ""

    parsed = await parse_assignment_document(extracted_text)
    
    async with async_sessionmaker_instance() as db:
        # Fetch school classes
        cls_result = await db.execute(select(GradeClass).where(GradeClass.school_id == user.school_id))
        classes = cls_result.scalars().all()
        
        if not classes:
            await update.message.reply_text("⚠️ No classes found in your school. Please ask an Admin to create classes first.")
            return

        draft = {
            "parsed": parsed,
            "classes": classes,
            "raw_text": extracted_text,
            "step": "SELECT_CLASS"
        }
        TEACHER_DRAFTS[chat_id] = draft

        # Show Class Selection Menu
        menu_text = f"📋 *AI Parsed Assignment Details:*\n"
        menu_text += f"• *Title*: {parsed.title or 'Not specified'}\n"
        menu_text += f"• *Subject*: {parsed.subject or 'Not specified'}\n"
        menu_text += f"• *Due Date*: {parsed.due_date or 'Not specified'}\n\n"
        menu_text += f"👉 *Select Target Class:* Reply with the number:\n"
        
        for idx, c in enumerate(classes, 1):
            grade_str = f"Grade {c.grade_level} - " if c.grade_level else ""
            menu_text += f"*{idx}.* {grade_str}{c.name}\n"
            
        menu_text += f"\n_(Type 'cancel' to abort at any time)_"
        
        await update.message.reply_text(menu_text, parse_mode="Markdown")

async def show_approval_summary(update: Update, draft: dict):
    parsed = draft["parsed"]
    sel_class = draft["selected_class"]
    class_name = sel_class.name if hasattr(sel_class, 'name') else "All Classes"
    grade_str = f"Grade {sel_class.grade_level} - " if hasattr(sel_class, 'grade_level') and sel_class.grade_level else ""

    summary = (
        f"📝 *Final Assignment Preview*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Title*: {parsed.title or 'Untitled Assignment'}\n"
        f"📚 *Subject*: {parsed.subject or 'General'}\n"
        f"🎯 *Target Class*: {grade_str}{class_name}\n"
        f"⏰ *Due Date*: {parsed.due_date}\n"
        f"📄 *Instructions*: {parsed.instructions or 'None'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Reply *'approve'* to publish to students, or *'cancel'* to abort."
    )
    await update.message.reply_text(summary, parse_mode="Markdown")

async def handle_teacher_file(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User):
    """Handle photo or document uploaded by a Teacher."""
    document = update.message.document
    photo = update.message.photo
    
    file_obj = None
    file_name = "uploaded_file"
    mime_type = "image/jpeg"
    
    if document:
        file_obj = await document.get_file()
        file_name = document.file_name or "uploaded_doc"
        mime_type = document.mime_type or "text/plain"
    elif photo:
        file_obj = await photo[-1].get_file()
        file_name = "uploaded_photo.jpg"
        mime_type = "image/jpeg"

    if file_obj:
        # Save file to temp folder
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file_name}")
        await file_obj.download_to_drive(file_path)
        
        caption = update.message.caption or ""
        await process_teacher_assignment_flow(update, context, user, raw_text=caption, file_path=file_path, mime_type=mime_type)

async def handle_cancel_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel_assignment command for teachers."""
    chat_id = str(update.effective_chat.id)
    args = context.args
    from app.telegram.handlers.fallback import resolve_user
    from app.models.assignment import Assignment
    from app.services.assignment_service import update_assignment_state

    async with async_sessionmaker_instance() as db:
        user = await resolve_user(chat_id, db)
        if not user or user.role != UserRole.TEACHER:
            await update.message.reply_text("⚠️ Only teachers can cancel assignments.")
            return

        target_assignment = None
        if args:
            asgn_id_str = args[0].strip()
            try:
                asgn_id = uuid.UUID(asgn_id_str)
                res = await db.execute(select(Assignment).where(Assignment.id == asgn_id, Assignment.created_by == user.id))
                target_assignment = res.scalar_one_or_none()
            except ValueError:
                pass

        if not target_assignment:
            # Pick the most recent active or draft assignment created by this teacher
            res = await db.execute(
                select(Assignment)
                .where(Assignment.created_by == user.id, Assignment.state.in_([AssignmentState.ACTIVE, AssignmentState.DRAFT]))
                .order_by(Assignment.created_at.desc())
                .limit(1)
            )
            target_assignment = res.scalar_one_or_none()

        if not target_assignment:
            await update.message.reply_text("⚠️ No active assignment found to cancel.")
            return

        try:
            await update_assignment_state(db, target_assignment.id, AssignmentState.CANCELLED, user)
            await update.message.reply_text(
                f"❌ *Assignment Cancelled Successfully!*\n\n"
                f"📌 *Title*: {target_assignment.title}\n\n"
                f"🔔 Enrolled students have been notified of the cancellation via Telegram.",
                parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Failed to cancel assignment: {e}")
