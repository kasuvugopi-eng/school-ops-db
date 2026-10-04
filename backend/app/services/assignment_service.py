import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.enums import AssignmentState, SubmissionState, AssignmentTargetType
from app.services.audit_service import log_event
from app.services.user_service import get_students_for_class

ASSIGNMENT_TRANSITIONS = {
    AssignmentState.DRAFT: {AssignmentState.ACTIVE, AssignmentState.PENDING_APPROVAL},
    AssignmentState.PENDING_APPROVAL: {AssignmentState.ACTIVE, AssignmentState.DRAFT},
    AssignmentState.ACTIVE: {AssignmentState.COMPLETED, AssignmentState.CANCELLED}
}

def validate_assignment_transition(current: AssignmentState, target: AssignmentState) -> bool:
    if target not in ASSIGNMENT_TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid transition from {current} to {target}")
    return True

async def create_assignment(db: AsyncSession, data: dict, target_class_id: uuid.UUID, user: dict):
    data = {k: v for k, v in data.items() if k != "target_class_id"}
    assignment = Assignment(**data, created_by=user.id, school_id=user.school_id, target_class_id=target_class_id)
    db.add(assignment)
    await db.flush()
    
    await log_event(db, "assignment.created", school_id=user.school_id, actor_id=user.id, resource_type="assignment", resource_id=assignment.id)
    
    from app.services.submission_service import create_submissions_for_assignment
    await create_submissions_for_assignment(db, assignment.id, assignment.target_student_ids, [target_class_id])
    
    await db.commit()
    await db.refresh(assignment)
    return assignment

async def list_assignments(db: AsyncSession, school_id: uuid.UUID, class_id: uuid.UUID = None, teacher_id: uuid.UUID = None, state: AssignmentState = None):
    query = select(Assignment).where(Assignment.school_id == school_id)
    if class_id:
        query = query.where(Assignment.target_class_id == class_id)
    if teacher_id: query = query.where(Assignment.created_by == teacher_id)
    if state: query = query.where(Assignment.state == state)
    result = await db.execute(query)
    return result.scalars().all()

async def get_assignment(db: AsyncSession, assignment_id: uuid.UUID):
    result = await db.execute(select(Assignment).where(Assignment.id == assignment_id))
    assignment = result.scalar_one_or_none()
    if assignment:
        # Fetch submission summary
        sub_query = select(Submission.state, func.count(Submission.id)).where(Submission.assignment_id == assignment_id).group_by(Submission.state)
        sub_result = await db.execute(sub_query)
        assignment.submission_summary = {state.value: count for state, count in sub_result.all()}
    return assignment

async def update_assignment_state(db: AsyncSession, assignment_id: uuid.UUID, new_state: AssignmentState, user: dict):
    assignment = await get_assignment(db, assignment_id)
    if not assignment:
        raise ValueError("Assignment not found")
    validate_assignment_transition(assignment.state, new_state)
    assignment.state = new_state
    await db.commit()
    await db.refresh(assignment)
    event_name = "assignment.activated" if new_state == AssignmentState.ACTIVE else "assignment.state_updated"
    await log_event(db, correlation_id=uuid.uuid4(), school_id=assignment.school_id, actor_id=user.id, actor_type="user", event_type=event_name, resource_type="assignment", resource_id=assignment.id, details={"new_state": new_state.value})
    return assignment

async def get_assignment_with_submissions(db: AsyncSession, assignment_id: uuid.UUID):
    assignment = await get_assignment(db, assignment_id)
    if not assignment:
        return None
    subs = await db.execute(select(Submission).where(Submission.assignment_id == assignment_id))
    return {"assignment": assignment, "submissions": subs.scalars().all()}
