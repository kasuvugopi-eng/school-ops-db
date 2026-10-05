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

    # 2. Check if Teacher is replying to a specific Student alert or sending direct student feedback
    if not file_path:
        # Check if teacher replied to a message in Telegram (reply_to_message)
        reply_msg = update.message.reply_to_message
        clean_text = (raw_text or "").strip()
        
        # Scenario A: Teacher used Telegram "Reply" feature on a Stuck Alert or Submission Alert
        if reply_msg and reply_msg.text:
            orig_text = reply_msg.text
            # Try to identify student submission context from original notification text
            async with async_sessionmaker_instance() as db:
                # Find blocked or submitted student in teacher's school/assignments
                from app.models.submission import Submission
                from app.models.assignment import Assignment
                from app.models.feedback import Feedback as FeedbackModel
                from app.models.enums import FeedbackAction, SubmissionState
                from app.telegram.bot import send_telegram_message

                # Find blocked or recent active submissions for this teacher's active assignments
                blocked_sub_res = await db.execute(
                    select(Submission, User)
                    .join(Assignment, Submission.assignment_id == Assignment.id)
                    .join(User, Submission.student_id == User.id)
                    .where(Assignment.created_by == user.id)
                    .order_by(Submission.updated_at.desc())
                )
                row = blocked_sub_res.first()
                if row:
                    sub, student = row
                    # Save feedback
                    fb = FeedbackModel(submission_id=sub.id, teacher_id=user.id, content=clean_text, action=FeedbackAction.COMMENT)
                    db.add(fb)
                    await db.commit()

                    # Send to student Telegram directly!
                    if student.telegram_chat_id:
                        student_msg = (
                            f"💬 *Teacher Feedback / Help:* \n\n"
                            f"Teacher *{user.full_name}* replied:\n"
                            f"\"{clean_text}\""
                        )
                        await send_telegram_message(student.telegram_chat_id, student_msg)

                    await update.message.reply_text(f"✅ Your message has been delivered directly to student *{student.full_name}* via Telegram!")
                    return

        # Scenario B: Check explicit triggers for new assignment
        assignment_triggers = ["create assignment", "new assignment", "assignment:", "homework:", "task:"]
        is_explicit_creation = any(clean_text.lower().startswith(trig) or f"\n{trig}" in clean_text.lower() for trig in assignment_triggers)
        
        if not is_explicit_creation:
            await update.message.reply_text(
                "💬 *Teacher Quick Assistant*\n\n"
                "• **Reply to Student Alert:** Click 'Reply' on any Telegram notification to send a direct message to that student!\n"
                "• **Create Assignment:** Start message with `Create assignment:` or upload a document/image.",
                parse_mode="Markdown"
            )
            return

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

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 1-click Inline button clicks from Telegram (Approve / Request Revision)."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if not (data.startswith("approve_") or data.startswith("revise_")):
        return

    action, sub_id_str = data.split("_", 1)
    try:
        sub_id = uuid.UUID(sub_id_str)
    except ValueError:
        return

    chat_id = str(update.effective_chat.id)
    from app.telegram.handlers.fallback import resolve_user
    from app.models.submission import Submission
    from app.models.feedback import Feedback as FeedbackModel
    from app.models.enums import FeedbackAction, SubmissionState, UserRole
    from app.telegram.bot import send_telegram_message

    async with async_sessionmaker_instance() as db:
        user = await resolve_user(chat_id, db)
        if not user or user.role != UserRole.TEACHER:
            await query.edit_message_text("⚠️ Permission denied.")
            return

        res = await db.execute(select(Submission).where(Submission.id == sub_id))
        sub = res.scalar_one_or_none()
        if not sub:
            await query.edit_message_text("⚠️ Submission not found.")
            return

        assign_res = await db.execute(select(Assignment).where(Assignment.id == sub.assignment_id))
        assignment = assign_res.scalar_one_or_none()

        student_res = await db.execute(select(User).where(User.id == sub.student_id))
        student = student_res.scalar_one_or_none()

        if action == "approve":
            sub.state = SubmissionState.COMPLETED
            fb_action = FeedbackAction.APPROVAL
            feedback_text = "Approved via Telegram Quick Action."
            response_msg = f"✅ *Assignment Approved!* ({student.full_name if student else 'Student'})"
            student_notify = f"🎉 *Assignment Approved!*\nYour work for *{assignment.title if assignment else 'Assignment'}* has been approved!"
        else:
            sub.state = SubmissionState.REVISION_REQUESTED
            fb_action = FeedbackAction.REVISION_REQUEST
            feedback_text = "Revision Requested via Telegram Quick Action."
            response_msg = f"🔄 *Revision Requested!* ({student.full_name if student else 'Student'})"
            student_notify = f"🔄 *Revision Requested*\nYour teacher requested a revision for *{assignment.title if assignment else 'Assignment'}*. Please review and resubmit."

        fb = FeedbackModel(
            submission_id=sub.id, teacher_id=user.id,
            content=feedback_text, action=fb_action
        )
        db.add(fb)
        await db.commit()

        if student and student.telegram_chat_id:
            from app.models.grade_class import GradeClass
            class_name = "All Classes"
            grade = "General"
            if assignment and assignment.target_class_id:
                cls_res = await db.execute(select(GradeClass).where(GradeClass.id == assignment.target_class_id))
                target_cls = cls_res.scalar_one_or_none()
                if target_cls:
                    class_name = target_cls.name
                    grade = target_cls.grade_level or "General"

            if action == "approve":
                formatted_student_msg = (
                    "🎉 *Assignment Approved!*\n\n"
                    f"*Assignment name:* {assignment.title if assignment else 'Assignment'}\n"
                    f"*class-grade:* {class_name} ({grade})\n"
                    f"*status:* Completed (Approved)\n"
                    f"*teacher feedback:* Great job!"
                )
            else:
                formatted_student_msg = (
                    "🔄 *Revision Requested for Assignment*\n\n"
                    f"*Assignment name:* {assignment.title if assignment else 'Assignment'}\n"
                    f"*class-grade:* {class_name} ({grade})\n"
                    f"*status:* Revision Requested\n"
                    f"*teacher feedback:* Please review and resubmit."
                )

            await send_telegram_message(student.telegram_chat_id, formatted_student_msg)

        await query.edit_message_text(f"{response_msg}\n\n📨 *Delivery Update:* Notification successfully delivered to Student ({student.full_name if student else 'Student'}) via Telegram!")
