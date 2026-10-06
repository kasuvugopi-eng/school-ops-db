import asyncio
from app.database import engine
from sqlalchemy import text

async def check_xyz_users():
    async with engine.begin() as conn:
        res = await conn.execute(text(
            "SELECT u.id, u.email, u.full_name, u.role, s.name as school_name "
            "FROM users u "
            "LEFT JOIN schools s ON u.school_id = s.id "
            "WHERE s.name ILIKE '%xyz%';"
        ))
        rows = res.fetchall()
        print("\n=== USERS IN XYZ SCHOOL ===")
        for r in rows:
            print(f"- Name: {r[2]} | Email: {r[1]} | Role: {r[3]} | School: {r[4]}")
        print("===========================\n")

if __name__ == "__main__":
    asyncio.run(check_xyz_users())
