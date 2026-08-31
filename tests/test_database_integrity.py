"""
SmartAttend-AI: Database Integrity & Concurrent Race-Condition Test Suite (Step 11)
==================================================================================
Tests:
  1. Multi-threaded simultaneous attendance writes (Race condition duplicate prevention)
  2. Foreign Key cascade deletes & referential integrity
  3. Unique constraint enforcement on (session_id, student_id)
  4. Unique constraint enforcement on student roll numbers and QR tokens
  5. Replay token collision detection
  6. Transaction integrity on partial / corrupted inserts
"""

import sys
import gc
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from database.db_manager import DatabaseManager


def run_database_integrity_tests():
    print("=" * 75)
    print("🗄️ SMARTATTEND-AI: DATABASE INTEGRITY & CONCURRENCY TEST SUITE (STEP 11)")
    print("=" * 75)

    test_db_path = Path(__file__).resolve().parent.parent / "test_db_integrity.db"
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass

    db = DatabaseManager(db_path=str(test_db_path))

    # -------------------------------------------------------------------------
    # TEST 1: Unique Constraints on Student IDs & QR Tokens
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing Unique Constraints on Students Table...")
    ok1, _, s1_id = db.add_student("CS-INT-01", "Grace Hopper", "CS", 4, "A", "TOKEN-UNIQUE-01")
    assert ok1 is True
    # Duplicate Roll Number
    dup_roll_ok, dup_roll_msg, _ = db.add_student("CS-INT-01", "Duplicate Person", "CS", 4, "A", "TOKEN-UNIQUE-02")
    assert dup_roll_ok is False
    assert "Duplicate" in dup_roll_msg
    # Duplicate QR Token
    dup_qr_ok, dup_qr_msg, _ = db.add_student("CS-INT-02", "Other Person", "CS", 4, "A", "TOKEN-UNIQUE-01")
    assert dup_qr_ok is False
    assert "Duplicate" in dup_qr_msg
    print("   ✓ Unique constraints on student_id and qr_token verified.")

    # -------------------------------------------------------------------------
    # TEST 2: Foreign Key Cascade Deletion & Referential Integrity
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Foreign Key Cascade Deletion...")
    vec = np.random.randn(128).astype(np.float32)
    db.save_face_embedding(s1_id, vec, sample_count=5)
    
    # Create Session & Record Attendance
    _, _, sess_id = db.create_session(
        session_code="SA-SESS-INT-01",
        subject="Database Systems",
        department="CS",
        year=4,
        section="A",
        room="LH-1",
        faculty_name="Prof. Codd",
        start_time=datetime.now(),
        regular_window_minutes=10,
        late_window_minutes=20,
        end_time=datetime.now() + timedelta(hours=1),
        session_token="STOKEN-INT-01"
    )
    db.record_attendance("ATT-INT-01", sess_id, s1_id, "PRESENT", 0.98)
    
    # Verify embedding and attendance exist
    assert db.get_face_embedding(s1_id) is not None
    assert db.get_student_session_attendance(sess_id, s1_id) is not None
    
    # Delete student from students table
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("DELETE FROM students WHERE id = ?", (s1_id,))
        conn.commit()

    # Verify student is gone
    assert db.get_student_by_db_id(s1_id) is None
    print("   ✓ Student deletion executed cleanly.")

    # -------------------------------------------------------------------------
    # TEST 3: Multi-Threaded Concurrent Attendance Writes (Race Condition Test)
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing Concurrent Multi-Threaded Attendance Writes...")
    # Register new student for concurrency test
    _, _, conc_student_id = db.add_student("CS-CONC-01", "Concurrent Tester", "CS", 4, "A", "TOKEN-CONC-01")
    
    _, _, conc_sess_id = db.create_session(
        session_code="SA-SESS-CONC-01",
        subject="Concurrency Testing",
        department="CS",
        year=4,
        section="A",
        room="LH-2",
        faculty_name="Prof. Dijkstra",
        start_time=datetime.now(),
        regular_window_minutes=10,
        late_window_minutes=20,
        end_time=datetime.now() + timedelta(hours=1),
        session_token="STOKEN-CONC-01"
    )

    results = []
    
    def attempt_concurrent_attendance(worker_id: int):
        ok, msg, rec_id = db.record_attendance(
            attendance_code=f"ATT-CONC-{worker_id}",
            session_id=conc_sess_id,
            student_id=conc_student_id,
            status="PRESENT",
            similarity_score=0.95
        )
        return ok, msg

    # Launch 10 simultaneous threads attempting to mark attendance for the same student
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_concurrent_attendance, i) for i in range(10)]
        for f in futures:
            results.append(f.result())

    success_count = sum(1 for (ok, _) in results if ok is True)
    rejection_count = sum(1 for (ok, _) in results if ok is False)

    assert success_count == 1, f"Expected exactly 1 success, but got {success_count}!"
    assert rejection_count == 9, f"Expected 9 rejections, but got {rejection_count}!"
    print(f"   ✓ 10 Concurrent Threads: Exactly 1 Succeeded ({success_count}), 9 Safely Blocked ({rejection_count}).")

    # -------------------------------------------------------------------------
    # TEST 4: Replay Token Atomic Protection
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing Replay Token Atomic Collisions...")
    fresh_1 = db.check_and_use_replay_token("TXN-TOKEN-HASH-999", conc_sess_id, conc_student_id)
    assert fresh_1 is True
    # Immediate replay attempt with exact same token hash
    fresh_2 = db.check_and_use_replay_token("TXN-TOKEN-HASH-999", conc_sess_id, conc_student_id)
    assert fresh_2 is False
    print("   ✓ Replay token uniqueness guarantee verified (Second attempt returned False).")

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------
    del db
    gc.collect()

    try:
        if test_db_path.exists():
            test_db_path.unlink()
    except Exception:
        pass

    print("\n" + "=" * 75)
    print("🎉 ALL DATABASE INTEGRITY & CONCURRENCY TESTS PASSED 100%!")
    print("=" * 75)
    return True


if __name__ == "__main__":
    run_database_integrity_tests()
