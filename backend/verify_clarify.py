import asyncio
import httpx
from app.main import app


async def test_clarify():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        import uuid
        rid = uuid.uuid4().hex[:6]
        req_data = {
            "school_name": f"Clarify {rid}",
            "school_code": f"C{rid}",
            "admin_email": f"a{rid}@school.com",
            "admin_password": "password",
            "admin_full_name": "Admin"
        }
        r = await client.post("/api/auth/register", json=req_data)
        admin_token = r.json()["access_token"]
        auth = {"Authorization": f"Bearer {admin_token}"}
        
        files = {"file": ("brief.txt", b"Assignment: Math Homework\nTarget: Grade 5\nStudents: All\nAttachments: None\nConstraints: None\nInstructions: Please complete pages 5 to 10.", "text/plain")}
        data = {"document_type": "ASSIGNMENT_BRIEF"}
        r = await client.post("/api/documents/upload", data=data, files=files, headers=auth)
        print("Upload:", r.status_code, r.json())
        doc_id = r.json()["id"]
        
        r = await client.post(f"/api/documents/{doc_id}/parse", headers=auth)
        print("Parse:", r.status_code, r.json())
        
        r = await client.post(f"/api/documents/{doc_id}/approve", headers=auth)
        print("Approve:", r.status_code, r.json())
        
        r = await client.post(f"/api/documents/{doc_id}/clarify", json={"response": "The due date is 2024-12-01"}, headers=auth)
        print("Clarify:", r.status_code, r.json())
        
        r = await client.post(f"/api/documents/{doc_id}/approve", headers=auth)
        print("Approve:", r.status_code, r.json())

if __name__ == "__main__":
    asyncio.run(test_clarify())
