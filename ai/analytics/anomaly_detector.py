"""
SmartAttend-AI: Local Attendance & Security Anomaly Detector (Step 10)
====================================================================
Identifies statistical anomalies in cohort attendance, unusual student absence streaks,
and abnormal verification failure spikes using explainable metrics.
"""

from typing import Dict, List, Optional, Any
import numpy as np


class AttendanceAnomalyDetector:
    """
    Statistical anomaly detector for attendance and verification behaviors.
    """

    def __init__(self, z_score_threshold: float = 2.0):
        self.z_score_threshold = z_score_threshold

    def detect_anomalies(
        self,
        student_profiles: List[Dict[str, Any]],
        temporal_trends: Dict[str, Any],
        security_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Runs multi-pattern anomaly detection across students, sessions, and security logs.
        """
        anomalies: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # Pattern 1: Sudden Daily Attendance Rate Drops (Z-score check)
        # -------------------------------------------------------------
        trend_points = temporal_trends.get("trend_points", [])
        if len(trend_points) >= 4:
            rates = [p["attendance_percentage"] for p in trend_points]
            mean_rate = float(np.mean(rates))
            std_rate = float(np.std(rates))

            if std_rate > 0.01:
                for p in trend_points:
                    z = (p["attendance_percentage"] - mean_rate) / std_rate
                    if z < -self.z_score_threshold:
                        anomalies.append({
                            "anomaly_type": "SESSION_ATTENDANCE_DROP",
                            "severity": "WARNING",
                            "entity": f"Date {p['date']}",
                            "description": f"Abnormal attendance drop to {p['attendance_percentage']}% on {p['date']} (Baseline Mean: {mean_rate:.1f}%, Z-Score: {z:.2f}).",
                            "metric_value": p["attendance_percentage"]
                        })

        # -------------------------------------------------------------
        # Pattern 2: Severe Student Absence Streaks
        # -------------------------------------------------------------
        for profile in student_profiles:
            history = profile.get("session_attendance_history", [])
            if len(history) >= 3:
                # Check trailing consecutive absences
                consecutive_absent = 0
                for s in reversed(history):
                    if s.get("status") == "ABSENT":
                        consecutive_absent += 1
                    else:
                        break

                if consecutive_absent >= 3:
                    anomalies.append({
                        "anomaly_type": "STUDENT_ABSENCE_STREAK",
                        "severity": "HIGH",
                        "entity": f"{profile['full_name']} ({profile['student_id']})",
                        "description": f"Critical absence streak: {consecutive_absent} consecutive classes missed.",
                        "metric_value": consecutive_absent
                    })

        # -------------------------------------------------------------
        # Pattern 3: Excessive Verification Failures in a Single Session
        # -------------------------------------------------------------
        high_fail_sessions = security_summary.get("sessions_with_highest_verification_failures", [])
        for sess in high_fail_sessions:
            fail_cnt = sess.get("fail_cnt", 0)
            if fail_cnt >= 4:
                anomalies.append({
                    "anomaly_type": "SECURITY_VERIFICATION_SPIKE",
                    "severity": "WARNING",
                    "entity": f"{sess.get('subject', 'Session')} [{sess.get('session_code', '')}]",
                    "description": f"Unusually high verification rejections ({fail_cnt} failed attempts) during this session.",
                    "metric_value": fail_cnt
                })

        return anomalies
