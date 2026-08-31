"""
SmartAttend-AI: FastAPI Security & Anti-Proxy Routes (Step 9)
============================================================
Endpoints for security summaries, anti-proxy event feeds, and telemetry.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from database.db_manager import DatabaseManager
from ai.security.audit_service import SecurityAuditService

router = APIRouter(prefix="/api/security", tags=["Security"])
db = DatabaseManager()
sec_service = SecurityAuditService(db_manager=db)


@router.get("/summary/{session_id}")
def get_session_security_summary(session_id: int):
    """Returns security attempt statistics and suspicious activity counts for a session."""
    session = db.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    report = sec_service.get_session_security_report(session_id)
    return {
        "session": session,
        "security_summary": report["summary"],
        "recent_events": report["recent_audit_events"]
    }


@router.get("/suspicious")
def get_suspicious_activity_feed(limit: int = Query(50, ge=1, le=200)):
    """Returns recent suspicious, high-severity events for faculty review."""
    events = sec_service.get_flagged_suspicious_events(limit=limit)
    return {
        "suspicious_events": events,
        "count": len(events)
    }
