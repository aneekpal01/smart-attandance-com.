"""
SmartAttend-AI: Faculty Session Management & Attendance CLI (Step 6)
===================================================================
Allows faculty to:
  1. Create classroom attendance sessions & generate temporary session QRs
  2. View active sessions & live attendance counters
  3. Close sessions
  4. Display full summary reports (Present / Late / Absent lists)
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from database.db_manager import DatabaseManager
from ai.attendance.session_manager import SessionManager
from ai.attendance.attendance_engine import AttendanceEngine


def print_banner():
    print("=" * 68)
    print("👨‍🏫 SmartAttend-AI: Faculty Classroom Session Control (Step 6)")
    print("=" * 68)


def create_session_interactive():
    print("\n--- Create New Classroom Attendance Session ---")
    subject = input("Subject Name (e.g. Data Structures & Algorithms): ").strip()
    department = input("Department (e.g. CS, IT, ECE): ").strip().upper()
    year_str = input("Year (1-4): ").strip()
    section = input("Section (e.g. A, B): ").strip().upper()
    room = input("Room / Hall (e.g. Room-302): ").strip()
    faculty_name = input("Faculty Name (e.g. Prof. Alan Turing): ").strip()
    reg_window = input("Regular Window Minutes [default 10]: ").strip()
    late_window = input("Late Window Minutes [default 20]: ").strip()

    try:
        year = int(year_str)
        reg_min = int(reg_window) if reg_window else 10
        late_min = int(late_window) if late_window else 20
    except ValueError:
        print("[ERROR] Year and window minutes must be integers.")
        return

    mgr = SessionManager()
    success, msg, session = mgr.create_session(
        subject=subject,
        department=department,
        year=year,
        section=section,
        room=room,
        faculty_name=faculty_name,
        regular_window_minutes=reg_min,
        late_window_minutes=late_min
    )

    if not success:
        print(f"[FAILED] {msg}")
        return

    print("\n" + "=" * 68)
    print("✅ CLASSROOM SESSION CREATED & ACTIVE!")
    print("=" * 68)
    print(f"Session Code   : {session['session_code']}")
    print(f"Subject        : {session['subject']} ({session['department']} Y{session['year']}-{session['section']})")
    print(f"Room           : {session['room']} | Faculty: {session['faculty_name']}")
    print(f"Start Time     : {session['start_time']}")
    print(f"Regular Window : {session['regular_window_minutes']} mins (PRESENT)")
    print(f"Late Window    : {session['late_window_minutes']} mins (LATE)")
    print(f"End Time       : {session['end_time']}")
    print(f"Temporary QR   : {session['qr_image_path']}")
    print("=" * 68)
    print("\n[NEXT STEP] Students can now scan the classroom QR & mark attendance!")


def list_active_sessions():
    db = DatabaseManager()
    sessions = db.list_active_sessions()

    print(f"\n--- Active Classroom Sessions ({len(sessions)}) ---")
    if not sessions:
        print("No active sessions found. Create a new session first.")
        return

    for s in sessions:
        print(f" • [{s['session_code']}] {s['subject']} | Room: {s['room']} | Dept: {s['department']} Y{s['year']}-{s['section']} | Status: {s['status']}")


def view_session_summary():
    code = input("\nEnter Session Code (e.g. SA-SESSION-XXXX): ").strip()
    db = DatabaseManager()
    session = db.get_session_by_code(code)
    if not session:
        print("[ERROR] Session not found.")
        return

    engine = AttendanceEngine(db_manager=db)
    summary = engine.get_session_summary(session["id"])
    if not summary:
        print("[ERROR] Could not generate summary.")
        return

    print("\n" + "=" * 68)
    print(f"📊 ATTENDANCE SUMMARY: {session['subject']} [{session['session_code']}]")
    print("=" * 68)
    print(f"Cohort Details   : {session['department']} Year {session['year']} - Section {session['section']}")
    print(f"Faculty / Room   : {session['faculty_name']} | Room {session['room']}")
    print(f"Total Registered : {summary['total_registered']}")
    print(f"Present Count    : {summary['present_count']} ✅")
    print(f"Late Count       : {summary['late_count']} ⏰")
    print(f"Absent Count     : {summary['absent_count']} ❌")
    print(f"Rejected Tries   : {summary['rejected_count']} ⚠️")
    print("-" * 68)

    print("\n[+] Present Students:")
    for p in summary["present_students"]:
        print(f"   ✓ {p['student_id']}: {p['full_name']} (at {p['timestamp']}, Sim: {p['similarity']:.2f})")

    print("\n[+] Late Students:")
    for l in summary["late_students"]:
        print(f"   ⏰ {l['student_id']}: {l['full_name']} (at {l['timestamp']}, Sim: {l['similarity']:.2f})")

    print("\n[+] Absent Students:")
    for a in summary["absent_students"]:
        print(f"   ✗ {a['student_id']}: {a['full_name']}")
    print("=" * 68)


def close_session_cli():
    code = input("\nEnter Session Code to close: ").strip()
    db = DatabaseManager()
    success, msg = db.close_session(code)
    if success:
        print(f"[OK] {msg}")
    else:
        print(f"[FAILED] {msg}")


def main():
    print_banner()
    while True:
        print("\nFaculty Controls Menu:")
        print(" 1. Create New Classroom Session")
        print(" 2. View Active Sessions")
        print(" 3. View Session Attendance Summary & Absent List")
        print(" 4. Close Session")
        print(" 5. Exit")
        choice = input("\nEnter option (1-5): ").strip()

        if choice == "1":
            create_session_interactive()
        elif choice == "2":
            list_active_sessions()
        elif choice == "3":
            view_session_summary()
        elif choice == "4":
            close_session_cli()
        elif choice == "5":
            print("Exiting Faculty Session Control.")
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
