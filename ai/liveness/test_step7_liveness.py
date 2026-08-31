"""
SmartAttend-AI: Step 7 Automated Test Suite (Liveness & Anti-Spoofing Verification)
==================================================================================
Tests all 10 mandatory requirements:
  TEST 1: Liveness service initializes correctly.
  TEST 2: Insufficient frames -> LIVENESS_UNCERTAIN.
  TEST 3: Stable static sequence -> Rejects static photo/image (not considered LIVE).
  TEST 4: Simulated temporal facial movement -> Expected LIVE signal.
  TEST 5: Identity + LIVE -> Attendance recorded successfully.
  TEST 6: Identity + SPOOF -> Attendance REJECTED.
  TEST 7: Identity + UNCERTAIN -> Attendance NOT marked.
  TEST 8: Unknown identity + LIVE -> Attendance REJECTED.
  TEST 9: QR identity mismatch + LIVE -> Attendance REJECTED.
  TEST 10: No face detected -> Attendance REJECTED.
"""

import sys
import gc
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import cv2

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from database.db_manager import DatabaseManager
from ai.attendance.session_manager import SessionManager
from ai.attendance.attendance_engine import AttendanceEngine
from ai.liveness.detector import (
    LivenessDetector,
    LivenessConfig,
    LivenessResult,
    LivenessState
)


