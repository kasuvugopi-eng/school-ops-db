import asyncio
from sqlalchemy import text
from app.database import engine, Base
import app.models  # Import all models to ensure metadata is populated

async def clear_data():
    async with engine.begin() as conn:
        tables = [table.name for table in Base.metadata.sorted_tables]
        if tables:
            tables_str = ", ".join(tables)
            print(f"Truncating tables: {tables_str}")
            await conn.execute(text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE;"))
    print("All table data successfully cleared!")

if __name__ == "__main__":
    asyncio.run(clear_data())
