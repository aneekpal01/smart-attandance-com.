"""
SmartAttend-AI: FastAPI Session Routes (Step 9)
==============================================
Endpoints for classroom session lifecycle: creation, active status,
QR code serving, closing, and history.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database.db_manager import DatabaseManager
from ai.attendance.session_manager import SessionManager

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])
db = DatabaseManager()
session_mgr = SessionManager(db_manager=db)


class CreateSessionRequest(BaseModel):
    subject: str = Field(..., example="Operating Systems")
    department: str = Field("CSE", example="CSE")
    year: int = Field(..., ge=1, le=4, example=3)
    section: Optional[str] = Field("", example="")
    room: str = Field("Room-101", example="Room-101")
    faculty_name: str = Field(..., example="Prof. Andrew Tanenbaum")
    start_time: Optional[str] = None
    regular_window_minutes: int = Field(10, ge=1, le=120)
    late_window_minutes: int = Field(20, ge=1, le=240)


@router.post("/create")
def create_session(payload: CreateSessionRequest):
    """Creates a new classroom attendance session and generates temporary session QR."""
    start_dt = datetime.fromisoformat(payload.start_time) if payload.start_time else datetime.now()
    
    success, msg, session_data = session_mgr.create_session(
        subject=payload.subject,
        department=payload.department,
        year=payload.year,
        section=payload.section,
        room=payload.room,
        faculty_name=payload.faculty_name,
        start_time=start_dt,
        regular_window_minutes=payload.regular_window_minutes,
        late_window_minutes=payload.late_window_minutes
    )

    if not success:
        raise HTTPException(status_code=400, detail=msg)

    return {
        "success": True,
        "message": msg,
        "session": session_data
    }


@router.get("/active")
def get_active_sessions():
    """Lists all currently active classroom sessions."""
    active = db.list_active_sessions()
    # Enrich with summary counts and window status
    now = datetime.now()
    enriched = []
    for s in active:
        summary = db.get_session_attendance_summary(s["id"])
        _, timing_status = session_mgr.evaluate_timing_status(s, now)
        enriched.append({
            **s,
            "timing_status": timing_status,
            "present_count": summary["present_count"] if summary else 0,
            "late_count": summary["late_count"] if summary else 0,
            "absent_count": summary["absent_count"] if summary else 0,
            "rejected_count": summary["rejected_count"] if summary else 0,
            "total_students": summary["total_registered"] if summary else 0
        })
    return {"sessions": enriched, "count": len(enriched)}


@router.get("/history")
def get_session_history(limit: int = Query(50, ge=1, le=200)):
    """Returns past and completed sessions with summary stats."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,))
        all_sessions = [dict(r) for r in cursor.fetchall()]

    history = []
    for s in all_sessions:
        summary = db.get_session_attendance_summary(s["id"])
        history.append({
            **s,
            "present_count": summary["present_count"] if summary else 0,
            "late_count": summary["late_count"] if summary else 0,
            "absent_count": summary["absent_count"] if summary else 0,
            "rejected_count": summary["rejected_count"] if summary else 0,
            "total_students": summary["total_registered"] if summary else 0
        })
    return {"history": history, "total": len(history)}


@router.get("/{session_id}")
def get_session_details(session_id: int):
    """Retrieves full details for a session including timing countdown and summary."""
    session = db.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    now = datetime.now()
    _, timing_status = session_mgr.evaluate_timing_status(session, now)
    summary = db.get_session_attendance_summary(session_id)

    # Expiration time remaining calculation
    end_dt = datetime.fromisoformat(session["end_time"])
    remaining_seconds = max(0, int((end_dt - now).total_seconds()))

    qr_path = Path(__file__).resolve().parent.parent.parent / "database" / "qr_codes" / f"session_{session['session_code']}.png"
    has_qr = qr_path.exists()

    return {
        "session": session,
        "timing_status": timing_status,
        "remaining_seconds": remaining_seconds,
        "summary": summary,
        "has_qr_image": has_qr,
        "qr_image_url": f"/api/sessions/{session_id}/qr-image" if has_qr else None
    }


@router.get("/{session_id}/qr-image")
def get_session_qr_image(session_id: int):
    """Serves the generated session QR code PNG image."""
    session = db.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    qr_path = Path(__file__).resolve().parent.parent.parent / "database" / "qr_codes" / f"session_{session['session_code']}.png"
    if not qr_path.exists():
        raise HTTPException(status_code=404, detail="QR image file not found.")

    return FileResponse(str(qr_path), media_type="image/png")


@router.post("/{session_id}/close")
def close_session(session_id: int):
    """Closes an active classroom session."""
    success, msg = db.close_session(session_id)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    
    db.log_audit_event(
        session_id=session_id,
        event_type="SESSION_CLOSED",
        severity="INFO",
        result="SUCCESS",
        reason="Session closed by faculty via Dashboard."
    )
    return {"success": True, "message": msg}


@router.delete("/clear-all")
def clear_all_sessions():
    """Permanently purges all sessions, attendance records, and audit events."""
    success = db.clear_all_sessions()
    if not success:
        raise HTTPException(status_code=400, detail="Failed to purge sessions.")
    return {"success": True, "message": "All session archives and attendance records cleared successfully."}


@router.delete("/{session_id}")
def delete_session(session_id: int):
    """Permanently deletes a classroom session and its associated records."""
    success = db.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete session.")
    return {"success": True, "message": "Session deleted successfully."}
