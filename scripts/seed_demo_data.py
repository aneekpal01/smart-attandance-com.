"""
SmartAttend-AI: SIH Live Demonstration Data Seeder (Step 12)
============================================================
Seeds isolated, realistic student cohort and session demonstration data:
  - 6 Registered Engineering Students across Year 4, Sec A (Computer Science)
  - Pre-generated secure student QR codes and disk images
  - Realistic 128-D SFace facial embeddings enrolled in SQLite
  - 1 Active Classroom Demo Session with dynamic Projector QR
  - Historical session attendance records for live AI Analytics display
"""

import sys
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from database.db_manager import DatabaseManager
from ai.face_recognition.qr_manager import QRManager
from ai.attendance.session_manager import SessionManager


def seed_sih_demo_data():
    print("=" * 80)
    print("🌱 SMARTATTEND-AI: SEEDING ISOLATED SIH DEMONSTRATION DATA")
    print("=" * 80)

    db = DatabaseManager()
    db.init_schema()
    qr_mgr = QRManager()
    session_mgr = SessionManager(db_manager=db)

    # 1. Clean existing demo students if present
    demo_students = [
        ("CS-2026-01", "Margaret Hamilton", "COMPUTER SCIENCE", 4, "A"),
        ("CS-2026-02", "Alan Turing", "COMPUTER SCIENCE", 4, "A"),
        ("CS-2026-03", "Ada Lovelace", "COMPUTER SCIENCE", 4, "A"),
        ("CS-2026-04", "Claude Shannon", "COMPUTER SCIENCE", 4, "A"),
        ("CS-2026-05", "Grace Hopper", "COMPUTER SCIENCE", 4, "A"),
        ("CS-2026-06", "John von Neumann", "COMPUTER SCIENCE", 4, "A")
    ]

    print("[1/4] Registering Demo Students & Generating Secure QR Identity Tokens...")
    rng = np.random.RandomState(42)
    seeded_students = []

    for roll, name, dept, year, sec in demo_students:
        existing = db.get_student_by_id(roll)
        if existing:
            stu_id = existing["id"]
            token = existing["qr_token"]
        else:
            token = qr_mgr.generate_token()
            ok, msg, stu_id = db.add_student(roll, name, dept, year, sec, token)
            if not ok:
                print(f"   [!] Note: {msg}")
                existing_stu = db.get_student_by_id(roll)
                stu_id = existing_stu["id"] if existing_stu else None
        
        # Save QR Image
        qr_file = qr_mgr.generate_qr_image(token, roll)

        # Generate & Save 128-D Normalized SFace Embedding
        vec = rng.randn(128).astype(np.float32)
        vec /= np.linalg.norm(vec)
        if stu_id:
            db.save_face_embedding(stu_id, vec, sample_count=5)
            seeded_students.append((stu_id, roll, name, token))
            print(f"   ✓ Student: {name:<20} | Roll: {roll:<10} | QR Token: {token} | QR File: {qr_file.name}")

    print(f"\n[2/4] Seeded {len(seeded_students)} demo students with 128-D SFace face embeddings.")

    # 2. Seed 4 Historical Sessions for Rich AI Analytics
    print("\n[3/4] Creating Historical Classroom Sessions for AI Analytics...")
    base_time = datetime.now() - timedelta(days=5)
    hist_subjects = [
        "Distributed Systems & Cloud Computing",
        "Neural Networks & Deep Learning",
        "Computer Vision & Edge AI",
        "Computer Architecture"
    ]

    for idx, subj in enumerate(hist_subjects):
        sess_dt = base_time + timedelta(days=idx, hours=9)
        sess_code = f"SA-DEMO-HIST-{idx+1}"
        
        # Check if already exists
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM sessions WHERE session_code = ?", (sess_code,))
            row = c.fetchone()
            if row:
                s_id = row["id"]
            else:
                _, _, s_id = db.create_session(
                    session_code=sess_code,
                    subject=subj,
                    department="COMPUTER SCIENCE",
                    year=4,
                    section="A",
                    room="LH-401",
                    faculty_name="Prof. Andrew Ng",
                    start_time=sess_dt,
                    regular_window_minutes=15,
                    late_window_minutes=30,
                    end_time=sess_dt + timedelta(minutes=60),
                    session_token=f"STOKEN-DEMO-HIST-{idx+1}"
                )

        # Seed attendance for demo cohort
        # Margaret, Alan, Ada attend all
        # Claude is absent for 2
        # Grace is late for 1
        # John is absent for 3 (At-risk demonstration)
        for stu_db_id, r_no, s_name, _ in seeded_students:
            if r_no in ("CS-2026-01", "CS-2026-02", "CS-2026-03"):
                db.record_attendance(f"ATT-DEMO-{idx}-{r_no}", s_id, stu_db_id, "PRESENT", 0.95)
            elif r_no == "CS-2026-04" and idx >= 2:
                db.record_attendance(f"ATT-DEMO-{idx}-{r_no}", s_id, stu_db_id, "PRESENT", 0.93)
            elif r_no == "CS-2026-05":
                status = "LATE" if idx == 1 else "PRESENT"
                db.record_attendance(f"ATT-DEMO-{idx}-{r_no}", s_id, stu_db_id, status, 0.92)
            elif r_no == "CS-2026-06" and idx == 0:
                db.record_attendance(f"ATT-DEMO-{idx}-{r_no}", s_id, stu_db_id, "PRESENT", 0.91)

    print("   ✓ Historical sessions & attendance patterns seeded for AI analytics.")

    # 3. Create 1 Live Active Demo Session
    print("\n[4/4] Creating Live Classroom Session for Active Demo...")
    live_start = datetime.now()
    live_ok, live_msg, live_sess = session_mgr.create_session(
        subject="High Performance Edge AI & Computer Vision",
        department="COMPUTER SCIENCE",
        year=4,
        section="A",
        room="AUDITORIUM-101",
        faculty_name="Prof. Andrew Ng",
        start_time=live_start,
        regular_window_minutes=15,
        late_window_minutes=30
    )
    if live_ok:
        print(f"   ✓ LIVE DEMO SESSION CREATED:")
        print(f"     Subject     : {live_sess['subject']}")
        print(f"     Session Code: {live_sess['session_code']}")
        print(f"     Projector QR: {live_sess['qr_image_path']}")
        print(f"     Window      : 15 min PRESENT | 30 min LATE")

    # Seed one demo proxy mismatch event for security panel
    if seeded_students:
        db.log_audit_event(
            session_id=live_sess["id"] if live_ok else 1,
            event_type="IDENTITY_MISMATCH",
            severity="WARNING",
            result="FLAGGED",
            reason="Verification mismatch: QR belongs to CS-2026-02 (Alan Turing) but recognized face is CS-2026-01 (Margaret Hamilton).",
            student_id=seeded_students[0][0]
        )

    print("\n" + "=" * 80)
    print("🎉 SIH DEMONSTRATION DATA SEEDING COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    seed_sih_demo_data()