def run_step7_verification():
    print("=" * 72)
    print("[*] SMARTATTEND-AI: STEP 7 LIVENESS & ANTI-SPOOFING TEST SUITE")
    print("=" * 72)

    # Use isolated test database
    test_db_path = Path(__file__).resolve().parent.parent.parent / "test_liveness.db"
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass

    test_qr_dir = Path(__file__).resolve().parent.parent.parent / "test_liveness_qrs"
    if test_qr_dir.exists():
        shutil.rmtree(test_qr_dir, ignore_errors=True)
    test_qr_dir.mkdir(parents=True, exist_ok=True)

    db = DatabaseManager(db_path=str(test_db_path))
    session_mgr = SessionManager(db_manager=db, qr_dir=str(test_qr_dir))
    engine = AttendanceEngine(db_manager=db)
    engine.session_mgr = session_mgr

    # -------------------------------------------------------------------------
    # SETUP: Register Test Student & Create Active Session
    # -------------------------------------------------------------------------
    print("\n[SETUP] Setting up Student & Session...")
    db.add_student("CS-701", "Diana Prince", "COMPUTER SCIENCE", 3, "A", "SA-STU-DIANA701")
    diana = db.get_student_by_id("CS-701")
    diana_vec = np.random.RandomState(42).randn(128).astype(np.float32)
    diana_vec /= np.linalg.norm(diana_vec)
    db.save_face_embedding(diana["id"], diana_vec, sample_count=5)

    base_time = datetime(2026, 8, 18, 10, 0, 0)
    sess_ok, _, session = session_mgr.create_session(
        subject="Computer Vision & AI Security",
        department="COMPUTER SCIENCE",
        year=3,
        section="A",
        room="AI-LAB",
        faculty_name="Prof. Ada Lovelace",
        start_time=base_time,
        regular_window_minutes=10,
        late_window_minutes=20
    )
    assert sess_ok is True
    print("   [OK] Student Diana (CS-701) and Session 'AI Security' initialized.")

    # -------------------------------------------------------------------------
    # TEST 1: Liveness Service Initialization
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing Liveness Detector Initialization & Configuration...")
    config = LivenessConfig(window_frames=10, min_frames_required=5, liveness_threshold=0.65)
    detector = LivenessDetector(config=config)
    assert detector is not None
    assert detector.config.window_frames == 10
    assert len(detector.frame_buffer) == 0
    print("   [OK] LivenessDetector initialized with clean configuration.")

    # -------------------------------------------------------------------------
    # TEST 2: Insufficient Frames -> LIVENESS_UNCERTAIN
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Insufficient Frames (< min_frames_required)...")
    sample_frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
    base_landmarks = [(280.0, 200.0), (360.0, 200.0), (320.0, 240.0), (290.0, 290.0), (350.0, 290.0)]
    bbox = (240, 150, 160, 180)

    # Feed only 2 frames (min required is 5)
    for _ in range(2):
        detector.add_frame_sample(sample_frame, base_landmarks, bbox)

    res_insufficient = detector.evaluate_liveness()
    assert res_insufficient.state == LivenessState.UNCERTAIN
    assert "UNCERTAIN" in res_insufficient.reason
    print(f"   [OK] 2 frames evaluated as UNCERTAIN: '{res_insufficient.reason}'")

    # -------------------------------------------------------------------------
    # TEST 3: Static Sequence (Printed Photo Attack) -> Rejected (SPOOF)
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing Static Image / Photo Attack (Identical coordinates across 10 frames)...")
    detector.reset()
    # Feed 10 identical frames with 0 pixel delta (Static photograph held in front of lens)
    for _ in range(10):
        detector.add_frame_sample(sample_frame, base_landmarks, bbox)

    res_static = detector.evaluate_liveness()
    assert res_static.state == LivenessState.SPOOF
    assert res_static.is_live is False
    print(f"   [OK] Static photo sequence successfully rejected as SPOOF: '{res_static.reason}'")

    # -------------------------------------------------------------------------
    # TEST 4: Simulated Natural Micro-Movement -> LIVE
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing Simulated Real Human Micro-Movement Sequence...")
    detector.reset()
    rng = np.random.RandomState(77)
    # Create realistic face crop with natural skin texture gradient
    texture_crop = rng.randint(50, 200, (180, 160, 3), dtype=np.uint8)

    for i in range(10):
        # Subtle natural tremor and eye/head movement (approx 1-3 pixels)
        jitter = rng.randn(5, 2) * 1.8
        live_landmarks = [(lx + jitter[k, 0], ly + jitter[k, 1]) for k, (lx, ly) in enumerate(base_landmarks)]
        detector.add_frame_sample(texture_crop, live_landmarks, bbox)

    res_live = detector.evaluate_liveness()
    assert res_live.state == LivenessState.LIVE
    assert res_live.is_live is True
    print(f"   [OK] Natural human motion evaluated as LIVE (Score: {res_live.liveness_score:.2f}, Conf: {res_live.confidence:.2f}).")

    # -------------------------------------------------------------------------
    # TEST 5: Identity + LIVE -> Attendance Allowed (PRESENT)
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing End-to-End: QR Token + Face Match + LIVE -> Marked PRESENT...")
    entry_time = base_time + timedelta(minutes=4) # 10:04 (PRESENT window)
    t_ok, _, ticket = engine.verify_student_session_entry(
        session_code_or_token=session["session_code"],
        student_qr_token="SA-STU-DIANA701",
        current_time=entry_time
    )
    assert t_ok is True

    rec_diana = {"id": diana["id"], "student_id": "CS-701", "full_name": "Diana Prince"}
    att_ok, att_msg, rec_data = engine.process_face_attendance_match(
        session_ticket=ticket,
        recognized_student=rec_diana,
        similarity_score=0.96,
        is_recognized=True,
        liveness_result=res_live
    )
    assert att_ok is True
    assert rec_data["status"] == "PRESENT"
    assert rec_data["liveness_verified"] is True
    print(f"   [OK] Attendance successfully recorded: {rec_data['student_name']} -> {rec_data['status']} (Liveness Verified).")

    # -------------------------------------------------------------------------
    # TEST 6: Identity + SPOOF -> Attendance REJECTED
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing Spoof Attack: Valid Student + Valid QR + SPOOF -> Rejected...")
    # Register second student Bruce Wayne
    db.add_student("CS-702", "Bruce Wayne", "COMPUTER SCIENCE", 3, "A", "SA-STU-BRUCE702")
    bruce = db.get_student_by_id("CS-702")
    b_ok, _, ticket_bruce = engine.verify_student_session_entry(
        session_code_or_token=session["session_code"],
        student_qr_token="SA-STU-BRUCE702",
        current_time=entry_time
    )
    assert b_ok is True

    rec_bruce = {"id": bruce["id"], "student_id": "CS-702", "full_name": "Bruce Wayne"}
    spoof_ok, spoof_msg, _ = engine.process_face_attendance_match(
        session_ticket=ticket_bruce,
        recognized_student=rec_bruce,
        similarity_score=0.95,
        is_recognized=True,
        liveness_result=res_static # Pass SPOOF result
    )
    assert spoof_ok is False
    assert "LIVENESS_FAILED" in spoof_msg
    # Verify NO record was inserted for Bruce
    assert db.get_student_session_attendance(session["id"], bruce["id"]) is None
    print(f"   [OK] Spoof attempt correctly blocked with zero DB writes: '{spoof_msg}'")

    # -------------------------------------------------------------------------
    # TEST 7: Identity + UNCERTAIN -> Attendance NOT Marked
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing Inconclusive Liveness: Valid Identity + UNCERTAIN -> Not Marked...")
    unc_ok, unc_msg, _ = engine.process_face_attendance_match(
        session_ticket=ticket_bruce,
        recognized_student=rec_bruce,
        similarity_score=0.95,
        is_recognized=True,
        liveness_result=res_insufficient # Pass UNCERTAIN result
    )
    assert unc_ok is False
    assert "LIVENESS_UNCERTAIN" in unc_msg
    assert db.get_student_session_attendance(session["id"], bruce["id"]) is None
    print(f"   [OK] Uncertain liveness safely blocked attendance: '{unc_msg}'")

    # -------------------------------------------------------------------------
    # TEST 8: Unknown Identity + LIVE -> Attendance REJECTED
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Testing Unknown Person (Not Enrolled) + LIVE -> Rejected...")
    unk_ok, unk_msg, _ = engine.process_face_attendance_match(
        session_ticket=ticket_bruce,
        recognized_student=None, # Unknown face
        similarity_score=0.25,
        is_recognized=False,
        liveness_result=res_live
    )
    assert unk_ok is False
    assert "FACE_UNKNOWN" in unk_msg
    print(f"   [OK] Unknown person correctly rejected: '{unk_msg}'")

    # -------------------------------------------------------------------------
    # TEST 9: QR Identity Mismatch + LIVE -> Attendance REJECTED
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Testing Identity Mismatch (Bruce's QR + Diana's Live Face) -> Rejected...")
    mis_ok, mis_msg, _ = engine.process_face_attendance_match(
        session_ticket=ticket_bruce,
        recognized_student=rec_diana, # Diana instead of Bruce
        similarity_score=0.95,
        is_recognized=True,
        liveness_result=res_live
    )
    assert mis_ok is False
    assert "IDENTITY_MISMATCH" in mis_msg
    print(f"   [OK] Identity mismatch correctly rejected: '{mis_msg}'")

    # -------------------------------------------------------------------------
    # TEST 10: No Face -> Attendance REJECTED
    # -------------------------------------------------------------------------
    print("\n[TEST 10] Testing Empty Frame / No Face -> Attendance REJECTED...")
    no_face_ok, no_face_msg, _ = engine.process_face_attendance_match(
        session_ticket=ticket_bruce,
        recognized_student=None,
        similarity_score=0.0,
        is_recognized=False,
        liveness_result=None
    )
    assert no_face_ok is False
    assert "FACE_UNKNOWN" in no_face_msg
    print(f"   [OK] No face detected correctly rejected: '{no_face_msg}'")

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
    print("[SUCCESS] ALL 10 STEP 7 LIVENESS & ANTI-SPOOFING TESTS PASSED 100%!")
    print("=" * 72)
    return True


if __name__ == "__main__":
    run_step7_verification()
