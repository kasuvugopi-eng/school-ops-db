import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.document_parse_result import DocumentParseResult
from app.models.enums import UserRole, AssignmentState, SubmissionState, ParseApprovalState
from app.models.student_enrollment import StudentEnrollment
from app.models.teacher_class_assignment import TeacherClassAssignment

async def get_admin_dashboard(db: AsyncSession, school_id: uuid.UUID):
    t_count = await db.execute(select(func.count(User.id)).where(User.school_id == school_id, User.role == UserRole.TEACHER))
    s_count = await db.execute(select(func.count(User.id)).where(User.school_id == school_id, User.role == UserRole.STUDENT))
    a_count = await db.execute(select(func.count(Assignment.id)).where(Assignment.school_id == school_id, Assignment.state == AssignmentState.ACTIVE))
    p_count = await db.execute(select(func.count(DocumentParseResult.id)).join(DocumentParseResult.document).where(DocumentParseResult.document.has(school_id=school_id), DocumentParseResult.approval_state == ParseApprovalState.PENDING))
    
    return {
        "total_teachers": t_count.scalar(),
        "total_students": s_count.scalar(),
        "active_assignments": a_count.scalar(),
        "pending_parses": p_count.scalar()
    }

async def get_teacher_dashboard(db: AsyncSession, teacher_id: uuid.UUID, school_id: uuid.UUID):
    a_count = await db.execute(select(func.count(Assignment.id)).where(Assignment.created_by == teacher_id, Assignment.state == AssignmentState.ACTIVE))
    # Submissions today logic omitted for brevity
    subs_today = 0
    
    blocked = await db.execute(select(Submission).join(Assignment).where(Assignment.created_by == teacher_id, Submission.state == SubmissionState.BLOCKED))
    pending = await db.execute(select(Submission).join(Assignment).where(Assignment.created_by == teacher_id, Submission.state.in_([SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED])))
    
    return {
        "my_assignments": a_count.scalar(),
        "submissions_today": subs_today,
        "blocked_students": blocked.scalars().all(),
        "pending_reviews": pending.scalars().all()
    }

async def get_student_dashboard(db: AsyncSession, student_id: uuid.UUID):
    subs = await db.execute(select(Submission).where(Submission.student_id == student_id))
    # Overdue logic omitted for brevity
    return {
        "assignments": subs.scalars().all(),
        "overdue_count": 0
    }

async def get_parent_dashboard(db: AsyncSession, guardian_id: uuid.UUID):
    return {
        "children": []
    }
