"""
SmartAttend-AI: Step 6 Automated Test Suite (Smart Attendance Engine)
====================================================================
Tests all 12 mandatory requirements:
  TEST 1: Create valid classroom session.
  TEST 2: Generate and validate temporary session QR token.
  TEST 3: Expired session rejection.
  TEST 4: Valid student QR verification.
  TEST 5: Unknown student / unregistered QR rejection.
  TEST 6: QR student + matching face -> PRESENT.
  TEST 7: QR student + different recognized face -> REJECTED (Anti-mismatch).
  TEST 8: Duplicate attendance -> ALREADY MARKED.
  TEST 9: Late attendance window -> LATE.
  TEST 10: Closed session -> REJECTED.
  TEST 11: Attendance summary counts (Present, Late, Absent, Rejected).
  TEST 12: SQLite uniqueness constraint prevents duplicate records.
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

from database.db_manager import DatabaseManager
from ai.attendance.session_manager import SessionManager
from ai.attendance.attendance_engine import AttendanceEngine


def run_step6_verification():
    print("=" * 72)
    print("[*] SMARTATTEND-AI: STEP 6 SMART ATTENDANCE ENGINE TEST SUITE")
    print("=" * 72)

    # Use isolated test database & test QR directory
    test_db_path = Path(__file__).resolve().parent.parent.parent / "test_attendance.db"
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass

    test_qr_dir = Path(__file__).resolve().parent.parent.parent / "test_session_qrs"
    if test_qr_dir.exists():
        shutil.rmtree(test_qr_dir, ignore_errors=True)
    test_qr_dir.mkdir(parents=True, exist_ok=True)

    db = DatabaseManager(db_path=str(test_db_path))
    session_mgr = SessionManager(db_manager=db, qr_dir=str(test_qr_dir))
    engine = AttendanceEngine(db_manager=db)
    engine.session_mgr = session_mgr

    # -------------------------------------------------------------------------
    # SETUP: Register 3 Cohort Students in Computer Science Year 3 Section A
    # -------------------------------------------------------------------------
    print("\n[SETUP] Registering Cohort Students (Alice, Bob, Charlie)...")
    # Student A: Alice
    db.add_student("CS-001", "Alice Johnson", "COMPUTER SCIENCE", 3, "A", "SA-STU-ALICE001")
    alice = db.get_student_by_id("CS-001")
    alice_vec = np.random.RandomState(42).randn(128).astype(np.float32)
    alice_vec /= np.linalg.norm(alice_vec)
    db.save_face_embedding(alice["id"], alice_vec, sample_count=5)

    # Student B: Bob
    db.add_student("CS-002", "Bob Smith", "COMPUTER SCIENCE", 3, "A", "SA-STU-BOB002")
    bob = db.get_student_by_id("CS-002")
    bob_vec = np.random.RandomState(100).randn(128).astype(np.float32)
    bob_vec /= np.linalg.norm(bob_vec)
    db.save_face_embedding(bob["id"], bob_vec, sample_count=5)

    # Student C: Charlie (Will remain absent)
    db.add_student("CS-003", "Charlie Davis", "COMPUTER SCIENCE", 3, "A", "SA-STU-CHARLIE003")
    charlie = db.get_student_by_id("CS-003")
    charlie_vec = np.random.RandomState(200).randn(128).astype(np.float32)
    charlie_vec /= np.linalg.norm(charlie_vec)
    db.save_face_embedding(charlie["id"], charlie_vec, sample_count=5)

    print("   [OK] 3 Cohort students registered & face enrolled in SQLite.")

    # -------------------------------------------------------------------------
    # TEST 1: Create Valid Session
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Creating Classroom Attendance Session...")
    base_time = datetime(2026, 8, 18, 9, 0, 0)
    success, msg, session = session_mgr.create_session(
        subject="Distributed Systems",
        department="COMPUTER SCIENCE",
        year=3,
        section="A",
        room="LH-101",
        faculty_name="Dr. Leslie Lamport",
        start_time=base_time,
        regular_window_minutes=10,  # 09:00 - 09:10
        late_window_minutes=20      # 09:10 - 09:20
    )
    assert success, f"Failed to create session: {msg}"
    assert session is not None
    assert session["session_code"].startswith("SA-SESSION-")
    print(f"   [OK] Session created: '{session['session_code']}' | Start: {session['start_time']} | End: {session['end_time']}")

    # -------------------------------------------------------------------------
    # TEST 2: Generate and Validate Session QR Token
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Validating Session QR Token Payload & Security...")
    qr_file = Path(session["qr_image_path"])
    assert qr_file.exists(), "Session QR code file does not exist!"
    
    # Validate session token
    valid_ok, valid_msg, valid_sess = session_mgr.validate_session(
        session["session_token"],
        current_time=base_time + timedelta(minutes=2)
    )
    assert valid_ok is True, f"Session validation failed: {valid_msg}"
    assert valid_sess["session_code"] == session["session_code"]
    print(f"   [OK] Session QR validated cleanly at 09:02 ({valid_msg}).")

    # -------------------------------------------------------------------------
    # TEST 3: Expired Session Rejection
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing Expired Session Rejection...")
    expired_time = base_time + timedelta(minutes=25) # 09:25 (after 09:20 window)
    exp_ok, exp_msg, _ = session_mgr.validate_session(session["session_token"], current_time=expired_time)
    assert exp_ok is False, "Expired session should be rejected!"
    assert "SESSION_EXPIRED" in exp_msg
    print(f"   [OK] Expired session correctly rejected: '{exp_msg}'")

    # -------------------------------------------------------------------------
    # TEST 4: Valid Student QR Verification
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing Student Entry Verification (Alice @ 09:05)...")
    ticket_time = base_time + timedelta(minutes=5) # 09:05 (PRESENT window)
    t_ok, t_msg, ticket_alice = engine.verify_student_session_entry(
        session_code_or_token=session["session_code"],
        student_qr_token="SA-STU-ALICE001",
        current_time=ticket_time
    )
    assert t_ok is True, f"Failed ticket verification: {t_msg}"
    assert ticket_alice["student_id"] == "CS-001"
    assert ticket_alice["timing_status"] == "PRESENT"
    print(f"   [OK] Alice verified for session: Timing Status = {ticket_alice['timing_status']}")

    # -------------------------------------------------------------------------
    # TEST 5: Unknown / Fake Student QR Rejection
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing Unregistered Student QR Rejection...")
    fake_ok, fake_msg, _ = engine.verify_student_session_entry(
        session_code_or_token=session["session_code"],
        student_qr_token="SA-STU-INVALID999",
        current_time=ticket_time
    )
    assert fake_ok is False, "Invalid student QR should be rejected!"
    assert "INVALID_QR_TOKEN" in fake_msg
    print(f"   [OK] Invalid student QR correctly rejected: '{fake_msg}'")

    # -------------------------------------------------------------------------
    # TEST 6: QR Student + Matching Face -> PRESENT
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing QR Student + Matching Face (Alice)...")
    rec_alice = {
        "id": alice["id"],
        "student_id": "CS-001",
        "full_name": "Alice Johnson"
    }
    att_ok, att_msg, rec_data = engine.process_face_attendance_match(
        session_ticket=ticket_alice,
        recognized_student=rec_alice,
        similarity_score=0.96,
        is_recognized=True
    )
    assert att_ok is True, f"Attendance match failed: {att_msg}"
    assert rec_data["status"] == "PRESENT"
    print(f"   [OK] Attendance successfully recorded: {rec_data['student_name']} -> {rec_data['status']} (Sim: {rec_data['similarity_score']})")

    # -------------------------------------------------------------------------
    # TEST 7: QR Student + Different Recognized Face -> REJECTED (Anti-Mismatch)
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing Anti-Mismatch: Bob scans QR, but Alice's face recognized...")
    # Bob gets ticket
    t_bob_ok, _, ticket_bob = engine.verify_student_session_entry(
        session_code_or_token=session["session_code"],
        student_qr_token="SA-STU-BOB002",
        current_time=ticket_time
    )
    assert t_bob_ok is True
    # But camera sees Alice instead of Bob!
    mismatch_ok, mismatch_msg, _ = engine.process_face_attendance_match(
        session_ticket=ticket_bob,
        recognized_student=rec_alice, # Alice instead of Bob
        similarity_score=0.95,
        is_recognized=True
    )
    assert mismatch_ok is False, "Mismatched face should be rejected!"
    assert "IDENTITY_MISMATCH" in mismatch_msg
    print(f"   [OK] Identity mismatch correctly caught & rejected: '{mismatch_msg}'")

    # -------------------------------------------------------------------------
    # TEST 8: Duplicate Attendance -> ALREADY MARKED
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Testing Duplicate Attendance Attempt for Alice...")
    dup_ok, dup_msg, _ = engine.verify_student_session_entry(
        session_code_or_token=session["session_code"],
        student_qr_token="SA-STU-ALICE001",
        current_time=ticket_time + timedelta(minutes=1)
    )
    assert dup_ok is False, "Duplicate entry should be rejected!"
    assert "ALREADY_MARKED" in dup_msg
    print(f"   [OK] Duplicate attendance prevented: '{dup_msg}'")

    # -------------------------------------------------------------------------
    # TEST 9: Late Attendance Window -> LATE
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Testing Late Attendance Window (Bob @ 09:14)...")
    late_time = base_time + timedelta(minutes=14) # 09:14 (LATE window 09:10-09:20)
    t_late_ok, _, ticket_bob_late = engine.verify_student_session_entry(
        session_code_or_token=session["session_code"],
        student_qr_token="SA-STU-BOB002",
        current_time=late_time
    )
    assert t_late_ok is True
    assert ticket_bob_late["timing_status"] == "LATE"

    rec_bob = {
        "id": bob["id"],
        "student_id": "CS-002",
        "full_name": "Bob Smith"
    }
    late_att_ok, _, late_rec = engine.process_face_attendance_match(
        session_ticket=ticket_bob_late,
        recognized_student=rec_bob,
        similarity_score=0.94,
        is_recognized=True
    )
    assert late_att_ok is True
    assert late_rec["status"] == "LATE"
    print(f"   [OK] Bob recorded as LATE ({late_rec['status']}) at 09:14.")

    # -------------------------------------------------------------------------
    # TEST 10: Closed Session -> REJECTED
    # -------------------------------------------------------------------------
    print("\n[TEST 10] Testing Faculty Closing Session...")
    close_ok, close_msg = db.close_session(session["id"])
    assert close_ok is True
    
    closed_ok, closed_msg, _ = session_mgr.validate_session(
        session["session_code"],
        current_time=base_time + timedelta(minutes=6)
    )
    assert closed_ok is False
    assert "SESSION_CLOSED" in closed_msg
    print(f"   [OK] Closed session rejected: '{closed_msg}'")

    # -------------------------------------------------------------------------
    # TEST 11: Attendance Summary & Absent Student Tracking
    # -------------------------------------------------------------------------
    print("\n[TEST 11] Validating Attendance Summary & Absent List...")
    summary = engine.get_session_summary(session["id"])
    assert summary is not None
    assert summary["total_registered"] == 3  # Alice, Bob, Charlie
    assert summary["present_count"] == 1     # Alice
    assert summary["late_count"] == 1        # Bob
    assert summary["absent_count"] == 1      # Charlie
    assert summary["present_students"][0]["student_id"] == "CS-001"
    assert summary["late_students"][0]["student_id"] == "CS-002"
    assert summary["absent_students"][0]["student_id"] == "CS-003"
    print(f"   [OK] Total Registered : {summary['total_registered']}")
    print(f"   [OK] Present Count    : {summary['present_count']} (Alice)")
    print(f"   [OK] Late Count       : {summary['late_count']} (Bob)")
    print(f"   [OK] Absent Count     : {summary['absent_count']} (Charlie Davis)")

    # -------------------------------------------------------------------------
    # TEST 12: Database Uniqueness Constraint Prevents Duplicate Attendance
    # -------------------------------------------------------------------------
    print("\n[TEST 12] Testing SQLite DB-Level Uniqueness Constraint on (session_id, student_id)...")
    db_dup_ok, db_dup_msg, _ = db.record_attendance(
        attendance_code="ATT-FORCE-DUP",
        session_id=session["id"],
        student_id=alice["id"],
        status="PRESENT",
        similarity_score=0.99
    )
    assert db_dup_ok is False, "DB level constraint must reject duplicate insert!"
    assert "ALREADY MARKED" in db_dup_msg
    print(f"   [OK] DB unique constraint active: '{db_dup_msg}'")

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------
    del db
    del session_mgr
    del engine
    gc.collect()

    try:
        if test_db_path.exists():
            test_db_path.unlink()
        if test_qr_dir.exists():
            shutil.rmtree(test_qr_dir, ignore_errors=True)
    except Exception:
        pass

    print("\n" + "=" * 72)
    print("[SUCCESS] ALL 12 STEP 6 ATTENDANCE ENGINE REQUIREMENTS PASSED 100%!")
    print("=" * 72)
    return True


if __name__ == "__main__":
    run_step6_verification()
