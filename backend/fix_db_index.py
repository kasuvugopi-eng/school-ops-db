import asyncio
from app.database import engine
from sqlalchemy import text

async def main():
    async with engine.begin() as conn:
        print("Dropping old unique index ix_users_email...")
        await conn.execute(text("DROP INDEX IF EXISTS ix_users_email;"))
        print("Creating non-unique index ix_users_email...")
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);"))
        print("Database index successfully updated!")

if __name__ == "__main__":
    asyncio.run(main())
