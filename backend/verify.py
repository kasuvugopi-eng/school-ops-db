import asyncio
import httpx
import uuid

BASE_URL = "http://127.0.0.1:8000"

async def test_teacher_scoping():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Register Admin
        admin_res = await client.post("/api/auth/register", json={
            "school_name": f"Test School {uuid.uuid4().hex[:8]}",
            "school_code": f"TS{uuid.uuid4().hex[:4]}",
            "admin_email": f"admin{uuid.uuid4().hex[:4]}@test.com",
            "admin_password": "password123",
            "admin_full_name": "Admin User"
        })
        admin_token = admin_res.json()["access_token"]
        headers_admin = {"Authorization": f"Bearer {admin_token}"}
        
        # Create Class A and Class B
        class_a_id = (await client.post("/api/classes", json={"name": "Class A", "grade_level": "10"}, headers=headers_admin)).json()["id"]
        class_b_id = (await client.post("/api/classes", json={"name": "Class B", "grade_level": "10"}, headers=headers_admin)).json()["id"]

        # Create Teacher
        t_token = (await client.post("/api/invites", json={"role": "TEACHER"}, headers=headers_admin)).json()["token"]
        t_email = f"t{uuid.uuid4().hex[:4]}@test.com"
        t_id = (await client.post(f"/api/invites/{t_token}/accept", json={"token": t_token, "email": t_email, "password": "pass", "full_name": "T"})).json()["id"]
        t_auth_token = (await client.post("/api/auth/login", data={"username": t_email, "password": "pass"})).json()["access_token"]
        headers_t = {"Authorization": f"Bearer {t_auth_token}"}

        # Create Students for Class A (2 students)
        s1_token = (await client.post("/api/invites", json={"role": "STUDENT", "target_class_id": class_a_id}, headers=headers_admin)).json()["token"]
        s1_email = f"s1{uuid.uuid4().hex[:4]}@test.com"
        s1_id = (await client.post(f"/api/invites/{s1_token}/accept", json={"token": s1_token, "email": s1_email, "password": "pass", "full_name": "S1"})).json()["id"]
        
        s2_token = (await client.post("/api/invites", json={"role": "STUDENT", "target_class_id": class_a_id}, headers=headers_admin)).json()["token"]
        s2_email = f"s2{uuid.uuid4().hex[:4]}@test.com"
        s2_id = (await client.post(f"/api/invites/{s2_token}/accept", json={"token": s2_token, "email": s2_email, "password": "pass", "full_name": "S2"})).json()["id"]

        # Create Student for Class B (1 student)
        s3_token = (await client.post("/api/invites", json={"role": "STUDENT", "target_class_id": class_b_id}, headers=headers_admin)).json()["token"]
        s3_email = f"s3{uuid.uuid4().hex[:4]}@test.com"
        s3_id = (await client.post(f"/api/invites/{s3_token}/accept", json={"token": s3_token, "email": s3_email, "password": "pass", "full_name": "S3"})).json()["id"]

        # Assign Teacher to Class A ONLY
        await client.post(f"/api/classes/{class_a_id}/teachers?teacher_id={t_id}", headers=headers_admin)
        await client.post(f"/api/classes/{class_a_id}/students?student_id={s1_id}", headers=headers_admin)
        await client.post(f"/api/classes/{class_a_id}/students?student_id={s2_id}", headers=headers_admin)
        await client.post(f"/api/classes/{class_b_id}/students?student_id={s3_id}", headers=headers_admin)
        
        print("Setup complete")

        # Create CLASS assignment for A (all students get submissions)
        r = await client.post("/api/assignments", json={
            "title": "A1",
            "target_type": "CLASS",
            "target_class_id": class_a_id
        }, headers=headers_t)
        assert r.status_code == 201
        a1_id = r.json()["id"]
        a1_det = await client.get(f"/api/assignments/{a1_id}", headers=headers_t)
        assert len(a1_det.json()["submissions"]) == 2
        print("CLASS assignment for A -> OK (2 submissions)")

        # Create GROUP assignment for A with 1 of 2 students
        r = await client.post("/api/assignments", json={
            "title": "A2",
            "target_type": "GROUP",
            "target_class_id": class_a_id,
            "target_student_ids": [s1_id]
        }, headers=headers_t)
        if r.status_code != 201:
            print("GROUP creation failed:", r.status_code, r.text)
            assert False
        a2_id = r.json()["id"]
        a2_det = await client.get(f"/api/assignments/{a2_id}", headers=headers_t)
        assert len(a2_det.json()["submissions"]) == 1
        print("GROUP assignment for A with 1 student -> OK (1 submission)")

        # Create assignment for B -> 403 and an access.denied audit row
        r = await client.post("/api/assignments", json={
            "title": "A3",
            "target_type": "CLASS",
            "target_class_id": class_b_id
        }, headers=headers_t)
        assert r.status_code == 403
        
        # Check audit
        r_audit = await client.get("/api/audit", headers=headers_admin)
        audit_events = r_audit.json()
        denied_found = any(e["event_type"] == "access.denied" and e["actor_id"] == t_id for e in audit_events)
        assert denied_found
        print("Assignment for B -> 403 and access.denied audit -> OK")

        # Student from class B in target_student_ids for class A -> rejected
        r = await client.post("/api/assignments", json={
            "title": "A4",
            "target_type": "GROUP",
            "target_class_id": class_a_id,
            "target_student_ids": [s3_id]
        }, headers=headers_t)
        assert r.status_code == 400
        print(f"Student from B for class A -> Rejected ({r.status_code}: {r.json()}) -> OK")
        
        print("ALL TESTS PASSED")

if __name__ == "__main__":
    asyncio.run(test_teacher_scoping())
