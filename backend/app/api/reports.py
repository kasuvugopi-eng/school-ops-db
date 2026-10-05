import io
import csv
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.auth.dependencies import require_role
from app.models.enums import UserRole, SubmissionState, AssignmentState
from app.models.user import User
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.feedback import Feedback
from app.models.grade_class import GradeClass
from app.models.student_enrollment import StudentEnrollment

router = APIRouter()

@router.get("/teacher-performance")
async def get_teacher_performance_report(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    # Fetch all teachers in school
    teachers_res = await db.execute(
        select(User).where(User.school_id == current_user.school_id, User.role == UserRole.TEACHER)
    )
    teachers = teachers_res.scalars().all()

    report = []
    for t in teachers:
        # Count assignments created
        asgn_res = await db.execute(
            select(func.count(Assignment.id)).where(Assignment.created_by == t.id)
        )
        total_created = asgn_res.scalar() or 0

        # Count total reviews / feedback given by teacher
        fb_res = await db.execute(
            select(func.count(Feedback.id)).where(Feedback.teacher_id == t.id)
        )
        reviews_given = fb_res.scalar() or 0

        # Count approved submissions by teacher
        appr_res = await db.execute(
            select(func.count(Feedback.id)).where(Feedback.teacher_id == t.id, Feedback.action == "APPROVAL")
        )
        approvals = appr_res.scalar() or 0

        report.append({
            "teacher_id": str(t.id),
            "teacher_name": t.full_name,
            "email": t.email,
            "assignments_created": total_created,
            "reviews_given": reviews_given,
            "approved_count": approvals
        })
    return report

@router.get("/class-completion")
async def get_class_completion_report(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    classes_res = await db.execute(
        select(GradeClass).where(GradeClass.school_id == current_user.school_id)
    )
    classes = classes_res.scalars().all()

    report = []
    for c in classes:
        # Count total enrolled students
        enr_res = await db.execute(
            select(func.count(StudentEnrollment.student_id)).where(StudentEnrollment.class_id == c.id)
        )
        total_students = enr_res.scalar() or 0

        # Submissions stats for assignments targeted to this class
        asgns_res = await db.execute(
            select(Assignment.id).where(Assignment.target_class_id == c.id)
        )
        asgn_ids = [a for a in asgns_res.scalars()]

        completed_cnt = 0
        blocked_cnt = 0
        pending_cnt = 0

        if asgn_ids:
            c_res = await db.execute(
                select(func.count(Submission.id)).where(Submission.assignment_id.in_(asgn_ids), Submission.state == SubmissionState.COMPLETED)
            )
            completed_cnt = c_res.scalar() or 0

            b_res = await db.execute(
                select(func.count(Submission.id)).where(Submission.assignment_id.in_(asgn_ids), Submission.state == SubmissionState.BLOCKED)
            )
            blocked_cnt = b_res.scalar() or 0

            p_res = await db.execute(
                select(func.count(Submission.id)).where(Submission.assignment_id.in_(asgn_ids), Submission.state.in_([SubmissionState.SUBMITTED, SubmissionState.RESUBMITTED]))
            )
            pending_cnt = p_res.scalar() or 0

        report.append({
            "class_id": str(c.id),
            "class_name": c.name,
            "grade_level": c.grade_level or "General",
            "total_students": total_students,
            "total_completed": completed_cnt,
            "total_blocked": blocked_cnt,
            "total_pending_review": pending_cnt
        })
    return report

@router.get("/export/csv")
async def export_reports_csv(
    report_type: str = "teacher", # 'teacher' or 'class'
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "teacher":
        writer.writerow(["Teacher Name", "Email", "Assignments Created", "Total Reviews Given", "Approvals"])
        data = await get_teacher_performance_report(current_user, db)
        for r in data:
            writer.writerow([r["teacher_name"], r["email"], r["assignments_created"], r["reviews_given"], r["approved_count"]])
        filename = "Teacher_Performance_Report.csv"
    else:
        writer.writerow(["Class Name", "Grade Level", "Total Students", "Completed Submissions", "Blocked (Needs Help)", "Pending Review"])
        data = await get_class_completion_report(current_user, db)
        for r in data:
            writer.writerow([r["class_name"], r["grade_level"], r["total_students"], r["total_completed"], r["total_blocked"], r["total_pending_review"]])
        filename = "Class_Completion_Report.csv"

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
