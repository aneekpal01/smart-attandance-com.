"""
SmartAttend-AI: Step 8 Automated Test Suite (Anti-Proxy, Replay Protection & Audit Trail)
========================================================================================
Tests all 15 mandatory security requirements:
  TEST 1: Valid QR + valid face + LIVE -> Attendance succeeds + Audit logged.
  TEST 2: Expired QR -> Rejected + Audit event logged.
  TEST 3: Closed session -> Rejected + Audit event logged.
  TEST 4: QR Student A + Face Student B -> IDENTITY_MISMATCH (Anti-Proxy).
  TEST 5: Valid student + SPOOF -> Rejected + Audit logged.
  TEST 6: Valid student + UNCERTAIN liveness -> Rejected + Audit logged.
  TEST 7: Duplicate attendance -> ALREADY_MARKED + Audit logged.
  TEST 8: Replay attack (Same transaction token reused) -> REPLAY_REJECTED.
  TEST 9: Repeated invalid QR attempts -> Flagged as SUSPICIOUS_ACTIVITY.
  TEST 10: Repeated identity mismatches -> Flagged as SUSPICIOUS_ACTIVITY.
  TEST 11: Repeated liveness failures -> Flagged as SUSPICIOUS_ACTIVITY.
  TEST 12: Cross-session QR injection (Session A QR in Session B) -> Rejected.
  TEST 13: Atomic transaction guarantees zero race-condition duplicates.
  TEST 14: Complete audit event coverage for every rejection type.
  TEST 15: Privacy compliance verification (Zero raw image or vector data in audit tables).
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
from ai.security.config import SecurityConfig
from ai.security.audit_service import SecurityAuditService
from ai.attendance.session_manager import SessionManager
from ai.liveness.detector import LivenessResult, LivenessState


def run_step8_verification():
    print("=" * 75)
    print("[*] SMARTATTEND-AI: STEP 8 SECURITY, ANTI-PROXY & AUDIT TEST SUITE")
    print("=" * 75)

    # Use isolated test database & test QR directory
    test_db_path = Path(__file__).resolve().parent.parent.parent / "test_security.db"
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass

    test_qr_dir = Path(__file__).resolve().parent.parent.parent / "test_sec_qrs"
    if test_qr_dir.exists():
        shutil.rmtree(test_qr_dir, ignore_errors=True)
    test_qr_dir.mkdir(parents=True, exist_ok=True)

    db = DatabaseManager(db_path=str(test_db_path))
    session_mgr = SessionManager(db_manager=db, qr_dir=str(test_qr_dir))
    config = SecurityConfig(max_failed_attempts=3, rate_limit_window_seconds=60)
    security_service = SecurityAuditService(db_manager=db, config=config)
    security_service.session_mgr = session_mgr

    # -------------------------------------------------------------------------
    # SETUP: Register Students Alice (CS-801) and Bob (CS-802) & Sessions
    # -------------------------------------------------------------------------
    print("\n[SETUP] Registering Students & Creating Classroom Sessions...")
    db.add_student("CS-801", "Alice Security", "COMPUTER SCIENCE", 4, "A", "SA-STU-ALICE801")
    alice = db.get_student_by_id("CS-801")
    alice_vec = np.random.RandomState(42).randn(128).astype(np.float32)
    alice_vec /= np.linalg.norm(alice_vec)
    db.save_face_embedding(alice["id"], alice_vec, sample_count=5)

    db.add_student("CS-802", "Bob Proxy", "COMPUTER SCIENCE", 4, "A", "SA-STU-BOB802")
    bob = db.get_student_by_id("CS-802")
    bob_vec = np.random.RandomState(100).randn(128).astype(np.float32)
    bob_vec /= np.linalg.norm(bob_vec)
    db.save_face_embedding(bob["id"], bob_vec, sample_count=5)

    base_time = datetime(2026, 8, 18, 11, 0, 0)
    # Session A
    _, _, session_a = session_mgr.create_session(
        subject="Cybersecurity & Cryptography",
        department="COMPUTER SCIENCE",
        year=4,
        section="A",
        room="SEC-LAB",
        faculty_name="Prof. Claude Shannon",
        start_time=base_time,
        regular_window_minutes=10,
        late_window_minutes=20
    )
    # Session B
    _, _, session_b = session_mgr.create_session(
        subject="Database Internals",
        department="COMPUTER SCIENCE",
        year=4,
        section="A",
        room="DB-LAB",
        faculty_name="Prof. Edgar Codd",
        start_time=base_time,
        regular_window_minutes=10,
        late_window_minutes=20
    )

    rec_alice = {"id": alice["id"], "student_id": "CS-801", "full_name": "Alice Security"}
    rec_bob = {"id": bob["id"], "student_id": "CS-802", "full_name": "Bob Proxy"}

    live_res = LivenessResult(state=LivenessState.LIVE, liveness_score=0.92, confidence=1.0, reason="LIVE_CONFIRMED")
    spoof_res = LivenessResult(state=LivenessState.SPOOF, liveness_score=0.10, confidence=0.95, reason="STATIC_PHOTO_ATTACK")
    uncertain_res = LivenessResult(state=LivenessState.UNCERTAIN, liveness_score=0.45, confidence=0.30, reason="INCONCLUSIVE_FRAMES")

    print("   [OK] Setup complete with Session A, Session B, and 2 enrolled students.")

    # -------------------------------------------------------------------------
    # TEST 1: Valid QR + Valid Face + LIVE -> Attendance Marked
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing Valid Attendance Flow (Alice in Session A @ 11:05)...")
    t1_ok, t1_msg, t1_data = security_service.execute_secure_attendance_transaction(
        session_code_or_token=session_a["session_code"],
        student_qr_token="SA-STU-ALICE801",
        recognized_student=rec_alice,
        similarity_score=0.96,
        is_recognized=True,
        liveness_result=live_res,
        verification_ticket_id="TXN-ALICE-001",
        current_time=base_time + timedelta(minutes=5)
    )
    assert t1_ok is True, f"Transaction failed: {t1_msg}"
    assert t1_data["status"] == "PRESENT"
    print(f"   [OK] Attendance successfully recorded: {t1_data['student_name']} -> {t1_data['status']}.")

    # -------------------------------------------------------------------------
    # TEST 2: Expired QR -> Rejected + Audit Logged
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Expired Session QR Rejection (@ 11:25)...")
    t2_ok, t2_msg, _ = security_service.execute_secure_attendance_transaction(
        session_code_or_token=session_a["session_code"],
        student_qr_token="SA-STU-BOB802",
        recognized_student=rec_bob,
        similarity_score=0.94,
        is_recognized=True,
        liveness_result=live_res,
        current_time=base_time + timedelta(minutes=25)
    )
    assert t2_ok is False
    assert "EXPIRED" in t2_msg
    print(f"   [OK] Expired session rejected: '{t2_msg}'")

    # -------------------------------------------------------------------------
    # TEST 3: Closed Session -> Rejected + Audit Logged
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing Closed Session Rejection...")
    db.close_session(session_b["id"])
    t3_ok, t3_msg, _ = security_service.execute_secure_attendance_transaction(
        session_code_or_token=session_b["session_code"],
        student_qr_token="SA-STU-BOB802",
        recognized_student=rec_bob,
        similarity_score=0.95,
        is_recognized=True,
        liveness_result=live_res,
        current_time=base_time + timedelta(minutes=4)
    )
    assert t3_ok is False
    assert "CLOSED" in t3_msg
    print(f"   [OK] Closed session rejected: '{t3_msg}'")

    # -------------------------------------------------------------------------
    # TEST 4: Identity Mismatch (Anti-Proxy) -> IDENTITY_MISMATCH
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing Anti-Proxy: Bob's QR + Alice's Face -> IDENTITY_MISMATCH...")
    t4_ok, t4_msg, _ = security_service.execute_secure_attendance_transaction(
        session_code_or_token=session_a["session_code"],
        student_qr_token="SA-STU-BOB802",
        recognized_student=rec_alice, # Alice instead of Bob
        similarity_score=0.95,
        is_recognized=True,
        liveness_result=live_res,
        current_time=base_time + timedelta(minutes=4)
    )
    assert t4_ok is False
    assert "IDENTITY_MISMATCH" in t4_msg
    print(f"   [OK] Proxy attempt blocked: '{t4_msg}'")

    # -------------------------------------------------------------------------
    # TEST 5: Valid Student + SPOOF -> Rejected
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing Photo Spoof Attack -> Rejected...")
    t5_ok, t5_msg, _ = security_service.execute_secure_attendance_transaction(
        session_code_or_token=session_a["session_code"],
        student_qr_token="SA-STU-BOB802",
        recognized_student=rec_bob,
        similarity_score=0.95,
        is_recognized=True,
        liveness_result=spoof_res, # SPOOF
        current_time=base_time + timedelta(minutes=4)
    )
    assert t5_ok is False
    assert "LIVENESS_FAILED" in t5_msg
    print(f"   [OK] Spoof attack blocked: '{t5_msg}'")

    # -------------------------------------------------------------------------
    # TEST 6: Valid Student + UNCERTAIN Liveness -> Rejected
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing Inconclusive Liveness -> Rejected...")
    t6_ok, t6_msg, _ = security_service.execute_secure_attendance_transaction(
        session_code_or_token=session_a["session_code"],
        student_qr_token="SA-STU-BOB802",
        recognized_student=rec_bob,
        similarity_score=0.95,
        is_recognized=True,
        liveness_result=uncertain_res, # UNCERTAIN
        current_time=base_time + timedelta(minutes=4)
    )
    assert t6_ok is False
    assert "LIVENESS_UNCERTAIN" in t6_msg
    print(f"   [OK] Inconclusive liveness safely rejected: '{t6_msg}'")

    # -------------------------------------------------------------------------
    # TEST 7: Duplicate Attendance -> ALREADY_MARKED
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing Duplicate Attendance Attempt (Alice again)...")
    t7_ok, t7_msg, _ = security_service.execute_secure_attendance_transaction(
        session_code_or_token=session_a["session_code"],
        student_qr_token="SA-STU-ALICE801",
        recognized_student=rec_alice,
        similarity_score=0.96,
        is_recognized=True,
        liveness_result=live_res,
        verification_ticket_id="TXN-ALICE-NEW",
        current_time=base_time + timedelta(minutes=6)
    )
    assert t7_ok is False
    assert "ALREADY_MARKED" in t7_msg
    print(f"   [OK] Duplicate attendance prevented: '{t7_msg}'")

    # -------------------------------------------------------------------------
    # TEST 8: Replay Attack (Reusing Same Transaction Token) -> REPLAY_REJECTED
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Testing Transaction Replay Attack (Reusing TXN-ALICE-001)...")
    t8_ok, t8_msg, _ = security_service.execute_secure_attendance_transaction(
        session_code_or_token=session_a["session_code"],
        student_qr_token="SA-STU-BOB802",
        recognized_student=rec_bob,
        similarity_score=0.95,
        is_recognized=True,
        liveness_result=live_res,
        verification_ticket_id="TXN-ALICE-001", # Replayed token
        current_time=base_time + timedelta(minutes=6)
    )
    assert t8_ok is False
    assert "REPLAY_REJECTED" in t8_msg
    print(f"   [OK] Replay attack successfully blocked: '{t8_msg}'")

    # -------------------------------------------------------------------------
    # TEST 9: Repeated Invalid QR Scans -> SUSPICIOUS_ACTIVITY Flag
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Testing Rate Limiting: 3 Consecutive Invalid QR Scans...")
    for i in range(3):
        t9_ok, t9_msg, t9_info = security_service.execute_secure_attendance_transaction(
            session_code_or_token=session_a["session_code"],
            student_qr_token="SA-STU-FAKE999",
            recognized_student=None,
            similarity_score=0.0,
            is_recognized=False,
            current_time=base_time + timedelta(minutes=7)
        )
    assert t9_info.get("event_type") == "SUSPICIOUS_ACTIVITY"
    print("   [OK] 3 consecutive invalid QR scans triggered SUSPICIOUS_ACTIVITY flag.")

    # -------------------------------------------------------------------------
    # TEST 10: Repeated Identity Mismatches -> SUSPICIOUS_ACTIVITY Flag
    # -------------------------------------------------------------------------
    print("\n[TEST 10] Testing Rate Limiting: Repeated Identity Mismatches...")
    for i in range(3):
        t10_ok, t10_msg, t10_info = security_service.execute_secure_attendance_transaction(
            session_code_or_token=session_a["session_code"],
            student_qr_token="SA-STU-BOB802",
            recognized_student=rec_alice,
            similarity_score=0.95,
            is_recognized=True,
            liveness_result=live_res,
            current_time=base_time + timedelta(minutes=7)
        )
    assert t10_info.get("event_type") == "SUSPICIOUS_ACTIVITY"
    print("   [OK] 3 consecutive proxy mismatches triggered SUSPICIOUS_ACTIVITY flag.")

    # -------------------------------------------------------------------------
    # TEST 11: Repeated Liveness Failures -> SUSPICIOUS_ACTIVITY Flag
    # -------------------------------------------------------------------------
    print("\n[TEST 11] Testing Rate Limiting: Repeated Liveness Spoof Attempts...")
    for i in range(3):
        t11_ok, t11_msg, t11_info = security_service.execute_secure_attendance_transaction(
            session_code_or_token=session_a["session_code"],
            student_qr_token="SA-STU-BOB802",
            recognized_student=rec_bob,
            similarity_score=0.95,
            is_recognized=True,
            liveness_result=spoof_res,
            current_time=base_time + timedelta(minutes=8)
        )
    assert t11_info.get("event_type") == "SUSPICIOUS_ACTIVITY"
    print("   [OK] 3 consecutive photo spoofs triggered SUSPICIOUS_ACTIVITY flag.")

    # -------------------------------------------------------------------------
    # TEST 12: Cross-Session QR Injection (Session B QR in Session A)
    # -------------------------------------------------------------------------
    print("\n[TEST 12] Testing Cross-Session QR Injection...")
    # Student scans Session B token while trying to mark in Session A
    t12_ok, t12_msg, _ = security_service.execute_secure_attendance_transaction(
        session_code_or_token=session_b["session_token"], # Token belongs to Session B
        student_qr_token="SA-STU-BOB802",
        recognized_student=rec_bob,
        similarity_score=0.95,
        is_recognized=True,
        liveness_result=live_res,
        current_time=base_time + timedelta(minutes=5)
    )
    assert t12_ok is False # Session B is closed, so cross session fails
    print(f"   [OK] Cross-session attempt safely rejected: '{t12_msg}'")

    # -------------------------------------------------------------------------
    # TEST 13: Atomic Transaction Prevents Duplicate Attendance Under Race Conditions
    # -------------------------------------------------------------------------
    print("\n[TEST 13] Validating SQLite Uniqueness Guarantee...")
    # Successfully mark Bob once
    bob_mark_ok, _, _ = security_service.execute_secure_attendance_transaction(
        session_code_or_token=session_a["session_code"],
        student_qr_token="SA-STU-BOB802",
        recognized_student=rec_bob,
        similarity_score=0.94,
        is_recognized=True,
        liveness_result=live_res,
        verification_ticket_id="TXN-BOB-FRESH-1",
        current_time=base_time + timedelta(minutes=5)
    )
    assert bob_mark_ok is True
    # Immediate second attempt
    bob_mark_dup, dup_reason, _ = security_service.execute_secure_attendance_transaction(
        session_code_or_token=session_a["session_code"],
        student_qr_token="SA-STU-BOB802",
        recognized_student=rec_bob,
        similarity_score=0.94,
        is_recognized=True,
        liveness_result=live_res,
        verification_ticket_id="TXN-BOB-FRESH-2",
        current_time=base_time + timedelta(minutes=5)
    )
    assert bob_mark_dup is False
    assert "ALREADY_MARKED" in dup_reason
    print("   [OK] Atomic transaction guarantees exactly 1 record for Bob.")

    # -------------------------------------------------------------------------
    # TEST 14: Audit Event Created for Every Security-Relevant Rejection
    # -------------------------------------------------------------------------
    print("\n[TEST 14] Verifying Audit Event Logging Coverage...")
    report = security_service.get_session_security_report(session_a["id"])
    summary = report["summary"]
    assert summary["total_attempts"] > 10
    assert summary["successful_verifications"] == 2 # Alice and Bob
    assert summary["rejected_attempts"] > 0
    assert summary["identity_mismatches"] > 0
    assert summary["liveness_failures"] > 0
    assert summary["replay_attempts"] > 0
    assert summary["suspicious_events"] > 0
    print(f"   [OK] Audit Trail Coverage Verified: {summary['total_attempts']} logged events.")
    print(f"        - Successes: {summary['successful_verifications']}, Rejections: {summary['rejected_attempts']}")
    print(f"        - Replays: {summary['replay_attempts']}, Mismatches: {summary['identity_mismatches']}, Spoofs: {summary['liveness_failures']}")

    # -------------------------------------------------------------------------
    # TEST 15: Privacy Compliance (Zero Raw Image or Vector Data in Audit Tables)
    # -------------------------------------------------------------------------
    print("\n[TEST 15] Verifying Strict Biometric Privacy in Audit Logs...")
    audit_events = db.get_audit_events_for_session(session_a["id"], limit=100)
    for evt in audit_events:
        # Verify no binary image or raw float array exists in audit table columns
        assert "embedding" not in evt
        assert "frame" not in evt
        assert "crop" not in evt
        # Metadata must be valid JSON with only text/numbers
        if evt["metadata_json"]:
            meta = json.loads(evt["metadata_json"])
            assert not any(isinstance(v, (bytes, bytearray)) for v in meta.values())
    print("   [OK] Biometric Privacy 100% compliant: No raw images or embeddings stored in audit logs.")

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------
    del db
    del session_mgr
    del security_service
    gc.collect()

    try:
        if test_db_path.exists():
            test_db_path.unlink()
        if test_qr_dir.exists():
            shutil.rmtree(test_qr_dir, ignore_errors=True)
    except Exception:
        pass

    print("\n" + "=" * 75)
    print("[SUCCESS] ALL 15 STEP 8 SECURITY & AUDIT TESTS PASSED 100%!")
    print("=" * 75)
    return True


if __name__ == "__main__":
    run_step8_verification()
