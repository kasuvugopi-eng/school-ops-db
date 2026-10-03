import asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        reg_res = await client.post("/api/auth/register-school", json={"school_name": "Test School", "admin_email": "admin2@test.com", "admin_password": "password", "admin_name": "Admin2"})
        
        login_res = await client.post("/api/auth/login", data={"username": "admin2@test.com", "password": "password"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, school_id FROM users WHERE email = 'admin2@test.com' LIMIT 1;"))
        admin = res.fetchone()
        
        await conn.execute(text("INSERT INTO schools (id, name, created_at, updated_at) VALUES ('22222222-2222-2222-2222-222222222222', 'Other', now(), now()) ON CONFLICT DO NOTHING;"))
        await conn.execute(text("INSERT INTO grade_classes (id, school_id, name, grade_level, created_at, updated_at) VALUES ('55555555-5555-5555-5555-555555555555', '22222222-2222-2222-2222-222222222222', 'Other Class', '1', now(), now()) ON CONFLICT DO NOTHING;"))
        await conn.execute(text("INSERT INTO users (id, email, password_hash, full_name, role, school_id, is_active, created_at, updated_at) VALUES ('44444444-4444-4444-4444-444444444444', 'st2@test.com', 'hash', 'St2', 'STUDENT', :sid, true, now(), now()) ON CONFLICT DO NOTHING;"), {"sid": admin.school_id})
        await conn.execute(text("INSERT INTO grade_classes (id, school_id, name, grade_level, created_at, updated_at) VALUES ('66666666-6666-6666-6666-666666666666', :sid, 'Class A', '1', now(), now()) ON CONFLICT DO NOTHING;"), {"sid": admin.school_id})
        await conn.execute(text("INSERT INTO grade_classes (id, school_id, name, grade_level, created_at, updated_at) VALUES ('77777777-7777-7777-7777-777777777777', :sid, 'Class B', '1', now(), now()) ON CONFLICT DO NOTHING;"), {"sid": admin.school_id})
        await conn.execute(text("INSERT INTO student_enrollments (id, student_id, class_id) VALUES ('88888888-8888-8888-8888-888888888888', '44444444-4444-4444-4444-444444444444', '66666666-6666-6666-6666-666666666666') ON CONFLICT DO NOTHING;"))
        await conn.commit()

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        res = await client.post("/api/classes/55555555-5555-5555-5555-555555555555/students?student_id=44444444-4444-4444-4444-444444444444", headers=headers)
        print("Cross-school response status:", res.status_code)
        print("Cross-school response text:", res.text)
        
        res = await client.post("/api/classes/77777777-7777-7777-7777-777777777777/students?student_id=44444444-4444-4444-4444-444444444444", headers=headers)
        print("Different class response status:", res.status_code)
        print("Different class response text:", res.text)

    async with engine.connect() as conn:
        print("Audit Events:")
        res = await conn.execute(text("SELECT event_type, details FROM audit_events ORDER BY created_at DESC LIMIT 2;"))
        for row in res:
            print(f"- {row.event_type}: {row.details}")

asyncio.run(main())
