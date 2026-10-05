import asyncio
from sqlalchemy import text
from app.database import engine

async def clear_teachers():
    async with engine.begin() as conn:
        teacher_subquery = "(SELECT id FROM users WHERE role = 'TEACHER')"
        await conn.execute(text("DELETE FROM teacher_class_assignments;"))
        await conn.execute(text("DELETE FROM invite_tokens WHERE role = 'TEACHER';"))
        await conn.execute(text(f"DELETE FROM audit_events WHERE actor_id IN {teacher_subquery};"))
        await conn.execute(text(f"DELETE FROM chat_messages WHERE user_id IN {teacher_subquery};"))
        await conn.execute(text(f"DELETE FROM documents WHERE uploaded_by IN {teacher_subquery};"))
        await conn.execute(text(f"DELETE FROM assignments WHERE created_by IN {teacher_subquery};"))
        await conn.execute(text("DELETE FROM users WHERE role = 'TEACHER';"))
    print("All teacher records cleared successfully!")

if __name__ == "__main__":
    asyncio.run(clear_teachers())
