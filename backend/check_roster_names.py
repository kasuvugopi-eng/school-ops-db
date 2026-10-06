import asyncio
from app.database import engine
from sqlalchemy import text

async def check_students():
    async with engine.begin() as conn:
        res = await conn.execute(text(
            "SELECT u.full_name, u.email, u.role, s.name as school_name "
            "FROM users u "
            "LEFT JOIN schools s ON u.school_id = s.id "
            "WHERE u.full_name IN ('Rahul Sharma', 'Priya Verma', 'Anish Kumar');"
        ))
        rows = res.fetchall()
        print("\n=== MATCHING STUDENTS IN DB ===")
        for r in rows:
            print(f"- Name: {r[0]} | Email: {r[1]} | Role: {r[2]} | School: {r[3]}")
        print("================================\n")

if __name__ == "__main__":
    asyncio.run(check_students())
