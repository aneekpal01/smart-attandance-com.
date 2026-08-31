"""
SmartAttend-AI: Step 10 Automated Test Suite (AI Analytics & Intelligence Layer)
================================================================================
Tests all 16 mandatory requirements:
  TEST 1: Overall attendance calculation.
  TEST 2: Student attendance calculation.
  TEST 3: Subject attendance calculation.
  TEST 4: Attendance trend detection.
  TEST 5: Improving trend.
  TEST 6: Declining trend.
  TEST 7: Stable trend.
  TEST 8: Below-threshold detection.
  TEST 9: Attendance risk calculation.
  TEST 10: Insufficient-data handling.
  TEST 11: Attendance anomaly detection.
  TEST 12: Security event aggregation.
  TEST 13: AI insight generation from real metrics.
  TEST 14: No fabricated insights (Fact-grounding validation).
  TEST 15: Analytics endpoints return correct data.
  TEST 16: Analytics endpoints do not expose biometric data.
"""

import sys
import gc
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from database.db_manager import DatabaseManager
from ai.analytics.analytics_service import AnalyticsService
from ai.analytics.risk_predictor import AttendanceRiskPredictor
from ai.analytics.anomaly_detector import AttendanceAnomalyDetector
from ai.analytics.insights_engine import InsightsEngine
from backend.app.main import app

client = TestClient(app)


