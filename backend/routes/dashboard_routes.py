"""
SmartAttend-AI: FastAPI Dashboard Overview Routes (Step 9)
=========================================================
Aggregates high-level faculty metrics: Today's sessions, active session,
total enrolled students, attendance rate, and recent security alerts.
"""

from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter
from database.db_manager import DatabaseManager

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
db = DatabaseManager()


@router.get("/overview")
def get_dashboard_overview():
    """Returns top-level KPI metrics for the Faculty Dashboard Home."""
    today_str = datetime.now().strftime("%Y-%m-%d")

    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Total Registered Students
        cursor.execute("SELECT COUNT(*) as total, SUM(is_enrolled) as enrolled FROM students")
        stu_row = cursor.fetchone()
        total_students = stu_row["total"] if stu_row else 0
        enrolled_students = stu_row["enrolled"] if stu_row and stu_row["enrolled"] else 0

        # 2. Today's Sessions
        cursor.execute("SELECT * FROM sessions WHERE start_time LIKE ? ORDER BY id DESC", (f"{today_str}%",))
        today_sessions = [dict(r) for r in cursor.fetchall()]

        # 3. Active Session
        cursor.execute("SELECT * FROM sessions WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1")
        active_row = cursor.fetchone()
        active_session = dict(active_row) if active_row else None

        # 4. Today's Attendance stats across all sessions today
        cursor.execute("""
            SELECT ar.status, COUNT(*) as cnt
            FROM attendance_records ar
            INNER JOIN sessions s ON ar.session_id = s.id
            WHERE ar.timestamp LIKE ?
            GROUP BY ar.status
        """, (f"{today_str}%",))
        att_counts = {r["status"]: r["cnt"] for r in cursor.fetchall()}
        
        present_total = att_counts.get("PRESENT", 0) + att_counts.get("LATE", 0)

        # 5. Security Alerts today
        cursor.execute("""
            SELECT COUNT(*) as alert_count
            FROM attendance_audit_events
            WHERE severity IN ('HIGH', 'WARNING') AND timestamp LIKE ?
        """, (f"{today_str}%",))
        alert_row = cursor.fetchone()
        security_alerts = alert_row["alert_count"] if alert_row else 0

        # 6. Recent Security Events
        cursor.execute("""
            SELECT ae.*, s.student_id as roll_no, s.full_name, sess.subject, sess.session_code
            FROM attendance_audit_events ae
            LEFT JOIN students s ON ae.student_id = s.id
            LEFT JOIN sessions sess ON ae.session_id = sess.id
            WHERE ae.severity IN ('HIGH', 'WARNING')
            ORDER BY ae.id DESC LIMIT 5
        """)
        recent_alerts = [dict(r) for r in cursor.fetchall()]

    # Active session enrichment
    if active_session:
        summary = db.get_session_attendance_summary(active_session["id"])
        if summary:
            active_session["present_count"] = summary["present_count"]
            active_session["late_count"] = summary["late_count"]
            active_session["absent_count"] = summary["absent_count"]
            active_session["total_cohort"] = summary["total_registered"]

    return {
        "today_sessions_count": len(today_sessions),
        "active_session": active_session,
        "total_students": total_students,
        "enrolled_students": enrolled_students,
        "today_present_total": present_total,
        "security_alerts_count": security_alerts,
        "recent_alerts": recent_alerts,
        "system_time": datetime.now().isoformat()
    }
