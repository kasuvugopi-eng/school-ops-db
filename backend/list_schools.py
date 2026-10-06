import asyncio
from app.database import engine
from sqlalchemy import text

async def list_schools():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT id, name, code, created_at FROM schools ORDER BY created_at DESC;"))
        rows = res.fetchall()
        print("\n=== SCHOOLS IN DATABASE ===")
        for r in rows:
            print(f"- Name: {r[1]}  (Code: {r[2]})  [ID: {r[0]}]")
        print("===============================\n")

if __name__ == "__main__":
    asyncio.run(list_schools())
