import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.auth.permissions import assert_same_school, assert_teacher_of_class
from app.models.enums import UserRole, AssignmentState, AssignmentTargetType, SubmissionState
from app.models.user import User
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.student_enrollment import StudentEnrollment
from app.models.teacher_class import TeacherClassAssignment
from app.services.assignment_service import (
    ASSIGNMENT_TRANSITIONS, validate_assignment_transition, get_assignment
)
from app.services.audit_service import log_event
from app.schemas.assignment import CreateAssignmentRequest

router = APIRouter()

@router.post("", status_code=201)
async def create_assignment(
    request: Request,
    data: CreateAssignmentRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    if not data.class_ids:
        raise HTTPException(status_code=400, detail="At least one class_id is required")

    # Validate classes belong to same school and teacher is assigned
    if current_user.role == UserRole.TEACHER:
        tc_result = await db.execute(
            select(TeacherClassAssignment.class_id)
            .where(
                TeacherClassAssignment.teacher_id == current_user.id,
                TeacherClassAssignment.class_id.in_(data.class_ids)
            )
        )
        assigned_classes = {row[0] for row in tc_result.all()}
        for cid in data.class_ids:
            if cid not in assigned_classes:
                await log_event(db, "access.denied", school_id=current_user.school_id, actor_id=current_user.id, resource_type="school_class", resource_id=cid)
                await db.commit()
                raise HTTPException(status_code=403, detail=f"Not a teacher of class {cid}")

    if data.student_ids:
        try:
            student_uuids = [uuid.UUID(str(sid)) for sid in data.student_ids]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid student IDs")
            
        result = await db.execute(
            select(StudentEnrollment.student_id)
            .join(User, User.id == StudentEnrollment.student_id)
            .where(
                StudentEnrollment.class_id.in_(data.class_ids),
                StudentEnrollment.student_id.in_(student_uuids),
                User.school_id == current_user.school_id
            )
        )
        valid_student_ids = {row[0] for row in result.all()}
        
        if len(valid_student_ids) != len(set(student_uuids)):
            raise HTTPException(status_code=400, detail="One or more students are not enrolled in the specified classes")
            
    from app.services.assignment_service import create_assignment as create_assignment_service
    
    assignment_data = {
        "title": data.title,
        "subject": data.subject,
        "instructions": data.instructions,
        "due_date": data.due_date,
        "target_type": data.target_type,
        "target_student_ids": [str(sid) for sid in (data.student_ids or [])],
        "state": AssignmentState.DRAFT
    }
    
    assignment = await create_assignment_service(db, assignment_data, data.class_ids, current_user)
    
    # Reload assignment with classes
    await db.refresh(assignment, ['classes'])
    
    return {
        "id": str(assignment.id), "title": assignment.title, "subject": assignment.subject,
        "instructions": assignment.instructions, "due_date": str(assignment.due_date) if assignment.due_date else None,
        "target_type": assignment.target_type.value, "state": assignment.state.value,
        "created_by": str(assignment.created_by), "school_id": str(assignment.school_id),
        "class_ids": [str(c.id) for c in assignment.classes],
        "created_at": str(assignment.created_at)
    }

@router.get("")
async def list_assignments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Assignment).where(Assignment.school_id == current_user.school_id)
    
    if current_user.role == UserRole.TEACHER:
        # Only assignments for classes this teacher is assigned to
        teacher_classes = await db.execute(
            select(TeacherClassAssignment.class_id).where(
                TeacherClassAssignment.teacher_id == current_user.id
            )
        )
        class_ids = [row[0] for row in teacher_classes.all()]
        if class_ids:
            from app.models.assignment import assignment_classes
            query = query.outerjoin(assignment_classes).where(
                (assignment_classes.c.class_id.in_(class_ids)) | 
                (Assignment.created_by == current_user.id)
            ).distinct()
        else:
            query = query.where(Assignment.created_by == current_user.id)
    elif current_user.role == UserRole.STUDENT:
        # Only assignments where student has a submission, and state is not DRAFT
        student_assignments = await db.execute(
            select(Submission.assignment_id).where(Submission.student_id == current_user.id)
        )
        assignment_ids = [row[0] for row in student_assignments.all()]
        query = query.where(
            Assignment.id.in_(assignment_ids),
            Assignment.state != AssignmentState.DRAFT
        )
    
    # Eager load classes
    from sqlalchemy.orm import selectinload
    result = await db.execute(query.options(selectinload(Assignment.classes)).order_by(Assignment.created_at.desc()))
    assignments = result.scalars().all()
    
    response = []
    for a in assignments:
        # Get submission summary
        sub_counts = await db.execute(
            select(Submission.state, func.count(Submission.id))
            .where(Submission.assignment_id == a.id)
            .group_by(Submission.state)
        )
        summary = {row[0].value: row[1] for row in sub_counts.all()}
        
        response.append({
            "id": str(a.id), "title": a.title, "subject": a.subject,
            "instructions": a.instructions,
            "due_date": str(a.due_date) if a.due_date else None,
            "target_type": a.target_type.value, "state": a.state.value,
            "created_by": str(a.created_by), "school_id": str(a.school_id),
            "class_ids": [str(c.id) for c in a.classes],
            "created_at": str(a.created_at),
            "submission_summary": summary
        })
    return response

@router.get("/{id}")
async def get_assignment_detail(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(select(Assignment).options(selectinload(Assignment.classes)).where(Assignment.id == id))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assert_same_school(current_user, assignment.school_id)
    
    # Get submissions with student names
    subs_result = await db.execute(
        select(Submission, User.full_name)
        .join(User, Submission.student_id == User.id)
        .where(Submission.assignment_id == id)
    )
    submissions = []
    for sub, student_name in subs_result.all():
        submissions.append({
            "id": str(sub.id), "student_id": str(sub.student_id),
            "student_name": student_name, "state": sub.state.value,
            "content_text": sub.content_text, "blocked_reason": sub.blocked_reason,
            "submitted_at": str(sub.submitted_at) if sub.submitted_at else None,
            "created_at": str(sub.created_at)
        })
    
    return {
        "id": str(assignment.id), "title": assignment.title, "subject": assignment.subject,
        "instructions": assignment.instructions,
        "due_date": str(assignment.due_date) if assignment.due_date else None,
        "target_type": assignment.target_type.value, "state": assignment.state.value,
        "created_by": str(assignment.created_by), "school_id": str(assignment.school_id),
        "class_ids": [str(c.id) for c in assignment.classes],
        "created_at": str(assignment.created_at),
        "submissions": submissions
    }

@router.put("/{id}/state")
async def update_assignment_state(
    id: uuid.UUID,
    new_state: str,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Assignment).where(Assignment.id == id))
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assert_same_school(current_user, assignment.school_id)
    
    try:
        target_state = AssignmentState(new_state)
        validate_assignment_transition(assignment.state, target_state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    old_state = assignment.state.value
    assignment.state = target_state
    await log_event(db, "assignment.state_updated", school_id=assignment.school_id,
                    actor_id=current_user.id, resource_type="assignment",
                    resource_id=assignment.id, details={"old_state": old_state, "new_state": new_state})
    await db.commit()
    return {"id": str(assignment.id), "state": assignment.state.value}
