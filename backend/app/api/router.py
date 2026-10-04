from fastapi import APIRouter
from app.api import auth, schools, classes, invites, assignments, submissions, feedback, documents, audit, dashboard, reminders, users, teachers, students

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(schools.router, prefix="/schools", tags=["Schools"])
api_router.include_router(classes.router, prefix="/classes", tags=["Classes"])
api_router.include_router(invites.router, prefix="/invites", tags=["Invites"])
api_router.include_router(assignments.router, prefix="/assignments", tags=["Assignments"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["Submissions"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(reminders.router, prefix="/reminders", tags=["Reminders"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(teachers.router, prefix="/teachers", tags=["Teachers"])
api_router.include_router(students.router, prefix="/students", tags=["Students"])
