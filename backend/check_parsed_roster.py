import asyncio
from app.database import engine
from sqlalchemy import text

async def check_all_parsed_rosters():
    async with engine.begin() as conn:
        res = await conn.execute(text(
            "SELECT d.id, d.original_filename, pr.parsed_data "
            "FROM documents d "
            "JOIN document_parse_results pr ON d.id = pr.document_id "
            "WHERE d.document_type = 'ROSTER' "
            "ORDER BY pr.created_at DESC LIMIT 1;"
        ))
        row = res.fetchone()
        if row:
            print(f"\nFilename: {row[1]}")
            print(f"Parsed Data JSON:\n{row[2]}\n")

if __name__ == "__main__":
    asyncio.run(check_all_parsed_rosters())
