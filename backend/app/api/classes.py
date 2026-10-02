from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.auth.permissions import assert_same_school, assert_admin_of_school
from app.models.enums import UserRole
from app.models.user import User
from app.models.grade_class import GradeClass
from app.models.teacher_class import TeacherClassAssignment
from app.models.student_enrollment import StudentEnrollment
from app.schemas.grade_class import CreateClassRequest, ClassResponse
from app.services.audit_service import log_event
import uuid

router = APIRouter()

@router.post("", status_code=201)
async def create_class(
    request: Request,
    data: CreateClassRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    grade_class = GradeClass(
        school_id=current_user.school_id,
        name=data.name,
        grade_level=data.grade_level
    )
    db.add(grade_class)
    await db.flush()
    await log_event(db, "class.created", school_id=current_user.school_id, 
                    actor_id=current_user.id, resource_type="grade_class", 
                    resource_id=grade_class.id)
    await db.commit()
    return {"id": str(grade_class.id), "name": grade_class.name, 
            "grade_level": grade_class.grade_level, "school_id": str(grade_class.school_id),
            "teacher_count": 0, "student_count": 0}

@router.get("")
async def list_classes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(GradeClass).where(GradeClass.school_id == current_user.school_id)
    )
    classes = result.scalars().all()
    response = []
    for c in classes:
        # Count teachers
        t_count = await db.execute(
            select(func.count(TeacherClassAssignment.id)).where(
                TeacherClassAssignment.class_id == c.id
            )
        )
        # Count students
        s_count = await db.execute(
            select(func.count(StudentEnrollment.id)).where(
                StudentEnrollment.class_id == c.id
            )
        )
        response.append({
            "id": str(c.id), "name": c.name, "grade_level": c.grade_level,
            "school_id": str(c.school_id), "created_at": str(c.created_at),
            "teacher_count": t_count.scalar() or 0,
            "student_count": s_count.scalar() or 0
        })
    return response

@router.get("/{class_id}")
async def get_class(
    class_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(GradeClass).where(GradeClass.id == class_id))
    grade_class = result.scalar_one_or_none()
    if not grade_class:
        raise HTTPException(status_code=404, detail="Class not found")
    assert_same_school(current_user, grade_class.school_id)
    return {"id": str(grade_class.id), "name": grade_class.name, 
            "grade_level": grade_class.grade_level, "school_id": str(grade_class.school_id)}

@router.post("/{class_id}/teachers")
async def assign_teacher(
    class_id: uuid.UUID,
    request: Request,
    teacher_id: uuid.UUID,
    subject: str = None,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    # Verify class belongs to same school
    cls_result = await db.execute(select(GradeClass).where(GradeClass.id == class_id))
    grade_class = cls_result.scalar_one_or_none()
    if not grade_class:
        raise HTTPException(status_code=404, detail="Class not found")
    if grade_class.school_id != current_user.school_id:
        await log_event(db, "access.denied", school_id=current_user.school_id, actor_id=current_user.id, details={"reason": "cross-school class", "class_id": str(class_id)})
        await db.commit()
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Verify teacher exists and is in same school
    teacher_result = await db.execute(select(User).where(User.id == teacher_id, User.role == UserRole.TEACHER))
    teacher = teacher_result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    if teacher.school_id != current_user.school_id:
        await log_event(db, "access.denied", school_id=current_user.school_id, actor_id=current_user.id, details={"reason": "cross-school teacher", "teacher_id": str(teacher_id)})
        await db.commit()
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if already assigned
    existing = await db.execute(
        select(TeacherClassAssignment).where(
            TeacherClassAssignment.teacher_id == teacher_id,
            TeacherClassAssignment.class_id == class_id
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Teacher assigned", "teacher_id": str(teacher_id), "class_id": str(class_id)}
    
    assignment = TeacherClassAssignment(
        teacher_id=teacher_id, class_id=class_id, subject=subject
    )
    db.add(assignment)
    await log_event(db, "class.assign", school_id=current_user.school_id,
                    actor_id=current_user.id, resource_type="teacher_class",
                    resource_id=assignment.id, details={"teacher_id": str(teacher_id), "class_id": str(class_id)})
    await db.commit()
    return {"message": "Teacher assigned", "teacher_id": str(teacher_id), "class_id": str(class_id)}

@router.post("/{class_id}/students")
async def enroll_student(
    class_id: uuid.UUID,
    request: Request,
    student_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    cls_result = await db.execute(select(GradeClass).where(GradeClass.id == class_id))
    grade_class = cls_result.scalar_one_or_none()
    if not grade_class:
        raise HTTPException(status_code=404, detail="Class not found")
    if grade_class.school_id != current_user.school_id:
        await log_event(db, "access.denied", school_id=current_user.school_id, actor_id=current_user.id, details={"reason": "cross-school class", "class_id": str(class_id)})
        await db.commit()
        raise HTTPException(status_code=403, detail="Access denied")
    
    student_result = await db.execute(select(User).where(User.id == student_id, User.role == UserRole.STUDENT))
    student = student_result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if student.school_id != current_user.school_id:
        await log_event(db, "access.denied", school_id=current_user.school_id, actor_id=current_user.id, details={"reason": "cross-school student", "student_id": str(student_id)})
        await db.commit()
        raise HTTPException(status_code=403, detail="Access denied")
    
    existing = await db.execute(
        select(StudentEnrollment).where(
            StudentEnrollment.student_id == student_id,
            StudentEnrollment.class_id == class_id
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Student enrolled", "student_id": str(student_id), "class_id": str(class_id)}
    
    enrollment = StudentEnrollment(student_id=student_id, class_id=class_id)
    db.add(enrollment)
    await log_event(db, "class.assign", school_id=current_user.school_id,
                    actor_id=current_user.id, resource_type="student_enrollment",
                    resource_id=enrollment.id, details={"student_id": str(student_id), "class_id": str(class_id)})
    await db.commit()
    return {"message": "Student enrolled", "student_id": str(student_id), "class_id": str(class_id)}
