"""
SmartAttend-AI: FastAPI Attendance Routes (Step 9)
=================================================
Endpoints for live attendance monitoring, cohort rosters, and CSV exports.
"""

import io
import csv
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Response, Query
from pydantic import BaseModel, Field

from database.db_manager import DatabaseManager
from ai.security.audit_service import SecurityAuditService
from ai.liveness.detector import LivenessResult, LivenessState
from ai.face_recognition.bg_remover import PythonBackgroundRemover

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])
db = DatabaseManager()
sec_service = SecurityAuditService(db_manager=db)
bg_remover = PythonBackgroundRemover()


class ManualVerifyRequest(BaseModel):
    session_code: str
    student_qr_token: str
    student_id: Optional[str] = None
    similarity_score: float = 0.95
    is_live: bool = True


@router.get("/session/{session_id}")
def get_session_attendance(session_id: int):
    """
    Returns live attendance records and full cohort status for a session.
    Zero raw face embeddings or sensitive biometric data returned.
    """
    summary = db.get_session_attendance_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found or cohort unavailable.")

    # Marked records
    records = db.get_session_attendance_records(session_id)

    # Build comprehensive student attendance list
    return {
        "session": summary["session"],
        "counts": {
            "total_registered": summary["total_registered"],
            "present_count": summary["present_count"],
            "late_count": summary["late_count"],
            "absent_count": summary["absent_count"],
            "rejected_count": summary["rejected_count"],
            "attendance_rate": round(
                ((summary["present_count"] + summary["late_count"]) / max(1, summary["total_registered"])) * 100, 1
            )
        },
        "records": records,
        "present_students": summary["present_students"],
        "late_students": summary["late_students"],
        "absent_students": summary["absent_students"]
    }


