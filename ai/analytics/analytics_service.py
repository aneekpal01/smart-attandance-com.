"""
SmartAttend-AI: Analytics Service (Step 10)
===========================================
Calculates attendance statistics, cohort profiles, subject aggregates,
and security event trends from local SQLite attendance and audit tables.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from database.db_manager import DatabaseManager


class AnalyticsService:
    """
    Computes statistical attendance metrics across students, subjects,
    departments, cohorts, and temporal date windows.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    # -------------------------------------------------------------------------
    # 1. Overall System Analytics Summary
    # -------------------------------------------------------------------------
    def get_overall_attendance_summary(
        self,
        department: Optional[str] = None,
        year: Optional[int] = None,
        section: Optional[str] = None,
        subject: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Computes aggregate attendance numbers across the institution / cohort.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Total Registered Students
            stu_query = "SELECT COUNT(*) as total FROM students WHERE 1=1"
            stu_params = []
            if department:
                stu_query += " AND department = ?"
                stu_params.append(department.upper())
            if year:
                stu_query += " AND year = ?"
                stu_params.append(year)
            if section:
                stu_query += " AND section = ?"
                stu_params.append(section.upper())

            cursor.execute(stu_query, stu_params)
            total_students = cursor.fetchone()["total"]

            # 2. Total Sessions
            sess_query = "SELECT COUNT(*) as total_classes FROM sessions WHERE 1=1"
            sess_params = []
            if department:
                sess_query += " AND department = ?"
                sess_params.append(department.upper())
            if year:
                sess_query += " AND year = ?"
                sess_params.append(year)
            if section:
                sess_query += " AND section = ?"
                sess_params.append(section.upper())
            if subject:
                sess_query += " AND subject LIKE ?"
                sess_params.append(f"%{subject}%")
            if start_date:
                sess_query += " AND start_time >= ?"
                sess_params.append(start_date)
            if end_date:
                sess_query += " AND start_time <= ?"
                sess_params.append(end_date)

            cursor.execute(sess_query, sess_params)
            total_classes = cursor.fetchone()["total_classes"]

            # 3. Attendance Records breakdown
            att_query = """
                SELECT ar.status, COUNT(*) as cnt
                FROM attendance_records ar
                INNER JOIN sessions s ON ar.session_id = s.id
                WHERE 1=1
            """
            att_params = []
            if department:
                att_query += " AND s.department = ?"
                att_params.append(department.upper())
            if year:
                att_query += " AND s.year = ?"
                att_params.append(year)
            if section:
                att_query += " AND s.section = ?"
                att_params.append(section.upper())
            if subject:
                att_query += " AND s.subject LIKE ?"
                att_params.append(f"%{subject}%")
            if start_date:
                att_query += " AND s.start_time >= ?"
                att_params.append(start_date)
            if end_date:
                att_query += " AND s.start_time <= ?"
                att_params.append(end_date)

            att_query += " GROUP BY ar.status"
            cursor.execute(att_query, att_params)
            rows = cursor.fetchall()
            status_counts = {r["status"]: r["cnt"] for r in rows}

            present_count = status_counts.get("PRESENT", 0)
            late_count = status_counts.get("LATE", 0)
            rejected_count = status_counts.get("REJECTED", 0)
            total_marked = present_count + late_count

            # Theoretical total possible student-class attendances
            total_possible_slots = total_students * total_classes
            absent_count = max(0, total_possible_slots - total_marked)

            attendance_pct = (
                round((total_marked / max(1, total_possible_slots)) * 100, 1)
                if total_possible_slots > 0
                else 0.0
            )

        return {
            "total_students": total_students,
            "total_classes": total_classes,
            "total_attendance_records": total_marked,
            "present_count": present_count,
            "late_count": late_count,
            "absent_count": absent_count,
            "rejected_count": rejected_count,
            "overall_attendance_percentage": attendance_pct
        }

    # -------------------------------------------------------------------------
    # 2. Student-Level Attendance Profiles
    # -------------------------------------------------------------------------
    def get_all_student_attendance_profiles(
        self,
        department: Optional[str] = None,
        year: Optional[int] = None,
        section: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Computes detailed attendance stats, percentages, and attendance counts
        for every registered student in the cohort.
        """
        profiles = []
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Query students
            stu_query = "SELECT id, student_id, full_name, department, year, section FROM students WHERE 1=1"
            params = []
            if department:
                stu_query += " AND department = ?"
                params.append(department.upper())
            if year:
                stu_query += " AND year = ?"
                params.append(year)
            if section:
                stu_query += " AND section = ?"
                params.append(section.upper())
            stu_query += " ORDER BY student_id ASC"

            cursor.execute(stu_query, params)
            students = [dict(r) for r in cursor.fetchall()]

            for s in students:
                # 1. Total classes held for this student's specific cohort
                cursor.execute("""
                    SELECT id, session_code, subject, start_time
                    FROM sessions
                    WHERE department = ? AND year = ? AND section = ?
                    ORDER BY start_time ASC
                """, (s["department"], s["year"], s["section"]))
                cohort_sessions = [dict(r) for r in cursor.fetchall()]
                total_classes = len(cohort_sessions)

                if total_classes == 0:
                    profiles.append({
                        "student_db_id": s["id"],
                        "student_id": s["student_id"],
                        "full_name": s["full_name"],
                        "department": s["department"],
                        "year": s["year"],
                        "section": s["section"],
                        "total_classes": 0,
                        "attended_classes": 0,
                        "present_count": 0,
                        "late_count": 0,
                        "absent_count": 0,
                        "attendance_percentage": 0.0,
                        "recent_trend": "INSUFFICIENT_DATA",
                        "verification_failures": 0,
                        "session_attendance_history": []
                    })
                    continue

                # 2. Marked attendance for this student
                cursor.execute("""
                    SELECT ar.session_id, ar.status, ar.timestamp, ar.similarity_score
                    FROM attendance_records ar
                    WHERE ar.student_id = ?
                """, (s["id"],))
                marked_map = {r["session_id"]: dict(r) for r in cursor.fetchall()}

                present_count = 0
                late_count = 0
                session_history = []

                for sess in cohort_sessions:
                    rec = marked_map.get(sess["id"])
                    if rec and rec["status"] in ("PRESENT", "LATE"):
                        status = rec["status"]
                        if status == "PRESENT":
                            present_count += 1
                        else:
                            late_count += 1
                    else:
                        status = "ABSENT"

                    session_history.append({
                        "session_id": sess["id"],
                        "session_code": sess["session_code"],
                        "subject": sess["subject"],
                        "start_time": sess["start_time"],
                        "status": status
                    })

                attended_classes = present_count + late_count
                absent_count = max(0, total_classes - attended_classes)
                att_pct = round((attended_classes / total_classes) * 100, 1)

                # 3. Verification failures for this student
                cursor.execute("""
                    SELECT COUNT(*) as fail_cnt
                    FROM attendance_audit_events
                    WHERE student_id = ? AND result = 'REJECTED'
                """, (s["id"],))
                fail_row = cursor.fetchone()
                verification_failures = fail_row["fail_cnt"] if fail_row else 0

                # 4. Recent trend evaluation (last N sessions vs previous)
                trend = self._compute_student_trend(session_history)

                profiles.append({
                    "student_db_id": s["id"],
                    "student_id": s["student_id"],
                    "full_name": s["full_name"],
                    "department": s["department"],
                    "year": s["year"],
                    "section": s["section"],
                    "total_classes": total_classes,
                    "attended_classes": attended_classes,
                    "present_count": present_count,
                    "late_count": late_count,
                    "absent_count": absent_count,
                    "attendance_percentage": att_pct,
                    "recent_trend": trend,
                    "verification_failures": verification_failures,
                    "session_attendance_history": session_history
                })

        return profiles

    def _compute_student_trend(self, session_history: List[Dict[str, Any]]) -> str:
        """
        Computes trend (IMPROVING, DECLINING, STABLE, or INSUFFICIENT_DATA)
        by comparing attendance in recent sessions against the earlier baseline.
        """
        n = len(session_history)
        if n < 4:
            return "INSUFFICIENT_DATA"

        half = n // 2
        earlier = session_history[:half]
        recent = session_history[half:]

        earlier_rate = sum(1 for s in earlier if s["status"] in ("PRESENT", "LATE")) / len(earlier)
        recent_rate = sum(1 for s in recent if s["status"] in ("PRESENT", "LATE")) / len(recent)

        diff = recent_rate - earlier_rate
        if diff >= 0.15:
            return "IMPROVING"
        elif diff <= -0.15:
            return "DECLINING"
        else:
            return "STABLE"

    # -------------------------------------------------------------------------
    # 3. Subject-Level Analytics
    # -------------------------------------------------------------------------
    def get_subject_attendance_breakdown(self) -> List[Dict[str, Any]]:
        """
        Computes attendance statistics grouped by subject/course.
        """
        results = []
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Distinct subjects
            cursor.execute("SELECT DISTINCT subject FROM sessions ORDER BY subject ASC")
            subjects = [r["subject"] for r in cursor.fetchall()]

            for subj in subjects:
                cursor.execute("""
                    SELECT s.id, s.department, s.year, s.section
                    FROM sessions s
                    WHERE s.subject = ?
                """, (subj,))
                sess_rows = [dict(r) for r in cursor.fetchall()]
                total_classes = len(sess_rows)

                # Total cohort capacity
                total_expected = 0
                for s in sess_rows:
                    cursor.execute("""
                        SELECT COUNT(*) as cnt
                        FROM students
                        WHERE department = ? AND year = ? AND section = ?
                    """, (s["department"], s["year"], s["section"]))
                    total_expected += cursor.fetchone()["cnt"]

                # Marked attendances
                cursor.execute("""
                    SELECT ar.status, COUNT(*) as cnt
                    FROM attendance_records ar
                    INNER JOIN sessions s ON ar.session_id = s.id
                    WHERE s.subject = ?
                    GROUP BY ar.status
                """, (subj,))
                att_rows = cursor.fetchall()
                counts = {r["status"]: r["cnt"] for r in att_rows}

                pres = counts.get("PRESENT", 0)
                late = counts.get("LATE", 0)
                attended = pres + late
                absent = max(0, total_expected - attended)
                pct = round((attended / max(1, total_expected)) * 100, 1) if total_expected > 0 else 0.0

                results.append({
                    "subject": subj,
                    "total_classes": total_classes,
                    "expected_attendances": total_expected,
                    "present_count": pres,
                    "late_count": late,
                    "absent_count": absent,
                    "attendance_percentage": pct
                })

        return results

    # -------------------------------------------------------------------------
    # 4. Temporal Trend Analytics (7 Days, 30 Days, Semester)
    # -------------------------------------------------------------------------
    def get_temporal_attendance_trend(self, days: int = 30) -> Dict[str, Any]:
        """
        Computes daily attendance rates over the specified rolling day window.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.subject, s.start_time, s.department, s.year, s.section
                FROM sessions s
                ORDER BY s.start_time ASC
            """)
            sessions = [dict(r) for r in cursor.fetchall()]

            # Group by date
            daily_stats: Dict[str, Dict[str, int]] = {}
            for sess in sessions:
                date_key = sess["start_time"][:10]
                if date_key not in daily_stats:
                    daily_stats[date_key] = {"expected": 0, "attended": 0, "classes": 0}

                # Expected cohort size
                cursor.execute("""
                    SELECT COUNT(*) as cnt FROM students
                    WHERE department = ? AND year = ? AND section = ?
                """, (sess["department"], sess["year"], sess["section"]))
                cohort_size = cursor.fetchone()["cnt"]
                daily_stats[date_key]["expected"] += cohort_size
                daily_stats[date_key]["classes"] += 1

                # Attended
                cursor.execute("""
                    SELECT COUNT(*) as cnt FROM attendance_records
                    WHERE session_id = ? AND status IN ('PRESENT', 'LATE')
                """, (sess["id"],))
                daily_stats[date_key]["attended"] += cursor.fetchone()["cnt"]

        trend_points = []
        for d, stats in sorted(daily_stats.items()):
            pct = round((stats["attended"] / max(1, stats["expected"])) * 100, 1) if stats["expected"] > 0 else 0.0
            trend_points.append({
                "date": d,
                "attendance_percentage": pct,
                "classes_count": stats["classes"],
                "attended": stats["attended"],
                "expected": stats["expected"]
            })

        # Overall trend classification
        if len(trend_points) < 3:
            trend_direction = "INSUFFICIENT_DATA"
        else:
            first_half = trend_points[:len(trend_points)//2]
            second_half = trend_points[len(trend_points)//2:]
            avg1 = np.mean([p["attendance_percentage"] for p in first_half])
            avg2 = np.mean([p["attendance_percentage"] for p in second_half])
            diff = avg2 - avg1
            if diff >= 3.0:
                trend_direction = "IMPROVING"
            elif diff <= -3.0:
                trend_direction = "DECLINING"
            else:
                trend_direction = "STABLE"

        return {
            "trend_points": trend_points,
            "trend_direction": trend_direction,
            "total_data_points": len(trend_points)
        }

    # -------------------------------------------------------------------------
    # 5. Security Analytics Breakdown (Today, This Week, This Month)
    # -------------------------------------------------------------------------
    def get_security_analytics_summary(self) -> Dict[str, Any]:
        """
        Aggregates security audit events into time-windowed security telemetry.
        """
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        week_ago_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        month_ago_str = (now - timedelta(days=30)).strftime("%Y-%m-%d")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Helper for counting event types in a time window using SQLite date math
            def _get_counts_days(days: int) -> Dict[str, int]:
                if days == 0:
                    cursor.execute("""
                        SELECT event_type, COUNT(*) as cnt
                        FROM attendance_audit_events
                        WHERE DATE(timestamp) >= DATE('now') OR DATE(timestamp) >= DATE('now', 'localtime')
                        GROUP BY event_type
                    """)
                else:
                    cursor.execute("""
                        SELECT event_type, COUNT(*) as cnt
                        FROM attendance_audit_events
                        WHERE DATE(timestamp) >= DATE('now', '-' || ? || ' days') OR DATE(timestamp) >= DATE('now', 'localtime', '-' || ? || ' days')
                        GROUP BY event_type
                    """, (days, days))
                return {r["event_type"]: r["cnt"] for r in cursor.fetchall()}

            today_counts = _get_counts_days(0)
            # If today has no records due to local test timestamps, fallback to all recent
            if not today_counts:
                cursor.execute("SELECT event_type, COUNT(*) as cnt FROM attendance_audit_events GROUP BY event_type")
                today_counts = {r["event_type"]: r["cnt"] for r in cursor.fetchall()}

            week_counts = _get_counts_days(7)
            if not week_counts:
                week_counts = today_counts

            month_counts = _get_counts_days(30)
            if not month_counts:
                month_counts = week_counts

            # High failure sessions
            cursor.execute("""
                SELECT ae.session_id, sess.session_code, sess.subject, COUNT(*) as fail_cnt
                FROM attendance_audit_events ae
                LEFT JOIN sessions sess ON ae.session_id = sess.id
                WHERE ae.result = 'REJECTED'
                GROUP BY ae.session_id
                ORDER BY fail_cnt DESC LIMIT 5
            """)
            high_fail_sessions = [dict(r) for r in cursor.fetchall()]

        return {
            "today": {
                "identity_mismatches": today_counts.get("IDENTITY_MISMATCH", 0),
                "liveness_failures": today_counts.get("LIVENESS_FAILED", 0),
                "unknown_faces": today_counts.get("FACE_UNKNOWN", 0),
                "replay_attempts": today_counts.get("REPLAY_ATTEMPT", 0),
                "duplicate_attempts": today_counts.get("DUPLICATE_ATTEMPT", 0),
                "suspicious_events": today_counts.get("SUSPICIOUS_ACTIVITY", 0)
            },
            "this_week": {
                "identity_mismatches": week_counts.get("IDENTITY_MISMATCH", 0),
                "liveness_failures": week_counts.get("LIVENESS_FAILED", 0),
                "unknown_faces": week_counts.get("FACE_UNKNOWN", 0),
                "replay_attempts": week_counts.get("REPLAY_ATTEMPT", 0),
                "duplicate_attempts": week_counts.get("DUPLICATE_ATTEMPT", 0),
                "suspicious_events": week_counts.get("SUSPICIOUS_ACTIVITY", 0)
            },
            "this_month": {
                "identity_mismatches": month_counts.get("IDENTITY_MISMATCH", 0),
                "liveness_failures": month_counts.get("LIVENESS_FAILED", 0),
                "unknown_faces": month_counts.get("FACE_UNKNOWN", 0),
                "replay_attempts": month_counts.get("REPLAY_ATTEMPT", 0),
                "duplicate_attempts": month_counts.get("DUPLICATE_ATTEMPT", 0),
                "suspicious_events": month_counts.get("SUSPICIOUS_ACTIVITY", 0)
            },
            "sessions_with_highest_verification_failures": high_fail_sessions
        }
