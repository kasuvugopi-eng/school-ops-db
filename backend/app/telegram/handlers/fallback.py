from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from app.database import async_sessionmaker_instance
from app.models.user import User
from app.models.submission import Submission
from app.models.assignment import Assignment
from app.models.enums import SubmissionState, AssignmentState, UserRole
from app.agents.intent_engine import classify_intent
from app.services.submission_service import update_submission_state
from app.services.audit_service import log_event
from app.websocket.events import emit_submission_update, emit_student_blocked
import datetime

TEACHER_DRAFTS = {}

async def resolve_user(chat_id: str, db):
    result = await db.execute(select(User).where(User.telegram_chat_id == chat_id))
    return result.scalar_one_or_none()

async def get_active_submission(db, user_id):
    """Get the student's most urgent active submission."""
    result = await db.execute(
        select(Submission, Assignment)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .where(
            Submission.student_id == user_id,
            Assignment.state == AssignmentState.ACTIVE,
            Submission.state.notin_([
                SubmissionState.COMPLETED,
                SubmissionState.SUBMITTED,
                SubmissionState.RESUBMITTED
            ])
        )
        .order_by(Assignment.due_date.asc().nulls_last())
        .limit(1)
    )
    return result.first()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route natural language messages through intent engine."""
    chat_id = str(update.effective_chat.id)
    message_text = update.message.text
    
    async with async_sessionmaker_instance() as db:
        user = await resolve_user(chat_id, db)
        if not user:
            await update.message.reply_text(
                "⚠️ Your account is not linked. Use /link <CODE> to connect your school account."
            )
            return
        
        # Classify intent
        intent = await classify_intent(message_text, user.role.value)
        
        # Log the message
        from app.models.chat_message import ChatMessage
        chat_msg = ChatMessage(
            telegram_chat_id=chat_id,
            user_id=user.id,
            direction="inbound",
            raw_text=message_text,
            detected_intent=intent.intent,
            intent_confidence=intent.confidence
        )
        db.add(chat_msg)
        
        # Route based on user role and intent
        from app.telegram.handlers.teacher import process_teacher_assignment_flow, TEACHER_DRAFTS
        
        if user.role == UserRole.TEACHER:
            await process_teacher_assignment_flow(update, context, user, raw_text=message_text)
            return

        if intent.intent == "progress_update":
            row = await get_active_submission(db, user.id)
            if row:
                sub, assign = row
                if sub.state == SubmissionState.NOT_STARTED:
                    sub = await update_submission_state(db, sub.id, SubmissionState.IN_PROGRESS)
                await log_event(db, event_type="submission.progress_update",
                    school_id=assign.school_id, actor_id=user.id,
                    resource_type="submission", resource_id=sub.id,
                    details={"message": message_text})
                await db.commit()
                await emit_submission_update(str(assign.school_id), {
                    "submission_id": str(sub.id), "student_name": user.full_name,
                    "assignment_title": assign.title, "state": sub.state.value
                })
                await update.message.reply_text(f"📝 Progress noted for *{assign.title}*. Keep going!", parse_mode="Markdown")
            else:
                await update.message.reply_text("No active assignments found to update.")
        
        elif intent.intent == "blocked_request":
            row = await get_active_submission(db, user.id)
            if row:
                sub, assign = row
                sub = await update_submission_state(
                    db, sub.id, SubmissionState.BLOCKED,
                    blocked_reason=message_text
                )
                await log_event(db, event_type="submission.blocked",
                    school_id=assign.school_id, actor_id=user.id,
                    resource_type="submission", resource_id=sub.id,
                    details={"reason": message_text})
                await db.commit()
                await emit_student_blocked(str(assign.school_id), {
                    "submission_id": str(sub.id), "student_name": user.full_name,
                    "assignment_title": assign.title, "reason": message_text
                })
                await update.message.reply_text(
                    f"🆘 I've notified your teacher that you're stuck on *{assign.title}*.\n"
                    f"They'll get back to you soon!", parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("No active assignments found.")
        
        elif intent.intent == "submission":
            row = await get_active_submission(db, user.id)
            if row:
                sub, assign = row
                new_state = SubmissionState.SUBMITTED
                sub = await update_submission_state(
                    db, sub.id, new_state,
                    content_text=message_text
                )
                await log_event(db, event_type="submission.submitted_telegram",
                    school_id=assign.school_id, actor_id=user.id,
                    resource_type="submission", resource_id=sub.id)
                await db.commit()
                await emit_submission_update(str(assign.school_id), {
                    "submission_id": str(sub.id), "student_name": user.full_name,
                    "assignment_title": assign.title, "state": sub.state.value
                })
                await update.message.reply_text(
                    f"✅ Work submitted for *{assign.title}*!\nYour teacher will review it.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("No pending assignments to submit to.")
        
        elif intent.intent == "parent_opt_in":
            if user.role == UserRole.GUARDIAN:
                from app.models.guardian_link import GuardianLink
                from datetime import datetime, timezone
                links_result = await db.execute(
                    select(GuardianLink).where(GuardianLink.guardian_id == user.id)
                )
                links = links_result.scalars().all()
                for link in links:
                    link.opted_in = True
                    link.opted_in_at = datetime.now(timezone.utc)
                await db.commit()
                await update.message.reply_text("✅ You've opted in to receive progress updates for your child(ren).")
            else:
                await update.message.reply_text("This action is only available for parents/guardians.")
        
        elif intent.intent in ("unsafe", "out_of_scope"):
            await db.commit()
            if intent.intent == "unsafe":
                await update.message.reply_text("⚠️ I can't process that request. Please keep messages related to school work.")
            else:
                await update.message.reply_text(
                    "🤔 I'm not sure how to help with that. I can help with:\n"
                    "- Assignment progress updates\n"
                    "- Reporting that you're stuck\n"
                    "- Submitting work\n"
                    "- Checking your status (/status)"
                )
        
        else:  # unknown or other intents
            await db.commit()
            await update.message.reply_text(
                f"I understood your message as: *{intent.intent.replace('_', ' ').title()}*\n"
                f"For this action, please use the web dashboard at the school portal.",
                parse_mode="Markdown"
            )
