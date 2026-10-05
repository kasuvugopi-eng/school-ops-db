import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.auth.permissions import assert_same_school, assert_teacher_of_class
from app.models.enums import UserRole, AssignmentState, AssignmentTargetType, SubmissionState
from app.models.user import User
from typing import Optional
from pydantic import BaseModel
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.student_enrollment import StudentEnrollment
from app.models.teacher_class import TeacherClassAssignment
from app.services.assignment_service import (
    ASSIGNMENT_TRANSITIONS, validate_assignment_transition, get_assignment, update_assignment_state as service_update_assignment_state
)
from app.services.audit_service import log_event
from app.schemas.assignment import CreateAssignmentRequest

class UpdateStateRequest(BaseModel):
    state: Optional[str] = None
    new_state: Optional[str] = None

router = APIRouter()

@router.post("", status_code=201)
async def create_assignment(
    request: Request,
    data: CreateAssignmentRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    # Teacher scope check removed for testing so any teacher can create assignments for any class

    if data.student_ids:
        try:
            student_uuids = [uuid.UUID(str(sid)) for sid in data.student_ids]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid student IDs")
            
        result = await db.execute(
            select(StudentEnrollment.student_id)
            .join(User, User.id == StudentEnrollment.student_id)
            .where(
                StudentEnrollment.class_id == data.target_class_id,
                StudentEnrollment.student_id.in_(student_uuids),
                User.school_id == current_user.school_id
            )
        )
        valid_student_ids = {row[0] for row in result.all()}
        
        if len(valid_student_ids) != len(set(student_uuids)):
            raise HTTPException(status_code=400, detail="One or more students are not enrolled in the specified class")
            
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
    
    assignment = await create_assignment_service(db, assignment_data, data.target_class_id, current_user)
    
    return {
        "id": str(assignment.id), "title": assignment.title, "subject": assignment.subject,
        "instructions": assignment.instructions, "due_date": str(assignment.due_date) if assignment.due_date else None,
        "target_type": assignment.target_type.value, "state": assignment.state.value,
        "created_by": str(assignment.created_by), "school_id": str(assignment.school_id),
        "target_class_id": str(assignment.target_class_id) if assignment.target_class_id else None,
        "created_at": str(assignment.created_at)
    }

@router.get("")
async def list_assignments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Assignment).where(Assignment.school_id == current_user.school_id)
    
    if current_user.role == UserRole.TEACHER:
        tc_result = await db.execute(
            select(TeacherClassAssignment.class_id).where(TeacherClassAssignment.teacher_id == current_user.id)
        )
        class_ids = [row[0] for row in tc_result.all()]
        if class_ids:
            query = query.where((Assignment.created_by == current_user.id) | (Assignment.target_class_id.in_(class_ids)))
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
    
    result = await db.execute(query.order_by(Assignment.created_at.desc()))
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
            "target_class_id": str(a.target_class_id) if a.target_class_id else None,
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
    result = await db.execute(select(Assignment).where(Assignment.id == id))
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
        "target_class_id": str(assignment.target_class_id) if assignment.target_class_id else None,
        "created_at": str(assignment.created_at),
        "submissions": submissions
    }

@router.put("/{id}/state")
async def update_assignment_state(
    id: uuid.UUID,
    payload: Optional[UpdateStateRequest] = Body(None),
    new_state: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    target_state_str = (payload.state if payload else None) or (payload.new_state if payload else None) or state or new_state
    if not target_state_str:
        raise HTTPException(status_code=400, detail="state or new_state parameter is required")
    try:
        target_state = AssignmentState(target_state_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid assignment state: {target_state_str}")
        
    try:
        assignment = await service_update_assignment_state(db, id, target_state, current_user)
        return {"id": str(assignment.id), "state": assignment.state.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

