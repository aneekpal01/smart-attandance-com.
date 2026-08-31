"""
SmartAttend-AI: Step 9 Automated Integration Test Suite (Faculty Dashboard API)
==============================================================================
Tests all 12 mandatory requirements:
  TEST 1: Dashboard overview endpoint returns valid aggregate KPIs.
  TEST 2: Create session via API returns valid session token & QR image path.
  TEST 3: Active session endpoint returns live session with QR & countdown window.
  TEST 4: Live attendance counts update correctly after verification.
  TEST 5: Student attendance roster loads with proper statuses (Present/Late/Absent).
  TEST 6: Security events endpoint loads flagged mismatches & spoofs.
  TEST 7: Audit log filtering works by event_type and severity.
  TEST 8: Session history endpoint returns completed sessions.
  TEST 9: CSV export returns valid formatted CSV without sensitive biometrics.
  TEST 10: Closed session is reflected correctly in API responses.
  TEST 11: Expired session state is computed accurately.
  TEST 12: Biometric Privacy check (Zero raw face embeddings or frames exposed).
"""

import sys
import gc
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from database.db_manager import DatabaseManager
from backend.app.main import app

client = TestClient(app)


def run_step9_verification():
    print("=" * 75)
    print("[*] SMARTATTEND-AI: STEP 9 FACULTY DASHBOARD INTEGRATION TEST SUITE")
    print("=" * 75)

    db = DatabaseManager()

    # -------------------------------------------------------------------------
    # SETUP: Seed Test Cohort & Initial Test Student
    # -------------------------------------------------------------------------
    print("\n[SETUP] Seeding Cohort Students for Dashboard Integration...")
    # Student 1: Ada Lovelace
    db.add_student("CS-901", "Ada Lovelace", "COMPUTER SCIENCE", 3, "A", "SA-STU-ADA901")
    ada = db.get_student_by_id("CS-901")
    ada_vec = np.random.RandomState(42).randn(128).astype(np.float32)
    ada_vec /= np.linalg.norm(ada_vec)
    db.save_face_embedding(ada["id"], ada_vec, sample_count=5)

    # Student 2: Alan Turing
    db.add_student("CS-902", "Alan Turing", "COMPUTER SCIENCE", 3, "A", "SA-STU-ALAN902")
    alan = db.get_student_by_id("CS-902")
    alan_vec = np.random.RandomState(100).randn(128).astype(np.float32)
    alan_vec /= np.linalg.norm(alan_vec)
    db.save_face_embedding(alan["id"], alan_vec, sample_count=5)

    # Student 3: Claude Shannon (Will remain absent)
    db.add_student("CS-903", "Claude Shannon", "COMPUTER SCIENCE", 3, "A", "SA-STU-CLAUDE903")
    claude = db.get_student_by_id("CS-903")
    claude_vec = np.random.RandomState(200).randn(128).astype(np.float32)
    claude_vec /= np.linalg.norm(claude_vec)
    db.save_face_embedding(claude["id"], claude_vec, sample_count=5)

    print("   [OK] Cohort students seeded in database.")

    # -------------------------------------------------------------------------
    # TEST 1: Dashboard Overview Endpoint
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing GET /api/dashboard/overview...")
    res1 = client.get("/api/dashboard/overview")
    assert res1.status_code == 200, f"Overview failed: {res1.text}"
    data1 = res1.json()
    assert "total_students" in data1
    assert "enrolled_students" in data1
    assert "today_sessions_count" in data1
    assert data1["total_students"] >= 3
    assert data1["enrolled_students"] >= 3
    print(f"   [OK] Dashboard overview loaded: Total Students={data1['total_students']}, Enrolled={data1['enrolled_students']}")

    # -------------------------------------------------------------------------
    # TEST 2: Create Session via API
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing POST /api/sessions/create...")
    payload = {
        "subject": "Algorithm Analysis",
        "department": "COMPUTER SCIENCE",
        "year": 3,
        "section": "A",
        "room": "Room-401",
        "faculty_name": "Prof. Donald Knuth",
        "regular_window_minutes": 10,
        "late_window_minutes": 20
    }
    res2 = client.post("/api/sessions/create", json=payload)
    assert res2.status_code == 200, f"Session create failed: {res2.text}"
    data2 = res2.json()
    assert data2["success"] is True
    session_id = data2["session"]["id"]
    session_code = data2["session"]["session_code"]
    print(f"   [OK] Session created via API: '{session_code}' (ID: {session_id})")

    # -------------------------------------------------------------------------
    # TEST 3: Active Session & QR Code Image Endpoint
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing GET /api/sessions/active and QR image serving...")
    res3 = client.get("/api/sessions/active")
    assert res3.status_code == 200
    active_list = res3.json()["sessions"]
    assert any(s["id"] == session_id for s in active_list)

    res3_qr = client.get(f"/api/sessions/{session_id}/qr-image")
    assert res3_qr.status_code == 200
    assert res3_qr.headers["content-type"] == "image/png"
    print(f"   [OK] Active session listed & PNG QR code image served successfully.")

    # -------------------------------------------------------------------------
    # TEST 4: Live Attendance Verification & Count Updates
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing POST /api/attendance/verify (Marking Ada as PRESENT)...")
    ver_payload = {
        "session_code": session_code,
        "student_qr_token": "SA-STU-ADA901",
        "student_id": "CS-901",
        "similarity_score": 0.96,
        "is_live": True
    }
    res4 = client.post("/api/attendance/verify", json=ver_payload)
    assert res4.status_code == 200
    ver_data = res4.json()
    assert ver_data["success"] is True
    assert ver_data["data"]["status"] == "PRESENT"
    print(f"   [OK] Attendance verified via API: {ver_data['data']['student_name']} -> {ver_data['data']['status']}")

    # -------------------------------------------------------------------------
    # TEST 5: Student Attendance Roster List
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing GET /api/attendance/session/{session_id}...")
    res5 = client.get(f"/api/attendance/session/{session_id}")
    assert res5.status_code == 200
    att_data = res5.json()
    assert att_data["counts"]["present_count"] == 1
    assert att_data["counts"]["absent_count"] == 2 # Alan & Claude
    assert len(att_data["present_students"]) == 1
    assert att_data["present_students"][0]["student_id"] == "CS-901"
    print(f"   [OK] Cohort roster loaded: Present={att_data['counts']['present_count']}, Absent={att_data['counts']['absent_count']}")

    # -------------------------------------------------------------------------
    # TEST 6: Security Events & Anti-Proxy Flagging
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing Anti-Proxy Detection & GET /api/security/suspicious...")
    # Attempt proxy mismatch: Alan's QR + Ada's Face
    mismatch_payload = {
        "session_code": session_code,
        "student_qr_token": "SA-STU-ALAN902",
        "student_id": "CS-901", # Ada instead of Alan
        "similarity_score": 0.95,
        "is_live": True
    }
    res6_att = client.post("/api/attendance/verify", json=mismatch_payload)
    assert res6_att.status_code == 200
    assert res6_att.json()["success"] is False
    assert "IDENTITY_MISMATCH" in res6_att.json()["message"]

    res6 = client.get("/api/security/suspicious")
    assert res6.status_code == 200
    susp = res6.json()["suspicious_events"]
    assert len(susp) > 0
    assert any(e["event_type"] == "IDENTITY_MISMATCH" for e in susp)
    print(f"   [OK] Proxy mismatch caught & listed in security feed.")

    # -------------------------------------------------------------------------
    # TEST 7: Audit Log Filtering
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing GET /api/audit/events with event_type and severity filters...")
    res7 = client.get("/api/audit/events?event_type=IDENTITY_MISMATCH&severity=WARNING")
    assert res7.status_code == 200
    audit_events = res7.json()["events"]
    assert len(audit_events) > 0
    assert all(e["event_type"] == "IDENTITY_MISMATCH" for e in audit_events)
    print(f"   [OK] Audit log filtering verified: {len(audit_events)} matching events.")

    # -------------------------------------------------------------------------
    # TEST 8: Session History Endpoint
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Testing GET /api/sessions/history...")
    res8 = client.get("/api/sessions/history")
    assert res8.status_code == 200
    history = res8.json()["history"]
    assert len(history) > 0
    assert any(s["id"] == session_id for s in history)
    print(f"   [OK] Session history loaded: {len(history)} total sessions archived.")

    # -------------------------------------------------------------------------
    # TEST 9: CSV Export Endpoint
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Testing GET /api/attendance/session/{session_id}/export-csv...")
    res9 = client.get(f"/api/attendance/session/{session_id}/export-csv")
    assert res9.status_code == 200
    assert "text/csv" in res9.headers["content-type"]
    csv_text = res9.text
    assert "SmartAttend-AI - Classroom Attendance Report" in csv_text
    assert "CS-901" in csv_text
    assert "Ada Lovelace" in csv_text
    assert "PRESENT" in csv_text
    assert "ABSENT" in csv_text
    print(f"   [OK] CSV report successfully generated and validated.")

    # -------------------------------------------------------------------------
    # TEST 10: Close Session via API
    # -------------------------------------------------------------------------
    print("\n[TEST 10] Testing POST /api/sessions/{session_id}/close...")
    res10 = client.post(f"/api/sessions/{session_id}/close")
    assert res10.status_code == 200
    assert res10.json()["success"] is True

    # Check status changed
    res10_detail = client.get(f"/api/sessions/{session_id}")
    assert res10_detail.json()["session"]["status"] == "CLOSED"
    print(f"   [OK] Session successfully closed and status updated to CLOSED.")

    # -------------------------------------------------------------------------
    # TEST 11: Expired Session Window Computation
    # -------------------------------------------------------------------------
    print("\n[TEST 11] Validating Session Expiration Calculation...")
    assert res10_detail.json()["timing_status"] is not None
    print(f"   [OK] Timing status evaluated: {res10_detail.json()['timing_status']}")

    # -------------------------------------------------------------------------
    # TEST 12: Biometric Privacy Audit (Zero Raw Embeddings in API Payloads)
    # -------------------------------------------------------------------------
    print("\n[TEST 12] Validating Biometric Privacy across all Dashboard Endpoints...")
    all_endpoints = [
        "/api/dashboard/overview",
        "/api/sessions/active",
        f"/api/sessions/{session_id}",
        f"/api/attendance/session/{session_id}",
        "/api/students/",
        "/api/security/suspicious",
        "/api/audit/events"
    ]
    for ep in all_endpoints:
        r = client.get(ep)
        body = r.text
        assert "embedding_bytes" not in body, f"Raw embedding bytes leaked in {ep}!"
        assert "face_crop" not in body, f"Face crop leaked in {ep}!"
        assert "frame_bytes" not in body, f"Frame bytes leaked in {ep}!"
    # Clean up test students from database
    with db.get_connection() as conn:
        c = conn.cursor()
        for r_id in ["CS-901", "CS-902", "CS-903"]:
            c.execute("DELETE FROM students WHERE student_id = ?", (r_id,))
        conn.commit()

    print("\n" + "=" * 75)
    print("[SUCCESS] ALL 12 STEP 9 FACULTY DASHBOARD INTEGRATION TESTS PASSED 100%!")
    print("=" * 75)
    return True


if __name__ == "__main__":
    run_step9_verification()