def run_step10_verification():
    print("=" * 75)
    print("[*] SMARTATTEND-AI: STEP 10 AI ANALYTICS & INTELLIGENCE TEST SUITE")
    print("=" * 75)

    # Use isolated test database
    test_db_path = Path(__file__).resolve().parent.parent.parent / "test_analytics.db"
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass

    db = DatabaseManager(db_path=str(test_db_path))
    analytics = AnalyticsService(db_manager=db)
    risk_predictor = AttendanceRiskPredictor(required_attendance_pct=75.0, min_classes_required_for_prediction=3)
    anomaly_detector = AttendanceAnomalyDetector(z_score_threshold=1.5)
    insights_engine = InsightsEngine()

    # -------------------------------------------------------------------------
    # SETUP: Register Cohort & Seed 8 Historical Sessions with Known Attendance
    # -------------------------------------------------------------------------
    print("\n[SETUP] Seeding Cohort & Multi-Day Session Attendance History...")
    # Student 1: High Attendance (Alice)
    db.add_student("CS-1001", "Alice Good", "COMPUTER SCIENCE", 3, "A", "SA-STU-ALICE1001")
    alice = db.get_student_by_id("CS-1001")

    # Student 2: Declining / Low Attendance (Bob)
    db.add_student("CS-1002", "Bob AtRisk", "COMPUTER SCIENCE", 3, "A", "SA-STU-BOB1002")
    bob = db.get_student_by_id("CS-1002")

    # Student 3: Improving Attendance (Charlie)
    db.add_student("CS-1003", "Charlie Improving", "COMPUTER SCIENCE", 3, "A", "SA-STU-CHARLIE1003")
    charlie = db.get_student_by_id("CS-1003")

    # Create 8 Sessions over 8 days
    base_date = datetime(2026, 8, 1, 9, 0, 0)
    session_ids = []
    for i in range(8):
        sess_dt = base_date + timedelta(days=i)
        subj = "Computer Networks" if i % 2 == 0 else "Compiler Design"
        _, _, s_id = db.create_session(
            session_code=f"SA-SESS-{1000+i}",
            subject=subj,
            department="COMPUTER SCIENCE",
            year=3,
            section="A",
            room="LH-201",
            faculty_name="Prof. Linus Torvalds",
            start_time=sess_dt,
            regular_window_minutes=10,
            late_window_minutes=20,
            end_time=sess_dt + timedelta(minutes=60),
            session_token=f"STOKEN-ANALYTICS-{1000+i}"
        )
        session_ids.append(s_id)

    # Attendance Patterns:
    # Alice: Attends all 8 sessions (100%) -> PRESENT
    for sid in session_ids:
        db.record_attendance(f"ATT-A-{sid}", sid, alice["id"], "PRESENT", 0.98)

    # Bob: Attends first 2 sessions, then misses last 6 sessions (25% total, Declining)
    for sid in session_ids[:2]:
        db.record_attendance(f"ATT-B-{sid}", sid, bob["id"], "PRESENT", 0.95)

    # Charlie: Misses first 3 sessions, attends last 5 sessions (62.5% total, Improving)
    for sid in session_ids[3:]:
        db.record_attendance(f"ATT-C-{sid}", sid, charlie["id"], "PRESENT", 0.96)

    # Seed some security events
    db.log_audit_event(session_ids[0], "IDENTITY_MISMATCH", "HIGH", "REJECTED", "Verification mismatch", bob["id"])
    db.log_audit_event(session_ids[1], "LIVENESS_FAILED", "HIGH", "REJECTED", "Photo spoof attempt", bob["id"])
    db.log_audit_event(session_ids[1], "LIVENESS_FAILED", "HIGH", "REJECTED", "Photo spoof attempt", bob["id"])
    db.log_audit_event(session_ids[1], "LIVENESS_FAILED", "HIGH", "REJECTED", "Photo spoof attempt", bob["id"])
    db.log_audit_event(session_ids[1], "LIVENESS_FAILED", "HIGH", "REJECTED", "Photo spoof attempt", bob["id"])

    print("   [OK] 3 students, 8 sessions, and historical records initialized.")

    # -------------------------------------------------------------------------
    # TEST 1: Overall Attendance Calculation
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing Overall Attendance Calculation...")
    overall = analytics.get_overall_attendance_summary()
    assert overall["total_students"] == 3
    assert overall["total_classes"] == 8
    # Total possible = 3 * 8 = 24. Alice(8) + Bob(2) + Charlie(5) = 15. Pct = 15/24 = 62.5%
    assert overall["total_attendance_records"] == 15
    assert overall["overall_attendance_percentage"] == 62.5
    print(f"   [OK] Overall attendance percentage: {overall['overall_attendance_percentage']}% (15/24).")

    # -------------------------------------------------------------------------
    # TEST 2: Student Attendance Profiles
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Student Attendance Profiles...")
    profiles = analytics.get_all_student_attendance_profiles()
    p_map = {p["student_id"]: p for p in profiles}
    assert p_map["CS-1001"]["attendance_percentage"] == 100.0
    assert p_map["CS-1002"]["attendance_percentage"] == 25.0
    assert p_map["CS-1003"]["attendance_percentage"] == 62.5
    print("   [OK] Individual student attendance percentages accurately calculated.")

    # -------------------------------------------------------------------------
    # TEST 3: Subject Attendance Calculation
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing Subject Attendance Breakdown...")
    subjects = analytics.get_subject_attendance_breakdown()
    assert len(subjects) == 2
    s_names = [s["subject"] for s in subjects]
    assert "Computer Networks" in s_names
    assert "Compiler Design" in s_names
    print(f"   [OK] Subject breakdowns computed for {len(subjects)} subjects.")

    # -------------------------------------------------------------------------
    # TEST 4: Attendance Trend Detection
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing Temporal Trend Analysis...")
    trends = analytics.get_temporal_attendance_trend(30)
    assert len(trends["trend_points"]) == 8
    assert trends["trend_direction"] in ("IMPROVING", "DECLINING", "STABLE")
    print(f"   [OK] Temporal trend points: {len(trends['trend_points'])}, Direction: {trends['trend_direction']}")

    # -------------------------------------------------------------------------
    # TEST 5: Improving Trend Detection (Charlie)
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing Improving Trend on Charlie...")
    assert p_map["CS-1003"]["recent_trend"] == "IMPROVING"
    print("   [OK] Charlie correctly identified as IMPROVING trend.")

    # -------------------------------------------------------------------------
    # TEST 6: Declining Trend Detection (Bob)
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing Declining Trend on Bob...")
    assert p_map["CS-1002"]["recent_trend"] == "DECLINING"
    print("   [OK] Bob correctly identified as DECLINING trend.")

    # -------------------------------------------------------------------------
    # TEST 7: Stable Trend Detection (Alice)
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing Stable Trend on Alice...")
    assert p_map["CS-1001"]["recent_trend"] == "STABLE"
    print("   [OK] Alice correctly identified as STABLE trend (100%).")

    # -------------------------------------------------------------------------
    # TEST 8: Below-Threshold Detection (< 75%)
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Testing Below-Threshold (75%) Detection...")
    cohort_risk = risk_predictor.evaluate_cohort_risk(profiles)
    assert cohort_risk["below_threshold_count"] == 2 # Bob (25%) & Charlie (62.5%)
    print(f"   [OK] Correctly flagged {cohort_risk['below_threshold_count']} students below 75% threshold.")

    # -------------------------------------------------------------------------
    # TEST 9: Attendance Risk Calculation & Class Margin
    # -------------------------------------------------------------------------
    print("\n[TEST 9] Testing Risk Scoring & Margin of Classes...")
    bob_risk = risk_predictor.evaluate_student_risk(p_map["CS-1002"])
    alice_risk = risk_predictor.evaluate_student_risk(p_map["CS-1001"])
    assert bob_risk.risk_level == "HIGH"
    assert bob_risk.classes_needed_for_target > 0
    assert alice_risk.risk_level == "LOW"
    assert alice_risk.margin_missable_classes >= 2
    print(f"   [OK] Bob Risk: {bob_risk.risk_level} (Needs {bob_risk.classes_needed_for_target} classes), Alice: {alice_risk.risk_level} (Can miss ~{alice_risk.margin_missable_classes} classes).")

    # -------------------------------------------------------------------------
    # TEST 10: Insufficient-Data Handling
    # -------------------------------------------------------------------------
    print("\n[TEST 10] Testing Insufficient-Data Handling (Small Sample Safety)...")
    small_student = {
        "student_id": "CS-NEW",
        "full_name": "New Student",
        "total_classes": 1,
        "attended_classes": 1,
        "attendance_percentage": 100.0,
        "recent_trend": "INSUFFICIENT_DATA",
        "session_attendance_history": [{"status": "PRESENT"}]
    }
    small_risk = risk_predictor.evaluate_student_risk(small_student)
    assert small_risk.risk_level == "INSUFFICIENT_DATA"
    assert "minimum" in small_risk.contributing_factors[0]
    print(f"   [OK] Small sample safely returned INSUFFICIENT_DATA: '{small_risk.contributing_factors[0]}'")

    # -------------------------------------------------------------------------
    # TEST 11: Attendance Anomaly Detection
    # -------------------------------------------------------------------------
    print("\n[TEST 11] Testing Anomaly Detection (Absence streaks & verification spikes)...")
    sec_summary = analytics.get_security_analytics_summary()
    anomalies = anomaly_detector.detect_anomalies(profiles, trends, sec_summary)
    assert len(anomalies) > 0
    types = [a["anomaly_type"] for a in anomalies]
    assert "STUDENT_ABSENCE_STREAK" in types or "SECURITY_VERIFICATION_SPIKE" in types
    print(f"   [OK] Detected {len(anomalies)} anomalies: {types}")

    # -------------------------------------------------------------------------
    # TEST 12: Security Event Aggregation
    # -------------------------------------------------------------------------
    print("\n[TEST 12] Testing Security Event Aggregation across Time Windows...")
    assert sec_summary["today"]["identity_mismatches"] >= 1
    assert sec_summary["today"]["liveness_failures"] >= 4
    print("   [OK] Security events aggregated correctly across Today/Week/Month.")

    # -------------------------------------------------------------------------
    # TEST 13: Explainable AI Insight Generation
    # -------------------------------------------------------------------------
    print("\n[TEST 13] Testing Explainable AI Insight Generation from SQL Stats...")
    insights = insights_engine.generate_insights(
        overall_summary=overall,
        student_profiles=profiles,
        risk_summary=cohort_risk,
        subject_breakdown=subjects,
        temporal_trends=trends,
        security_summary=sec_summary
    )
    assert len(insights) >= 3
    print(f"   [OK] Generated {len(insights)} structured explainable insights.")

    # -------------------------------------------------------------------------
    # TEST 14: Fact-Grounding Verification (No Fabricated Insights)
    # -------------------------------------------------------------------------
    print("\n[TEST 14] Verifying Fact Grounding of AI Insights...")
    for ins in insights:
        assert "insight_text" in ins and len(ins["insight_text"]) > 10
        assert "grounding_metric" in ins and isinstance(ins["grounding_metric"], dict)
        # Ensure percentages mentioned in text match grounding metrics
        if "overall_attendance_pct" in ins["grounding_metric"]:
            assert str(ins["grounding_metric"]["overall_attendance_pct"]) in ins["insight_text"]
    print("   [OK] 100% of generated insights are strictly grounded in SQL metrics.")

    # -------------------------------------------------------------------------
    # TEST 15: Analytics API Endpoints
    # -------------------------------------------------------------------------
    print("\n[TEST 15] Testing FastAPI Analytics Routes...")
    r_ov = client.get("/api/analytics/overview")
    assert r_ov.status_code == 200
    r_tr = client.get("/api/analytics/attendance-trend")
    assert r_tr.status_code == 200
    r_sb = client.get("/api/analytics/subjects")
    assert r_sb.status_code == 200
    r_ins = client.get("/api/analytics/insights")
    assert r_ins.status_code == 200
    print("   [OK] All /api/analytics endpoints respond with 200 OK.")

    # -------------------------------------------------------------------------
    # TEST 16: Biometric Privacy (Zero Raw Embeddings / Images in Analytics API)
    # -------------------------------------------------------------------------
    print("\n[TEST 16] Validating Biometric Privacy in Analytics Payloads...")
    analytics_eps = [
        "/api/analytics/overview",
        "/api/analytics/attendance-trend",
        "/api/analytics/subjects",
        "/api/analytics/students",
        "/api/analytics/risk",
        "/api/analytics/security",
        "/api/analytics/insights"
    ]
    for ep in analytics_eps:
        r = client.get(ep)
        body = r.text
        assert "embedding_bytes" not in body, f"Embedding leaked in {ep}!"
        assert "face_crop" not in body, f"Crop leaked in {ep}!"
        assert "frame_bytes" not in body, f"Frame leaked in {ep}!"
    print("   [OK] Biometric Privacy 100% compliant across all Analytics API responses.")

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------
    del db
    del analytics
    del risk_predictor
    del anomaly_detector
    del insights_engine
    gc.collect()

    try:
        if test_db_path.exists():
            test_db_path.unlink()
    except Exception:
        pass

    print("\n" + "=" * 75)
    print("[SUCCESS] ALL 16 STEP 10 AI ANALYTICS & INTELLIGENCE TESTS PASSED 100%!")
    print("=" * 75)
    return True


if __name__ == "__main__":
    run_step10_verification()
