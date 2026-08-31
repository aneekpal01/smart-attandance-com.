"""
SmartAttend-AI: FastAPI Audit Log Routes (Step 9)
================================================
Searchable, filterable audit event logs with date, severity, and event_type filters.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query
from database.db_manager import DatabaseManager

router = APIRouter(prefix="/api/audit", tags=["Audit Log"])
db = DatabaseManager()


@router.get("/events")
def get_audit_events(
    session_id: Optional[int] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    result: Optional[str] = None,
    date_str: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """
    Returns filtered audit events from database.
    Privacy Guarantee: Zero raw images or face embeddings are stored or returned.
    """
    with db.get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT ae.*, s.student_id as roll_no, s.full_name, sess.subject, sess.session_code
            FROM attendance_audit_events ae
            LEFT JOIN students s ON ae.student_id = s.id
            LEFT JOIN sessions sess ON ae.session_id = sess.id
            WHERE 1=1
        """
        params = []

        if session_id:
            query += " AND ae.session_id = ?"
            params.append(session_id)
        if event_type:
            query += " AND ae.event_type = ?"
            params.append(event_type)
        if severity:
            query += " AND ae.severity = ?"
            params.append(severity)
        if result:
            query += " AND ae.result = ?"
            params.append(result)
        if date_str:
            query += " AND ae.timestamp LIKE ?"
            params.append(f"{date_str}%")
        if search:
            query += " AND (ae.reason LIKE ? OR s.student_id LIKE ? OR s.full_name LIKE ? OR sess.session_code LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

        query += " ORDER BY ae.id DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        events = [dict(r) for r in cursor.fetchall()]

    return {
        "events": events,
        "count": len(events)
    }
