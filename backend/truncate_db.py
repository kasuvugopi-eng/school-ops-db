import asyncio
from app.database import engine
from sqlalchemy import text

async def truncate_all_tables():
    async with engine.begin() as conn:
        # Get all table names in public schema
        result = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "AND table_name != 'alembic_version';"
        ))
        tables = [row[0] for row in result.fetchall()]
        
        if not tables:
            print("No tables found to truncate.")
            return

        print(f"Found {len(tables)} tables to truncate: {tables}")
        
        # Truncate all tables using CASCADE
        tables_str = ", ".join([f'"{t}"' for t in tables])
        await conn.execute(text(f"TRUNCATE TABLE {tables_str} CASCADE;"))
        print("Successfully truncated all application database tables!")

if __name__ == "__main__":
    asyncio.run(truncate_all_tables())
