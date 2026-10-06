import asyncio
from app.database import engine
from sqlalchemy import text

async def fetch_raghavendra_users():
    async with engine.begin() as conn:
        res = await conn.execute(text(
            "SELECT u.full_name, u.email, u.role, s.name "
            "FROM users u "
            "JOIN schools s ON u.school_id = s.id "
            "WHERE s.name ILIKE '%Raghavendra%';"
        ))
        rows = res.fetchall()
        print("\n=== USERS IN RAGHAVENDRA PUBLIC SCHOOL ===")
        for r in rows:
            print(f"- Full Name: {r[0]} | Email: {r[1]} | Role: {r[2]}")
        print("=============================================\n")

if __name__ == "__main__":
    asyncio.run(fetch_raghavendra_users())
