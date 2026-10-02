import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.grade_class import GradeClass
from app.models.teacher_class_assignment import TeacherClassAssignment
from app.models.student_enrollment import StudentEnrollment

async def create_class(db: AsyncSession, school_id: uuid.UUID, name: str, grade_level: str):
    new_class = GradeClass(school_id=school_id, name=name, grade_level=grade_level)
    db.add(new_class)
    await db.commit()
    await db.refresh(new_class)
    return new_class

async def list_classes(db: AsyncSession, school_id: uuid.UUID):
    result = await db.execute(select(GradeClass).where(GradeClass.school_id == school_id))
    return result.scalars().all()

async def get_class(db: AsyncSession, class_id: uuid.UUID):
    result = await db.execute(select(GradeClass).where(GradeClass.id == class_id))
    grade_class = result.scalar_one_or_none()
    if grade_class:
        # Simple counts for now
        t_count = await db.execute(select(func.count(TeacherClassAssignment.id)).where(TeacherClassAssignment.class_id == class_id))
        s_count = await db.execute(select(func.count(StudentEnrollment.id)).where(StudentEnrollment.class_id == class_id))
        grade_class.teacher_count = t_count.scalar()
        grade_class.student_count = s_count.scalar()
    return grade_class

async def assign_teacher_to_class(db: AsyncSession, teacher_id: uuid.UUID, class_id: uuid.UUID, subject: str, is_primary: bool):
    assignment = TeacherClassAssignment(teacher_id=teacher_id, class_id=class_id, subject=subject, is_primary=is_primary)
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment

async def enroll_student_in_class(db: AsyncSession, student_id: uuid.UUID, class_id: uuid.UUID):
    enrollment = StudentEnrollment(student_id=student_id, class_id=class_id)
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment
