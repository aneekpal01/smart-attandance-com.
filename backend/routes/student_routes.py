"""
SmartAttend-AI: FastAPI Student Routes
======================================
Endpoints for student directory, registration, QR image serving, and student deletion.
Zero biometric data exposure.
"""

from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database.db_manager import DatabaseManager
from ai.face_recognition.qr_manager import QRManager

router = APIRouter(prefix="/api/students", tags=["Students"])
db = DatabaseManager()
qr_mgr = QRManager()


class StudentRegisterRequest(BaseModel):
    student_id: str = Field(..., description="Roll Number or Registration Number", example="AGEMC-CSE-2026-01")
    full_name: str = Field(..., example="Grace Hopper")
    department: str = Field("CSE", example="CSE")
    year: int = Field(..., ge=1, le=4, example=3)
    section: Optional[str] = Field("", example="")


@router.get("/")
def list_students(
    search: Optional[str] = None,
    department: Optional[str] = None,
    year: Optional[int] = None,
    section: Optional[str] = None
):
    """Returns the student roster. Strictly does NOT include raw face embeddings."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT id, student_id, full_name, department, year, section, qr_token, is_enrolled, created_at FROM students WHERE 1=1"
        params = []

        if department:
            query += " AND department = ?"
            params.append(department.upper())
        if year:
            query += " AND year = ?"
            params.append(year)
        if section:
            query += " AND section = ?"
            params.append(section.upper())
        if search:
            query += " AND (student_id LIKE ? OR full_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        students = [dict(r) for r in cursor.fetchall()]

    return {"students": students, "total": len(students)}


@router.post("/register")
def register_student(payload: StudentRegisterRequest):
    """Registers a student profile by Roll/Registration No, generates personal QR token & PNG image."""
    dept = payload.department.upper().strip()
    # Normalize department to CSE, AI, ECE, EE
    dept_map = {
        "COMPUTER SCIENCE": "CSE",
        "COMPUTER SCIENCE & ENGINEERING": "CSE",
        "CSE": "CSE",
        "ARTIFICIAL INTELLIGENCE": "AI",
        "AI": "AI",
        "ELECTRONICS & COMM": "ECE",
        "ELECTRONICS": "ECE",
        "ECE": "ECE",
        "ELECTRICAL ENGG": "EE",
        "ELECTRICAL": "EE",
        "EE": "EE"
    }
    normalized_dept = dept_map.get(dept, dept)

    qr_token = qr_mgr.generate_token()
    success, msg, db_id = db.add_student(
        student_id=payload.student_id.strip().upper(),
        full_name=payload.full_name.strip(),
        department=normalized_dept,
        year=payload.year,
        section=payload.section.strip() if payload.section else "",
        qr_token=qr_token
    )

    if not success:
        raise HTTPException(status_code=400, detail=msg)

    # Generate QR image file on disk
    qr_file = qr_mgr.generate_qr_image(qr_token, payload.student_id)

    return {
        "success": True,
        "message": msg,
        "student_id": payload.student_id,
        "db_id": db_id,
        "qr_token": qr_token,
        "qr_image_url": f"/api/students/{payload.student_id}/qr-image"
    }


@router.get("/{student_id}/qr-image")
def get_student_qr_image(student_id: str):
    """Serves student QR code PNG image."""
    clean_id = student_id.replace("/", "_").replace("\\", "_")
    file_path = qr_mgr.qr_dir / f"{clean_id}_qr.png"
    if not file_path.exists():
        # Fallback to query by student ID from DB and generate on the fly
        stu = db.get_student_by_id(student_id)
        if stu and stu["qr_token"]:
            file_path = qr_mgr.generate_qr_image(stu["qr_token"], student_id)
        else:
            raise HTTPException(status_code=404, detail="Student QR not found.")

    return FileResponse(str(file_path), media_type="image/png")


@router.delete("/{student_id}")
def delete_student(student_id: str):
    """Permanently deletes a student from the directory."""
    success = db.delete_student(student_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete student.")
    return {"success": True, "message": "Student deleted successfully."}
