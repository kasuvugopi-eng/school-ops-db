from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from app.database import async_sessionmaker_instance
from app.models.user import User
from app.models.submission import Submission
from app.models.assignment import Assignment
from app.models.enums import SubmissionState, AssignmentState
from app.services.submission_service import update_submission_state
from app.services.audit_service import log_event
from app.websocket.events import emit_submission_update

async def resolve_user(chat_id: str, db):
    result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
    return result.scalar_one_or_none()

async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show student's assignment status."""
    chat_id = str(update.effective_chat.id)
    
    async with async_sessionmaker_instance() as db:
        user = await resolve_user(chat_id, db)
        if not user:
            await update.message.reply_text("⚠️ Account not linked. Use /link <CODE> first.")
            return
        
        # Get active submissions
        result = await db.execute(
            select(Submission, Assignment)
            .join(Assignment, Submission.assignment_id == Assignment.id)
            .where(
                Submission.student_id == user.id,
                Assignment.state == AssignmentState.ACTIVE
            )
        )
        rows = result.all()
        
        if not rows:
            await update.message.reply_text("📚 No active assignments right now. Enjoy! 🎉")
            return
        
        status_lines = ["📚 *Your Active Assignments:*\n"]
        for sub, assign in rows:
            state_emoji = {
                SubmissionState.NOT_STARTED: "⬜",
                SubmissionState.IN_PROGRESS: "🔵",
                SubmissionState.BLOCKED: "🔴",
                SubmissionState.SUBMITTED: "🟢",
                SubmissionState.REVISION_REQUESTED: "🟡",
                SubmissionState.RESUBMITTED: "🟣",
                SubmissionState.COMPLETED: "✅",
            }.get(sub.state, "⬜")
            
            due = f" (Due: {assign.due_date.strftime('%b %d')}" if assign.due_date else ""
            if due:
                from datetime import datetime, timezone
                if assign.due_date < datetime.now(timezone.utc):
                    due += " ⚠️ OVERDUE"
                due += ")"
            
            status_lines.append(f"{state_emoji} *{assign.title}*{due}")
            status_lines.append(f"   Status: {sub.state.value.replace('_', ' ').title()}\n")
        
        await update.message.reply_text("\n".join(status_lines), parse_mode="Markdown")

async def handle_file_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo or file submission from student."""
    chat_id = str(update.effective_chat.id)
    
    async with async_sessionmaker_instance() as db:
        user = await resolve_user(chat_id, db)
        if not user:
            await update.message.reply_text("⚠️ Account not linked. Use /link <CODE> first.")
            return
        
        # Find the student's most recent active assignment with a non-completed submission
        result = await db.execute(
            select(Submission, Assignment)
            .join(Assignment, Submission.assignment_id == Assignment.id)
            .where(
                Submission.student_id == user.id,
                Assignment.state == AssignmentState.ACTIVE,
                Submission.state.in_([
                    SubmissionState.NOT_STARTED,
                    SubmissionState.IN_PROGRESS,
                    SubmissionState.BLOCKED,
                    SubmissionState.REVISION_REQUESTED
                ])
            )
            .order_by(Assignment.due_date.asc().nulls_last())
            .limit(1)
        )
        row = result.first()
        
        if not row:
            await update.message.reply_text("📭 No pending assignments to submit to. Check /status for details.")
            return
        
        sub, assign = row
        caption = update.message.caption or "Submitted via Telegram"
        
        await update.message.reply_text("⏳ Received your file. Parsing and extracting text for review...")

        import tempfile
        import os
        import base64
        from app.agents.llm_factory import LLMFactory

        file_obj = None
        mime_type = ""
        try:
            if update.message.photo:
                photo = update.message.photo[-1]
                file_obj = await photo.get_file()
                mime_type = "image/jpeg"
            elif update.message.document:
                file_obj = await update.message.document.get_file()
                mime_type = update.message.document.mime_type or "application/octet-stream"
            elif update.message.voice:
                file_obj = await update.message.voice.get_file()
                mime_type = update.message.voice.mime_type or "audio/ogg"
            elif update.message.audio:
                file_obj = await update.message.audio.get_file()
                mime_type = update.message.audio.mime_type or "audio/mpeg"
        except Exception as e:
            print(f"Error getting file object: {e}")

        extracted_text = f"[{caption}]"
        if file_obj:
            try:
                with tempfile.NamedTemporaryFile(delete=False) as tf:
                    temp_path = tf.name
                
                await file_obj.download_to_drive(custom_path=temp_path)
                
                if mime_type.startswith("image/"):
                    with open(temp_path, "rb") as f:
                        b64_img = base64.b64encode(f.read()).decode("utf-8")
                    
                    parsed = LLMFactory.generate_text(
                        prompt="Please transcribe the content of this image, extracting any handwritten or typed text related to the assignment. If it's a photo of work, describe it clearly.",
                        image_b64=b64_img,
                        mime_type=mime_type
                    )
                    extracted_text = f"[Image Parsed Context]\n{parsed}\n\n[Original Caption]: {caption}"
                elif mime_type.startswith("audio/") or mime_type.startswith("video/") or "ogg" in mime_type:
                    with open(temp_path, "rb") as f:
                        b64_audio = base64.b64encode(f.read()).decode("utf-8")
                    parsed = LLMFactory.generate_text(
                        prompt="Please carefully transcribe this audio message.",
                        image_b64=b64_audio,
                        mime_type=mime_type
                    )
                    extracted_text = f"[Audio Transcribed Context]\n{parsed}\n\n[Original Caption]: {caption}"
                else:
                    from app.agents.document_parser import extract_text as doc_extract
                    raw_text = doc_extract(temp_path, mime_type)
                    parsed = LLMFactory.generate_text(
                        prompt=f"Please summarize and clean up this assignment submission text:\n\n{raw_text}",
                    )
                    extracted_text = f"[Document Parsed Context]\n{parsed}\n\n[Original Caption]: {caption}"
                
                os.unlink(temp_path)
            except Exception as e:
                print(f"Failed to extract file: {e}")
                extracted_text = f"[{caption}] - (Failed to parse attached file: {e})"
        
        # Update submission state
        new_state = SubmissionState.RESUBMITTED if sub.state == SubmissionState.REVISION_REQUESTED else SubmissionState.SUBMITTED
        sub = await update_submission_state(
            db, sub.id, new_state,
            content_text=extracted_text
        )
        
        await log_event(
            db, event_type="submission.submitted_telegram",
            school_id=assign.school_id, actor_id=user.id,
            resource_type="submission", resource_id=sub.id
        )
        await db.commit()
        
        await emit_submission_update(str(assign.school_id), {
            "submission_id": str(sub.id),
            "student_id": str(user.id),
            "student_name": user.full_name,
            "assignment_id": str(assign.id),
            "assignment_title": assign.title,
            "state": sub.state.value
        })
        
        await update.message.reply_text(
            f"✅ Work submitted for *{assign.title}*!\n"
            f"Your teacher will review it soon.",
            parse_mode="Markdown"
        )
