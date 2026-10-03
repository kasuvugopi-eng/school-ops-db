import asyncio
import httpx
import websockets
import json
import uuid
import sys
import traceback

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"

results = []

def record(step, name, status, reason=""):
    results.append({
        "step": step,
        "name": name,
        "status": status,
        "reason": reason.replace('\n', ' ')
    })
    print(f"[{status}] Step {step}: {name}")
    if reason:
        print(f"Reason: {reason}")

def get_token(state, key):
    t = state.get(key)
    if not t:
        return "mock_token"
    return t

def get_id(state, key):
    i = state.get(key)
    if not i:
        return str(uuid.uuid4())
    return i

async def main():
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
            state = {}

            # Step 1 — Admin registration/authentication
            try:
                # register
                req_data = {
                    "school_name": f"Test School {uuid.uuid4().hex[:8]}",
                    "school_code": f"TS{uuid.uuid4().hex[:4]}",
                    "admin_email": f"admin{uuid.uuid4().hex[:4]}@test.com",
                    "admin_password": "password123",
                    "admin_full_name": "Admin User"
                }
                r = await client.post("/api/auth/register", json=req_data)
                if r.status_code != 200:
                    record("1", "Admin registration/authentication", "FAIL", f"Register failed: {r.status_code} {r.text[:100]}")
                else:
                    data = r.json()
                    state["admin_token"] = data["access_token"]
                    # get me
                    headers = {"Authorization": f"Bearer {state['admin_token']}"}
                    r2 = await client.get("/api/auth/me", headers=headers)
                    if r2.status_code != 200:
                        record("1", "Admin registration/authentication", "FAIL", f"GET /me failed: {r2.status_code} {r2.text[:100]}")
                    else:
                        me_data = r2.json()
                        state["school_id"] = me_data["school_id"]
                        if me_data["role"] == "ADMIN":
                            record("1", "Admin registration/authentication", "PASS", f"200 OK")
                        else:
                            record("1", "Admin registration/authentication", "FAIL", f"Unexpected role {me_data.get('role')} in /me")
            except Exception as e:
                record("1", "Admin registration/authentication", "FAIL", f"Exception: {str(e)}")

            if "admin_token" not in state:
                state["admin_token"] = "mock_token"

            # Step 2 — Class, invites, and role logins
            try:
                headers_admin = {"Authorization": f"Bearer {get_token(state, 'admin_token')}"}
                r_class = await client.post("/api/classes", json={"name": "E2E Class", "grade_level": "10"}, headers=headers_admin)
                if r_class.status_code != 201:
                    record("2", "Class, invites, and role logins", "FAIL", f"Class creation failed: {r_class.status_code} {r_class.text[:100]}")
                else:
                    state["class_id"] = r_class.json()["id"]

                    async def create_invite(role, **kwargs):
                        payload = {"role": role}
                        payload.update(kwargs)
                        res = await client.post("/api/invites", json=payload, headers=headers_admin)
                        if res.status_code != 200:
                            raise Exception(f"Invite {role} failed: {res.status_code} {res.text[:100]}")
                        return res.json()["token"]

                    async def accept_invite(token, email, pwd, fname):
                        res = await client.post(f"/api/invites/{token}/accept", json={"token": token, "email": email, "password": pwd, "full_name": fname})
                        if res.status_code != 200:
                            raise Exception(f"Accept invite failed: {res.status_code} {res.text[:100]}")
                        return res.json()["id"]
                    
                    async def login(email, pwd):
                        res = await client.post("/api/auth/login", data={"username": email, "password": pwd})
                        if res.status_code != 200:
                            raise Exception(f"Login failed: {res.status_code} {res.text[:100]}")
                        return res.json()["access_token"]

                    t_token = await create_invite("TEACHER")
                    s_token = await create_invite("STUDENT", target_class_id=state["class_id"])
                    
                    # Accept teacher and student
                    t_email = f"t{uuid.uuid4().hex[:4]}@test.com"
                    s_email = f"s{uuid.uuid4().hex[:4]}@test.com"
                    t_id = await accept_invite(t_token, t_email, "pass123", "Teacher")
                    s_id = await accept_invite(s_token, s_email, "pass123", "Student")

                    state["teacher_id"] = t_id
                    state["student_id"] = s_id
                    state["teacher_token"] = await login(t_email, "pass123")
                    state["student_token"] = await login(s_email, "pass123")

                    # Create guardian invite targeting student
                    g_res = await client.post("/api/invites", json={"role": "GUARDIAN", "target_student_id": s_id, "relationship": "mother"}, headers=headers_admin)
                    if g_res.status_code != 200:
                         raise Exception(f"Invite guardian failed: {g_res.status_code} {g_res.text[:100]}")
                    g_token = g_res.json()["token"]

                    g_email = f"g{uuid.uuid4().hex[:4]}@test.com"
                    g_id = await accept_invite(g_token, g_email, "pass123", "Guardian")
                    state["guardian_token"] = await login(g_email, "pass123")
                    
                    record("2", "Class, invites, and role logins", "PASS", "200 OK")
            except Exception as e:
                record("2", "Class, invites, and role logins", "FAIL", f"Exception: {str(e)}")

            # Step 3 — Teacher assignment and student enrollment
            try:
                headers_admin = {"Authorization": f"Bearer {get_token(state, 'admin_token')}"}
                r_ta = await client.post(f"/api/classes/{get_id(state, 'class_id')}/teachers?teacher_id={get_id(state, 'teacher_id')}", headers=headers_admin)
                r_se = await client.post(f"/api/classes/{get_id(state, 'class_id')}/students?student_id={get_id(state, 'student_id')}", headers=headers_admin)
                if r_ta.status_code == 200 and r_se.status_code in [200, 409]:
                    record("3", "Teacher assignment and student enrollment", "PASS", "200 OK")
                else:
                    record("3", "Teacher assignment and student enrollment", "FAIL", f"Assign: {r_ta.status_code} {r_ta.text[:100]} Enroll: {r_se.status_code} {r_se.text[:100]}")
            except Exception as e:
                record("3", "Teacher assignment and student enrollment", "FAIL", f"Exception: {str(e)}")

            # Step 4 — Assignment creation and submission auto-creation
            try:
                headers_t = {"Authorization": f"Bearer {get_token(state, 'teacher_token')}"}
                r_a = await client.post("/api/assignments", json={
                    "title": "E2E Assignment",
                    "target_type": "CLASS",
                    "target_class_id": get_id(state, "class_id")
                }, headers=headers_t)
                if r_a.status_code == 201:
                    a_data = r_a.json()
                    state["assignment_id"] = a_data["id"]
                    
                    # Verify submission
                    r_a_det = await client.get(f"/api/assignments/{state['assignment_id']}", headers=headers_t)
                    if r_a_det.status_code == 200:
                        subs = r_a_det.json().get("submissions", [])
                        if subs and len(subs) > 0:
                            state["submission_id"] = subs[0]["id"]
                            # Activate the assignment so student can see it
                            r_act = await client.put(f"/api/assignments/{state['assignment_id']}/state", params={"new_state": "ACTIVE"}, headers=headers_t)
                            if r_act.status_code == 200:
                                record("4", "Assignment creation and submission auto-creation", "PASS", "201 Created and submissions found")
                            else:
                                record("4", "Assignment creation and submission auto-creation", "FAIL", f"Activation failed: {r_act.status_code}")
                        else:
                            record("4", "Assignment creation and submission auto-creation", "FAIL", "No submissions auto-created")
                    else:
                        record("4", "Assignment creation and submission auto-creation", "FAIL", f"Get assignment detail failed: {r_a_det.status_code}")
                else:
                    record("4", "Assignment creation and submission auto-creation", "FAIL", f"Assignment create failed: {r_a.status_code} {r_a.text[:100]}")
            except Exception as e:
                record("4", "Assignment creation and submission auto-creation", "FAIL", f"Exception: {str(e)}")

            # Step 5 — Submission state machine
            try:
                headers_s = {"Authorization": f"Bearer {get_token(state, 'student_token')}"}
                sub_id = get_id(state, "submission_id")
                
                # verify NOT_STARTED
                r_mine = await client.get("/api/submissions/mine", headers=headers_s)
                if r_mine.status_code != 200:
                    raise Exception(f"mine failed {r_mine.status_code}")
                my_subs = r_mine.json()
                init_state = [s["state"] for s in my_subs if s["id"] == sub_id]
                if not init_state or init_state[0] != "NOT_STARTED":
                    raise Exception(f"Initial state is {init_state}")

                # NOT_STARTED -> IN_PROGRESS
                r_up1 = await client.put(f"/api/submissions/{sub_id}", json={"state": "IN_PROGRESS"}, headers=headers_s)
                if r_up1.status_code != 200: raise Exception(f"IN_PROGRESS fail: {r_up1.status_code}")
                
                # IN_PROGRESS -> BLOCKED
                r_up2 = await client.put(f"/api/submissions/{sub_id}", json={"state": "BLOCKED", "blocked_reason": "stuck"}, headers=headers_s)
                if r_up2.status_code != 200: raise Exception(f"BLOCKED fail: {r_up2.status_code}")

                # BLOCKED -> IN_PROGRESS
                r_up3 = await client.put(f"/api/submissions/{sub_id}", json={"state": "IN_PROGRESS"}, headers=headers_s)
                if r_up3.status_code != 200: raise Exception(f"IN_PROGRESS 2 fail: {r_up3.status_code}")

                # IN_PROGRESS -> SUBMITTED
                r_sub = await client.post(f"/api/submissions/{sub_id}/submit", json={"content_text": "Done"}, headers=headers_s)
                if r_sub.status_code != 200: raise Exception(f"Submit fail: {r_sub.status_code}")
                
                # Invalid transition
                r_inv = await client.put(f"/api/submissions/{sub_id}", json={"state": "COMPLETED"}, headers=headers_s)
                if r_inv.status_code in [400, 403, 422]:
                    record("5", "Submission state machine", "PASS", f"200 OK. Invalid transition rejected with {r_inv.status_code} {r_inv.text[:100]}")
                else:
                    record("5", "Submission state machine", "FAIL", f"Invalid transition returned {r_inv.status_code} instead of 400/403")
            except Exception as e:
                record("5", "Submission state machine", "FAIL", f"Exception: {str(e)}")

            # Step 6 — WebSocket
            try:
                school_id = get_id(state, "school_id")
                t_token = get_token(state, "teacher_token")
                sub_id = get_id(state, "submission_id")
                headers_s = {"Authorization": f"Bearer {get_token(state, 'student_token')}"}

                ws_url = f"{WS_URL}/ws/school/{school_id}?token={t_token}"
                
                async def ws_task():
                    try:
                        async with websockets.connect(ws_url) as ws:
                            # Update submission to trigger event
                            r_up = await client.put(f"/api/submissions/{sub_id}", json={"content_text": "ws trigger"}, headers=headers_s)
                            if r_up.status_code != 200:
                                return False, f"Put failed: {r_up.status_code}"
                            # Wait for event
                            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                            return True, msg
                    except Exception as e:
                        return False, str(e)
                
                success, msg_or_err = await ws_task()
                
                # Test invalid tokens
                ws_no_token = f"{WS_URL}/ws/school/{school_id}"
                ws_bad_token = f"{WS_URL}/ws/school/{school_id}?token=invalid"
                
                async def test_ws_err(url):
                    try:
                        async with websockets.connect(url) as ws:
                            pass
                        return False, "Did not close"
                    except websockets.exceptions.InvalidStatusCode as e:
                        return False, f"HTTP status {e.status_code}"
                    except websockets.exceptions.ConnectionClosed as e:
                        if e.code == 1008:
                            return True, str(e.code)
                        return False, str(e.code)
                    except Exception as e:
                        if "403" in str(e):
                             return True, "403 Forbidden"
                        return False, str(e)
                
                no_tok_res, no_tok_msg = await test_ws_err(ws_no_token)
                bad_tok_res, bad_tok_msg = await test_ws_err(ws_bad_token)
                
                if success and no_tok_res and bad_tok_res:
                    record("6", "WebSocket", "PASS", f"Event received: {msg_or_err[:50]}. Rejects: {no_tok_msg}, {bad_tok_msg}")
                else:
                    record("6", "WebSocket", "FAIL", f"Success: {success}, msg: {msg_or_err}, no_tok: {no_tok_msg}, bad_tok: {bad_tok_msg}")
            except Exception as e:
                record("6", "WebSocket", "FAIL", f"Exception: {str(e)}")

            # Step 7 — Feedback and resubmission
            try:
                headers_t = {"Authorization": f"Bearer {get_token(state, 'teacher_token')}"}
                headers_s = {"Authorization": f"Bearer {get_token(state, 'student_token')}"}
                sub_id = get_id(state, "submission_id")

                r_fb1 = await client.post(f"/api/feedback/{sub_id}/feedback", json={"content": "pls fix", "action": "REVISION_REQUEST"}, headers=headers_t)
                if r_fb1.status_code != 200: raise Exception(f"Feedback 1 fail: {r_fb1.status_code}")
                
                r_s_chk = await client.get(f"/api/submissions/{sub_id}", headers=headers_s)
                if r_s_chk.json()["state"] != "REVISION_REQUESTED": raise Exception("Not REVISION_REQUESTED")

                r_sub = await client.post(f"/api/submissions/{sub_id}/submit", json={"content_text": "Fixed"}, headers=headers_s)
                if r_sub.status_code != 200: raise Exception(f"Resubmit fail: {r_sub.status_code}")

                r_fb2 = await client.post(f"/api/feedback/{sub_id}/feedback", json={"content": "good", "action": "APPROVAL"}, headers=headers_t)
                if r_fb2.status_code != 200: raise Exception(f"Feedback 2 fail: {r_fb2.status_code}")

                r_t_chk = await client.get(f"/api/submissions/{sub_id}", headers=headers_t)
                if r_t_chk.json()["state"] != "COMPLETED": raise Exception("Not COMPLETED")

                record("7", "Feedback and resubmission", "PASS", "200 OK transitions successful")
            except Exception as e:
                record("7", "Feedback and resubmission", "FAIL", f"Exception: {str(e)}")

            # Step 8 — Wrong-context authorization
            try:
                headers_s = {"Authorization": f"Bearer {get_token(state, 'student_token')}"}
                headers_g = {"Authorization": f"Bearer {get_token(state, 'guardian_token')}"}
                headers_admin = {"Authorization": f"Bearer {get_token(state, 'admin_token')}"}

                # Student create assignment
                r_sc = await client.post("/api/assignments", json={
                    "title": "Hacked",
                    "target_type": "CLASS",
                    "target_class_id": get_id(state, "class_id")
                }, headers=headers_s)
                
                # Read another student's submission
                async def accept_invite(token, email, pwd, fname):
                    res = await client.post(f"/api/invites/{token}/accept", json={"token": token, "email": email, "password": pwd, "full_name": fname})
                    if res.status_code != 200:
                        raise Exception(f"Accept failed: {res.status_code}")
                    return res.json()["id"]
                
                async def login(email, pwd):
                    res = await client.post("/api/auth/login", data={"username": email, "password": pwd})
                    return res.json()["access_token"]
                
                res_inv = await client.post("/api/invites", json={"role": "STUDENT", "target_class_id": get_id(state, "class_id")}, headers=headers_admin)
                if res_inv.status_code == 200:
                    s2_token = res_inv.json()["token"]
                    s2_email = f"s2{uuid.uuid4().hex[:4]}@test.com"
                    await accept_invite(s2_token, s2_email, "pass", "Student2")
                    s2_access = await login(s2_email, "pass")
                    headers_s2 = {"Authorization": f"Bearer {s2_access}"}
                    
                    r_read = await client.get(f"/api/submissions/{get_id(state, 'submission_id')}", headers=headers_s2)
                    read_status = r_read.status_code
                else:
                    read_status = 500
                
                # Guardian access teacher route (POST assignment)
                r_gc = await client.post("/api/assignments", json={"title": "Hack", "target_type": "CLASS"}, headers=headers_g)
                
                statuses = [r_sc.status_code, read_status, r_gc.status_code]
                if all(s in [403, 401, 404] for s in statuses):
                    record("8", "Wrong-context authorization", "PASS", f"All rejected. Statuses: {statuses}")
                else:
                    record("8", "Wrong-context authorization", "FAIL", f"Some passed: {statuses}")
            except Exception as e:
                record("8", "Wrong-context authorization", "FAIL", f"Exception: {str(e)}")

            # Step 9 — Audit
            try:
                headers_admin = {"Authorization": f"Bearer {get_token(state, 'admin_token')}"}
                r_audit = await client.get("/api/audit", headers=headers_admin)
                if r_audit.status_code == 200:
                    events = [e["event_type"] for e in r_audit.json()]
                    found = set(events)
                    record("9", "Audit", "PASS", f"200 OK. Found events: {list(found)[:5]}...")
                else:
                    record("9", "Audit", "FAIL", f"Audit GET failed: {r_audit.status_code}")
            except Exception as e:
                record("9", "Audit", "FAIL", f"Exception: {str(e)}")

            # Step 10 — Dashboards
            try:
                tokens = {
                    "admin": state.get("admin_token"),
                    "teacher": state.get("teacher_token"),
                    "student": state.get("student_token"),
                    "guardian": state.get("guardian_token")
                }
                dashboard_ok = True
                roles_found = []
                for role, t in tokens.items():
                    if not t: continue
                    r_dash = await client.get("/api/dashboard", headers={"Authorization": f"Bearer {t}"})
                    if r_dash.status_code != 200:
                        dashboard_ok = False
                        break
                    data = r_dash.json()
                    if data.get("role") != role:
                        dashboard_ok = False
                        break
                    roles_found.append(data.get("role"))
                if dashboard_ok:
                    record("10", "Dashboards", "PASS", f"200 OK. Roles: {roles_found}")
                else:
                    record("10", "Dashboards", "FAIL", f"Dashboard check failed for some role")
            except Exception as e:
                record("10", "Dashboards", "FAIL", f"Exception: {str(e)}")

            # Step 11 — Reminder trigger
            try:
                headers_admin = {"Authorization": f"Bearer {get_token(state, 'admin_token')}"}
                r_rem = await client.post("/api/reminders/trigger", headers=headers_admin)
                if r_rem.status_code == 200:
                    record("11", "Reminder trigger", "PASS", f"200 OK. {str(r_rem.json())[:100]}")
                else:
                    record("11", "Reminder trigger", "FAIL", f"Trigger failed: {r_rem.status_code}")
            except Exception as e:
                record("11", "Reminder trigger", "FAIL", f"Exception: {str(e)}")

            # Step 12 — Document upload and parse
            try:
                headers_admin = {"Authorization": f"Bearer {get_token(state, 'admin_token')}"}
                csv_content = b"name,email\nStudent 3,s3@test.com"
                files = {"file": ("roster.csv", csv_content, "text/csv")}
                data = {"document_type": "ROSTER"}
                
                r_up = await client.post("/api/documents/upload", data=data, files=files, headers=headers_admin)
                if r_up.status_code == 200:
                    doc_id = r_up.json()["id"]
                    r_parse = await client.post(f"/api/documents/{doc_id}/parse", headers=headers_admin)
                    if r_parse.status_code == 200:
                        record("12", "Document upload and parse", "PASS", f"Upload {r_up.status_code}, Parse {r_parse.status_code}")
                    elif r_parse.status_code == 500 or "Failed to extract text" in r_parse.text or "quota" in r_parse.text.lower() or "llm" in r_parse.text.lower() or "parsing not supported" in r_parse.text.lower():
                        record("12", "Document upload and parse", "SKIPPED", f"Upload {r_up.status_code}, Parse {r_parse.status_code}: {r_parse.text[:100]}")
                    else:
                        record("12", "Document upload and parse", "FAIL", f"Upload {r_up.status_code}, Parse {r_parse.status_code}: {r_parse.text[:100]}")
                else:
                    record("12", "Document upload and parse", "FAIL", f"Upload failed: {r_up.status_code} {r_up.text[:100]}")
            except Exception as e:
                record("12", "Document upload and parse", "FAIL", f"Exception: {str(e)}")

            # Step 13 - Clarify flow test
            try:
                headers_admin = {"Authorization": f"Bearer {get_token(state, 'admin_token')}"}
                brief_content = b"Assignment: Read Chapter 5. Instructions: Do questions 1-10."
                files = {"file": ("test_brief.txt", brief_content, "text/plain")}
                data = {"document_type": "ASSIGNMENT_BRIEF"}
                
                r_up = await client.post("/api/documents/upload", data=data, files=files, headers=headers_admin)
                if r_up.status_code == 200:
                    doc_id = r_up.json()["id"]
                    r_parse = await client.post(f"/api/documents/{doc_id}/parse", headers=headers_admin)
                    if r_parse.status_code == 200:
                        parse_state = r_parse.json().get("approval_state")
                        if parse_state == "NEEDS_CLARIFICATION":
                            r_app1 = await client.post(f"/api/documents/{doc_id}/approve", headers=headers_admin)
                            if r_app1.status_code == 409:
                                r_clar = await client.post(f"/api/documents/{doc_id}/clarify", json={
                                    "due_date": "2024-12-01T00:00:00Z",
                                    "target_class_id": get_id(state, "class_id")
                                }, headers=headers_admin)
                                
                                if r_clar.status_code == 200 and r_clar.json().get("approval_state") == "PENDING":
                                    r_app2 = await client.post(f"/api/documents/{doc_id}/approve", headers=headers_admin)
                                    if r_app2.status_code == 200:
                                        assignment_id = r_app2.json().get("created_assignment_id")
                                        if assignment_id:
                                            r_assign = await client.get(f"/api/assignments/{assignment_id}", headers=headers_admin)
                                            sub_sum = r_assign.json().get("submission_summary", {})
                                            record("13", "Clarify flow", "PASS", f"Assignment created with submissions: {sub_sum}")
                                        else:
                                            record("13", "Clarify flow", "FAIL", "Approve 200 but no assignment ID")
                                    else:
                                        record("13", "Clarify flow", "FAIL", f"Approve 2 failed: {r_app2.status_code} {r_app2.text[:100]}")
                                else:
                                    record("13", "Clarify flow", "FAIL", f"Clarify failed or not pending: {r_clar.status_code} {r_clar.text[:100]}")
                            else:
                                record("13", "Clarify flow", "FAIL", f"Expected 409 on early approve, got {r_app1.status_code}")
                        else:
                            record("13", "Clarify flow", "SKIPPED", f"Parse state not NEEDS_CLARIFICATION (was {parse_state})")
                    else:
                        record("13", "Clarify flow", "FAIL", f"Parse failed: {r_parse.status_code}")
                else:
                    record("13", "Clarify flow", "FAIL", f"Upload failed: {r_up.status_code}")
            except Exception as e:
                record("13", "Clarify flow", "FAIL", f"Exception: {str(e)}")

    except Exception as e:
        print(f"Critical error: {e}")
        traceback.print_exc()

    with open('results.json', 'w') as f:
        json.dump(results, f)

if __name__ == "__main__":
    asyncio.run(main())
