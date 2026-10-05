from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.enums import UserRole, AssignmentState, SubmissionState, ParseApprovalState
from app.models.user import User
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.document import Document
from app.models.document_parse import DocumentParseResult
from app.models.guardian_link import GuardianLink
from app.models.teacher_class import TeacherClassAssignment

router = APIRouter()

@router.get("")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == UserRole.ADMIN:
        return await _admin_dashboard(db, current_user)
    elif current_user.role == UserRole.TEACHER:
        return await _teacher_dashboard(db, current_user)
    elif current_user.role == UserRole.STUDENT:
        return await _student_dashboard(db, current_user)
    elif current_user.role == UserRole.GUARDIAN:
        return await _parent_dashboard(db, current_user)
    return {}

async def _admin_dashboard(db: AsyncSession, user: User):
    school_id = user.school_id
    teachers = await db.execute(select(func.count(User.id)).where(User.school_id == school_id, User.role == UserRole.TEACHER))
    students = await db.execute(select(func.count(User.id)).where(User.school_id == school_id, User.role == UserRole.STUDENT))
    active_assignments = await db.execute(select(func.count(Assignment.id)).where(Assignment.school_id == school_id, Assignment.state == AssignmentState.ACTIVE))
    pending_parses = await db.execute(
        select(func.count(DocumentParseResult.id))
        .join(Document, DocumentParseResult.document_id == Document.id)
        .where(
            DocumentParseResult.approval_state == ParseApprovalState.PENDING,
            Document.school_id == school_id
        )
    )
    
    return {
        "role": "admin",
        "total_teachers": teachers.scalar() or 0,
        "total_students": students.scalar() or 0,
        "active_assignments": active_assignments.scalar() or 0,
        "pending_parses": pending_parses.scalar() or 0
    }

async def _teacher_dashboard(db: AsyncSession, user: User):
    # Teacher created assignments filter (strict isolation per teacher)
    assignment_filter = (Assignment.created_by == user.id)
    
    my_assignments = await db.execute(
        select(func.count(Assignment.id)).where(
            Assignment.school_id == user.school_id,
            assignment_filter
        )
    )
    
    # Submissions today
    from datetime import datetime, time
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    submissions_today = await db.execute(
        select(func.count(Submission.id))
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .where(
            Submission.submitted_at >= today_start,
            Assignment.school_id == user.school_id,
            assignment_filter
        )
    )

    # Blocked students
    blocked = await db.execute(
        select(Submission, User.full_name, Assignment.title)
        .join(User, Submission.student_id == User.id)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .where(
            Submission.state == SubmissionState.BLOCKED,
            Assignment.school_id == user.school_id,
            assignment_filter
        )
    )
    blocked_students = [{
        "student_name": name, "assignment_title": title,
        "blocked_reason": sub.blocked_reason, "submission_id": str(sub.id)
    } for sub, name, title in blocked.all()]
    
    # Recent submissions
    recent = await db.execute(
        select(Submission, User.full_name, Assignment.title)
        .join(User, Submission.student_id == User.id)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .where(
            Submission.state.in_([SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED]),
            Assignment.school_id == user.school_id,
            assignment_filter
        )
        .order_by(Submission.submitted_at.desc())
        .limit(10)
    )
    pending_reviews = [{
        "student_name": name, "assignment_title": title,
        "submission_id": str(sub.id), "state": sub.state.value,
        "submitted_at": str(sub.submitted_at) if sub.submitted_at else None
    } for sub, name, title in recent.all()]
    
    return {
        "role": "teacher",
        "my_assignments": my_assignments.scalar() or 0,
        "submissions_today": submissions_today.scalar() or 0,
        "blocked_students": blocked_students,
        "pending_reviews": pending_reviews
    }

async def _student_dashboard(db: AsyncSession, user: User):
    result = await db.execute(
        select(Submission, Assignment.title, Assignment.due_date)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .where(Submission.student_id == user.id, Assignment.state == AssignmentState.ACTIVE)
        .order_by(Assignment.due_date.asc().nulls_last())
    )
    assignments = [{
        "assignment_title": title, "due_date": str(due) if due else None,
        "state": sub.state.value, "submission_id": str(sub.id),
        "assignment_id": str(sub.assignment_id)
    } for sub, title, due in result.all()]
    
    overdue = sum(1 for a in assignments if a["due_date"] and a["state"] not in ("COMPLETED", "SUBMITTED", "RESUBMITTED"))
    
    return {"role": "student", "assignments": assignments, "overdue_count": overdue}

async def _parent_dashboard(db: AsyncSession, user: User):
    links = await db.execute(
        select(GuardianLink, User.full_name)
        .join(User, GuardianLink.student_id == User.id)
        .where(GuardianLink.guardian_id == user.id)
    )
    children = []
    for link, child_name in links.all():
        assignments_res = await db.execute(
            select(Assignment.title, Submission.state, Assignment.due_date)
            .join(Assignment, Submission.assignment_id == Assignment.id)
            .where(Submission.student_id == link.student_id)
            .order_by(Assignment.due_date.asc().nulls_last())
        )
        assignments = [{
            "title": title,
            "state": state.value,
            "due_date": str(due) if due else None
        } for title, state, due in assignments_res.all()]
        
        children.append({
            "full_name": child_name,
            "student_id": str(link.student_id),
            "assignments": assignments
        })
    return {"role": "guardian", "children": children}
