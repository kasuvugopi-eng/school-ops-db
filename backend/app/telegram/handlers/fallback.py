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
        
        # Route based on intent
        if chat_id in TEACHER_DRAFTS:
            # Handle conversational reply for draft assignment
            draft = TEACHER_DRAFTS[chat_id]
            if message_text.lower() in ["cancel", "stop"]:
                del TEACHER_DRAFTS[chat_id]
                await update.message.reply_text("Assignment creation cancelled.")
                return
                
            if draft.get("state") == "WAITING_DUE_DATE":
                # User replied to due date question
                if "ok" in message_text.lower() or "yes" in message_text.lower():
                    from datetime import datetime, timedelta, timezone
                    draft["parsed"].due_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                else:
                    # They provided a specific date string, but for simplicity let's assume they just gave a date
                    draft["parsed"].due_date = message_text
                
                draft["state"] = "WAITING_APPROVAL"
                await update.message.reply_text(
                    f"Got it! Due date set to: {draft['parsed'].due_date}\n\n"
                    f"Title: {draft['parsed'].title}\n"
                    f"Subject: {draft['parsed'].subject}\n"
                    f"Instructions: {draft['parsed'].instructions}\n\n"
                    f"Shall I approve and send this to the students? (Reply 'approve' or 'cancel')"
                )
                return
                
            elif draft.get("state") == "WAITING_APPROVAL":
                if "approve" in message_text.lower() or "ok" in message_text.lower():
                    # Create assignment
                    from app.services.assignment_service import create_assignment
                    from app.models.enums import AssignmentTargetType
                    import uuid
                    
                    # Fetch a class to assign it to if target_class_id is missing
                    target_class_id = draft["parsed"].target_class_id
                    if not target_class_id:
                        from app.models.grade_class import GradeClass
                        cls_result = await db.execute(select(GradeClass).where(GradeClass.school_id == user.school_id).limit(1))
                        first_class = cls_result.scalar_one_or_none()
                        if first_class:
                            target_class_id = first_class.id
                        else:
                            await update.message.reply_text("Error: No classes found in school to assign to.")
                            del TEACHER_DRAFTS[chat_id]
                            return
                    else:
                        try:
                            target_class_id = uuid.UUID(target_class_id)
                        except ValueError:
                            # Match by name
                            from app.models.grade_class import GradeClass
                            cls_result = await db.execute(select(GradeClass).where(GradeClass.school_id == user.school_id))
                            classes = cls_result.scalars().all()
                            matched = next((c for c in classes if c.name.lower() in target_class_id.lower()), classes[0] if classes else None)
                            target_class_id = matched.id if matched else None
                            
                    assignment_data = {
                        "title": draft["parsed"].title or "Untitled",
                        "subject": draft["parsed"].subject or "General",
                        "instructions": draft["parsed"].instructions,
                        "due_date": datetime.now(timezone.utc) + timedelta(days=7), # Simplified
                        "target_type": AssignmentTargetType.CLASS,
                        "state": AssignmentState.ACTIVE
                    }
                    
                    created = await create_assignment(db, assignment_data, target_class_id, user)
                    await update.message.reply_text(f"✅ Assignment '{created.title}' has been successfully created and sent to students!")
                    del TEACHER_DRAFTS[chat_id]
                    return
                else:
                    del TEACHER_DRAFTS[chat_id]
                    await update.message.reply_text("Cancelled.")
                    return

        if intent.intent == "create_assignment" and user.role == UserRole.TEACHER:
            from app.agents.document_parser import parse_assignment_document
            parsed = await parse_assignment_document(message_text)
            
            if not parsed.due_date:
                TEACHER_DRAFTS[chat_id] = {
                    "parsed": parsed,
                    "state": "WAITING_DUE_DATE"
                }
                await update.message.reply_text(
                    f"I analyzed your assignment:\n"
                    f"Title: {parsed.title}\n"
                    f"Subject: {parsed.subject}\n\n"
                    f"But I noticed there is no due date. Shall I set it to 1 week from now? (Reply 'ok' or provide a date)"
                )
            else:
                TEACHER_DRAFTS[chat_id] = {
                    "parsed": parsed,
                    "state": "WAITING_APPROVAL"
                }
                await update.message.reply_text(
                    f"I analyzed your assignment:\n"
                    f"Title: {parsed.title}\n"
                    f"Subject: {parsed.subject}\n"
                    f"Due Date: {parsed.due_date}\n\n"
                    f"Shall I approve and send this to the students? (Reply 'approve' or 'cancel')"
                )
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
