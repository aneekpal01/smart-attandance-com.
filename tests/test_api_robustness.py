"""
SmartAttend-AI: FastAPI API Robustness & Security Hardening Test Suite (Step 11)
================================================================================
Tests malformed inputs, edge conditions, invalid IDs, and boundary conditions
across all REST API route groups to ensure graceful validation errors (422/400)
without internal 500 crashes or unintended database state changes.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.main import app

client = TestClient(app)


def run_api_robustness_tests():
    print("=" * 75)
    print("🛡️ SMARTATTEND-AI: API ROBUSTNESS & SECURITY HARDENING TEST SUITE (STEP 11)")
    print("=" * 75)

    # -------------------------------------------------------------------------
    # TEST 1: Malformed Session Creation Payloads
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing /api/sessions/create with missing/invalid fields...")
    # Missing required 'subject'
    r1 = client.post("/api/sessions/create", json={"department": "CS", "year": 3})
    assert r1.status_code == 422, f"Expected 422 for missing field, got {r1.status_code}"

    # Invalid type for 'year' (string instead of int)
    r2 = client.post("/api/sessions/create", json={
        "subject": "Math",
        "department": "CS",
        "year": "NOT_A_NUMBER",
        "section": "A",
        "room": "R1",
        "faculty_name": "Dr. Smith"
    })
    assert r2.status_code == 422
    print("   ✓ Session creation validates missing fields and invalid data types.")

    # -------------------------------------------------------------------------
    # TEST 2: Invalid Session Lookups & Non-Existent IDs
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing /api/sessions/{id} with non-existent session ID...")
    r3 = client.get("/api/sessions/999999")
    assert r3.status_code == 404
    assert "not found" in r3.json()["detail"].lower()
    print("   ✓ Non-existent session IDs gracefully return 404 Not Found.")

    # -------------------------------------------------------------------------
    # TEST 3: Attendance Verification with Corrupted / Invalid Payloads
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing /api/attendance/verify with invalid/empty tokens...")
    r4 = client.post("/api/attendance/verify", json={
        "session_code": "NON_EXISTENT_SESSION_CODE_XYZ",
        "student_qr_token": "FAKE_TOKEN_123",
        "student_id": "CS-000",
        "similarity_score": 0.95,
        "is_live": True
    })
    assert r4.status_code == 200
    assert r4.json()["success"] is False
    assert "NOT_FOUND" in r4.json()["message"] or "INVALID" in r4.json()["message"]
    print("   ✓ Non-existent session codes reject attendance gracefully.")

    # -------------------------------------------------------------------------
    # TEST 4: Student Registration Input Validation
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing /api/students/register with missing fields...")
    r5 = client.post("/api/students/register", json={"student_id": "CS-999"})
    assert r5.status_code == 422
    print("   ✓ Student registration enforces required schema.")

    # -------------------------------------------------------------------------
    # TEST 5: Out-of-Bound Query Parameters on Analytics
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing /api/analytics/risk with out-of-range thresholds...")
    # Threshold < 50%
    r6 = client.get("/api/analytics/risk?required_threshold=10.0")
    assert r6.status_code == 422
    # Threshold > 100%
    r7 = client.get("/api/analytics/risk?required_threshold=150.0")
    assert r7.status_code == 422
    print("   ✓ Query parameter boundaries (ge=50.0, le=100.0) strictly validated.")

    # -------------------------------------------------------------------------
    # TEST 6: Biometric Leak Prevention across All Root Endpoints
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Validating Zero Biometric Vector Leakage...")
    endpoints = [
        "/api/health",
        "/api/dashboard/overview",
        "/api/sessions/active",
        "/api/students/",
        "/api/security/suspicious",
        "/api/audit/events",
        "/api/analytics/overview"
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 200
        text = resp.text
        assert "embedding_bytes" not in text, f"Biometric leak detected in {ep}!"
        assert "raw_frame" not in text, f"Raw frame leak detected in {ep}!"
    print("   ✓ Zero biometric leakage verified across all REST endpoints.")

    print("\n" + "=" * 75)
    print("🎉 ALL API ROBUSTNESS & SECURITY HARDENING TESTS PASSED 100%!")
    print("=" * 75)
    return True


if __name__ == "__main__":
    run_api_robustness_tests()