@router.get("/session/{session_id}/export-csv")
def export_attendance_csv(session_id: int):
    """
    Generates and streams a downloadable CSV report for faculty.
    Strictly excludes biometric vectors and raw image telemetry.
    """
    summary = db.get_session_attendance_summary(session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Session not found.")

    session = summary["session"]
    records = db.get_session_attendance_records(session_id)
    marked_map = {r["roll_no"]: r for r in records}

    output = io.StringIO()
    writer = csv.writer(output)

    # Header metadata
    writer.writerow(["SmartAttend-AI - Classroom Attendance Report"])
    writer.writerow(["Subject", session["subject"]])
    writer.writerow(["Session Code", session["session_code"]])
    writer.writerow(["Room", session["room"]])
    writer.writerow(["Faculty", session["faculty_name"]])
    writer.writerow(["Cohort", f"{session['department']} Year {session['year']} Section {session['section']}"])
    writer.writerow(["Date", session["start_time"][:10]])
    writer.writerow([])

    # Table columns
    writer.writerow([
        "Roll Number",
        "Student Name",
        "Status",
        "Verification Method",
        "Similarity Score",
        "Timestamp"
    ])

    # Present students
    for p in summary["present_students"]:
        rec = marked_map.get(p["student_id"], {})
        writer.writerow([
            p["student_id"],
            p["full_name"],
            "PRESENT",
            rec.get("verification_method", "QR_FACE_LIVENESS"),
            f"{p.get('similarity', 0.0):.2f}",
            p.get("timestamp", "")
        ])

    # Late students
    for l in summary["late_students"]:
        rec = marked_map.get(l["student_id"], {})
        writer.writerow([
            l["student_id"],
            l["full_name"],
            "LATE",
            rec.get("verification_method", "QR_FACE_LIVENESS"),
            f"{l.get('similarity', 0.0):.2f}",
            l.get("timestamp", "")
        ])

    # Absent students
    for a in summary["absent_students"]:
        writer.writerow([
            a["student_id"],
            a["full_name"],
            "ABSENT",
            "N/A",
            "N/A",
            "N/A"
        ])

    filename = f"Attendance_{session['session_code']}_{session['subject'].replace(' ', '_')}.csv"
    csv_content = output.getvalue()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.post("/verify")
def verify_attendance_endpoint(payload: ManualVerifyRequest):
    """
    Executes secure attendance verification via the Step 8 atomic pipeline.
    """
    student = None
    if payload.student_id:
        student = db.get_student_by_id(payload.student_id)

    live_res = LivenessResult(
        state=LivenessState.LIVE if payload.is_live else LivenessState.SPOOF,
        liveness_score=0.92 if payload.is_live else 0.10,
        confidence=0.95,
        reason="LIVE_VERIFIED" if payload.is_live else "SPOOF_DETECTED"
    )

    success, msg, data = sec_service.execute_secure_attendance_transaction(
        session_code_or_token=payload.session_code,
        student_qr_token=payload.student_qr_token,
        recognized_student=student,
        similarity_score=payload.similarity_score,
        is_recognized=True if student else False,
        liveness_result=live_res
    )

    if not success:
        return {"success": False, "message": msg, "data": data}

    return {"success": True, "message": msg, "data": data}


class ManualMarkRequest(BaseModel):
    session_id: int
    student_id: int
    status: str = Field("PRESENT", example="PRESENT")
    reason: Optional[str] = "MANUAL_FACULTY_OVERRIDE"


@router.post("/manual-mark")
def manual_mark_attendance(payload: ManualMarkRequest):
    """Allows faculty to manually add or update attendance for any student in a session."""
    success, msg = db.manual_mark_attendance(
        session_id=payload.session_id,
        student_id=payload.student_id,
        status=payload.status,
        reason=payload.reason or "MANUAL_FACULTY_OVERRIDE"
    )
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.delete("/session/{session_id}/student/{student_id}")
def delete_student_attendance(session_id: int, student_id: int):
    """Removes a student's attendance record from a session."""
    success = db.delete_attendance_record(session_id, student_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete attendance record.")
    return {"success": True, "message": "Attendance record deleted successfully."}


class MobileCheckInRequest(BaseModel):
    session_code: str
    student_id: str
    token: Optional[str] = None
    face_image_base64: Optional[str] = None


@router.post("/mobile-checkin")
def mobile_checkin_endpoint(payload: MobileCheckInRequest):
    """
    Direct mobile browser self-checkin when student scans classroom projector QR.
    """
    # 1. Validate session
    sess = db.get_session_by_code(payload.session_code)
    if not sess:
        sess = db.get_session_by_token(payload.session_code)
    if not sess:
        raise HTTPException(status_code=404, detail="Classroom session not found or invalid QR code.")

    if sess["status"] != "ACTIVE":
        raise HTTPException(status_code=400, detail="This classroom session has already been CLOSED by faculty.")

    # 2. Evaluate window timing
    now = datetime.now()
    end_dt = datetime.fromisoformat(sess["end_time"])
    start_dt = datetime.fromisoformat(sess["start_time"])
    reg_window = sess.get("regular_window_minutes", 10)
    
    if now > end_dt:
        raise HTTPException(status_code=400, detail="Attendance window has EXPIRED for this class session.")

    timing_status = "PRESENT" if (now - start_dt).total_seconds() <= (reg_window * 60) else "LATE"

    # 3. Lookup student by Roll / Reg No
    student = db.get_student_by_id(payload.student_id.strip().upper())
    if not student:
        raise HTTPException(
            status_code=404, 
            detail=f"Student with Roll/Reg No '{payload.student_id}' not found in AGEMC directory. Please ask teacher to register you."
        )

    # 4. Check if student matches session cohort (department / year)
    if student["department"].upper() != sess["department"].upper() or int(student["year"]) != int(sess["year"]):
        raise HTTPException(
            status_code=400,
            detail=f"Cohort Mismatch: You belong to {student['department']} Year {student['year']}, but this session is for {sess['department']} Year {sess['year']}."
        )

    # 5. Check if already marked
    existing = db.get_student_session_attendance(sess["id"], student["id"])
    if existing:
        return {
            "success": True,
            "already_marked": True,
            "message": f"Attendance already recorded as {existing['status']}!",
            "data": {
                "student_name": student["full_name"],
                "roll_no": student["student_id"],
                "status": existing["status"],
                "subject": sess["subject"],
                "room": sess["room"]
            }
        }

    # 6. Record attendance
    verification_method = "MOBILE_SELFIE_AI" if payload.face_image_base64 else "MOBILE_WEB_CHECKIN"
    att_code = f"ATT-MOB-{now.strftime('%H%M%S')}-{student['student_id']}"
    rec_ok, rec_msg, rec_id = db.record_attendance(
        attendance_code=att_code,
        session_id=sess["id"],
        student_id=student["id"],
        status=timing_status,
        similarity_score=1.0,
        verification_method=verification_method
    )

    if not rec_ok:
        raise HTTPException(status_code=400, detail=rec_msg)

    # Log to audit trail
    db.log_audit_event(
        session_id=sess["id"],
        student_id=student["id"],
        event_type="MOBILE_SELF_CHECKIN",
        severity="INFO",
        result="SUCCESS",
        similarity_score=1.0,
        reason=f"Student {student['full_name']} ({student['student_id']}) checked in via Mobile QR Portal ({timing_status})."
    )

    return {
        "success": True,
        "already_marked": False,
        "message": f"Attendance marked successfully as {timing_status}!",
        "data": {
            "student_name": student["full_name"],
            "roll_no": student["student_id"],
            "status": timing_status,
            "subject": sess["subject"],
            "room": sess["room"],
            "checkin_time": now.strftime("%H:%M:%S")
        }
    }


class ProcessPhotoRequest(BaseModel):
    image_base64: str


@router.post("/process-biometric-photo")
def process_biometric_photo_endpoint(payload: ProcessPhotoRequest):
    """
    Python-based AI Background Removal endpoint.
    Takes student webcam frame and removes room background using OpenCV GrabCut + YuNet.
    """
    if not payload.image_base64:
        raise HTTPException(status_code=400, detail="No image provided.")

    try:
        res = bg_remover.process_base64(payload.image_base64)
        if not res or not res.get("isolated_retina_base64"):
            return {"success": False, "isolated_retina_base64": payload.image_base64, "isolated_full_base64": payload.image_base64}

        return {
            "success": True,
            "isolated_retina_base64": res["isolated_retina_base64"],
            "isolated_full_base64": res["isolated_full_base64"]
        }
    except Exception as e:
        print(f"[WARN] Python bg removal fallback: {e}")
        return {"success": False, "isolated_retina_base64": payload.image_base64, "isolated_full_base64": payload.image_base64}
