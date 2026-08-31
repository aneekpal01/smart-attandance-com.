"""
SmartAttend-AI: Student Registration CLI Utility
Allows quick registration of students and automatic QR code generation.
"""

import sys
from pathlib import Path

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from ai.face_recognition.enrollment_service import StudentEnrollmentService
from database.db_manager import DatabaseManager


def register_cli():
    print("=" * 65)
    print("🎓 SmartAttend-AI: Student Registration CLI")
    print("=" * 65)

    service = StudentEnrollmentService()

    if len(sys.argv) >= 6:
        student_id = sys.argv[1]
        full_name = sys.argv[2]
        department = sys.argv[3]
        year = int(sys.argv[4])
        section = sys.argv[5]
    else:
        print("Please enter student details:")
        student_id = input("Student ID / Roll Number (e.g. CS2026-001): ").strip()
        full_name = input("Full Name (e.g. John Doe): ").strip()
        department = input("Department (e.g. Computer Science): ").strip()
        year_str = input("Year (1-4): ").strip()
        section = input("Section (e.g. A): ").strip()
        
        try:
            year = int(year_str)
        except ValueError:
            print("[ERROR] Year must be a number.")
            return

    success, msg, stu_data = service.register_new_student(
        student_id=student_id,
        full_name=full_name,
        department=department,
        year=year,
        section=section
    )

    if not success:
        print(f"\n[FAILED] {msg}")
        return

    print("\n" + "=" * 65)
    print("✅ STUDENT REGISTRATION SUCCESSFUL!")
    print("=" * 65)
    print(f"Student ID : {stu_data['student_id']}")
    print(f"Full Name  : {stu_data['full_name']}")
    print(f"Department : {stu_data['department']}")
    print(f"Year / Sec : Year {stu_data['year']} - Section {stu_data['section']}")
    print(f"QR Token   : {stu_data['qr_token']} (Random Unique ID)")
    print(f"QR Image   : {stu_data['qr_image_path']}")
    print("=" * 65)
    print("\n[NEXT STEP] Run the interactive enrollment app to scan this QR & enroll face:")
    print("python -m ai.face_recognition.interactive_enrollment")


if __name__ == "__main__":
    register_cli()
