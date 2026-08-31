"""
SmartAttend-AI: Local Explainable AI Insights Engine (Step 10)
=============================================================
Transforms database metrics, risk predictions, and temporal trends into
concise, fact-grounded, natural-language insights for faculty.
"""

from typing import Dict, List, Optional, Any


class InsightsEngine:
    """
    Generates explainable, verifiable natural-language insights from SQL analytics.
    Strictly grounds every statement in actual database statistics (Zero hallucinations).
    """

    def generate_insights(
        self,
        overall_summary: Dict[str, Any],
        student_profiles: List[Dict[str, Any]],
        risk_summary: Dict[str, Any],
        subject_breakdown: List[Dict[str, Any]],
        temporal_trends: Dict[str, Any],
        security_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes metrics into a structured list of actionable faculty insights.
        """
        insights: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # Insight 1: Overall Cohort Health
        # -------------------------------------------------------------
        total_classes = overall_summary.get("total_classes", 0)
        overall_pct = overall_summary.get("overall_attendance_percentage", 0.0)

        if total_classes > 0:
            status_desc = "strong" if overall_pct >= 85.0 else ("moderate" if overall_pct >= 75.0 else "concerning")
            insights.append({
                "category": "ATTENDANCE_OVERVIEW",
                "severity": "INFO" if overall_pct >= 75.0 else "WARNING",
                "insight_text": f"Overall institutional attendance stands at {overall_pct}% across {total_classes} recorded class sessions, indicating {status_desc} student participation.",
                "grounding_metric": {
                    "overall_attendance_pct": overall_pct,
                    "total_classes": total_classes,
                    "total_records": overall_summary.get("total_attendance_records", 0)
                }
            })

        # -------------------------------------------------------------
        # Insight 2: Threshold Compliance & At-Risk Students
        # -------------------------------------------------------------
        below_count = risk_summary.get("below_threshold_count", 0)
        high_risk_count = risk_summary.get("high_risk_count", 0)
        req_thresh = risk_summary.get("required_attendance_threshold", 75.0)

        if below_count > 0 or high_risk_count > 0:
            insights.append({
                "category": "STUDENT_RISK",
                "severity": "WARNING" if high_risk_count > 0 else "INFO",
                "insight_text": f"{below_count} student(s) currently fall below the required {req_thresh}% attendance threshold, with {high_risk_count} student(s) classified at HIGH risk of academic penalty.",
                "grounding_metric": {
                    "below_threshold_count": below_count,
                    "high_risk_count": high_risk_count,
                    "threshold_pct": req_thresh
                }
            })
        elif total_classes >= 3:
            insights.append({
                "category": "STUDENT_RISK",
                "severity": "INFO",
                "insight_text": f"All evaluated students are currently meeting the mandatory {req_thresh}% attendance requirement.",
                "grounding_metric": {
                    "total_students": len(student_profiles),
                    "threshold_pct": req_thresh
                }
            })

        # -------------------------------------------------------------
        # Insight 3: Subject Performance Disparity
        # -------------------------------------------------------------
        if len(subject_breakdown) >= 2:
            sorted_subjects = sorted(subject_breakdown, key=lambda x: x["attendance_percentage"], reverse=True)
            best_sub = sorted_subjects[0]
            lowest_sub = sorted_subjects[-1]

            if best_sub["attendance_percentage"] - lowest_sub["attendance_percentage"] >= 5.0:
                insights.append({
                    "category": "SUBJECT_COMPARISON",
                    "severity": "INFO",
                    "insight_text": f"Attendance is highest in '{best_sub['subject']}' ({best_sub['attendance_percentage']}%) and lowest in '{lowest_sub['subject']}' ({lowest_sub['attendance_percentage']}%).",
                    "grounding_metric": {
                        "highest_subject": best_sub["subject"],
                        "highest_pct": best_sub["attendance_percentage"],
                        "lowest_subject": lowest_sub["subject"],
                        "lowest_pct": lowest_sub["attendance_percentage"]
                    }
                })

        # -------------------------------------------------------------
        # Insight 4: Temporal Trajectory
        # -------------------------------------------------------------
        trend_direction = temporal_trends.get("trend_direction", "STABLE")
        if trend_direction == "IMPROVING":
            insights.append({
                "category": "TEMPORAL_TREND",
                "severity": "INFO",
                "insight_text": "Overall attendance trajectory is IMPROVING over recent sessions compared to earlier baselines.",
                "grounding_metric": {"trend_direction": trend_direction}
            })
        elif trend_direction == "DECLINING":
            insights.append({
                "category": "TEMPORAL_TREND",
                "severity": "WARNING",
                "insight_text": "Overall attendance trajectory has been DECLINING over recent sessions. Faculty review recommended.",
                "grounding_metric": {"trend_direction": trend_direction}
            })

        # -------------------------------------------------------------
        # Insight 5: Anti-Proxy & Security Health
        # -------------------------------------------------------------
        this_week_sec = security_summary.get("this_week", {})
        mismatches = this_week_sec.get("identity_mismatches", 0)
        spoofs = this_week_sec.get("liveness_failures", 0)
        replays = this_week_sec.get("replay_attempts", 0)

        total_violations = mismatches + spoofs + replays
        if total_violations > 0:
            insights.append({
                "category": "SECURITY_HEALTH",
                "severity": "WARNING" if total_violations >= 3 else "INFO",
                "insight_text": f"Anti-proxy system intercepted {total_violations} security violations this week ({mismatches} proxy mismatches, {spoofs} photo spoofs, {replays} token replays).",
                "grounding_metric": {
                    "mismatches": mismatches,
                    "spoofs": spoofs,
                    "replays": replays
                }
            })
        else:
            insights.append({
                "category": "SECURITY_HEALTH",
                "severity": "INFO",
                "insight_text": "Zero proxy attempts or spoofing violations detected this week. Verification logs indicate clean student participation.",
                "grounding_metric": {"total_violations": 0}
            })

        return insights
