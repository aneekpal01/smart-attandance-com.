"""
SmartAttend-AI: FastAPI Analytics & Intelligence Routes (Step 10)
================================================================
Endpoints for attendance trends, risk predictions, anomaly detection,
subject comparisons, and explainable AI faculty insights.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query

from database.db_manager import DatabaseManager
from ai.analytics.analytics_service import AnalyticsService
from ai.analytics.risk_predictor import AttendanceRiskPredictor
from ai.analytics.anomaly_detector import AttendanceAnomalyDetector
from ai.analytics.insights_engine import InsightsEngine

router = APIRouter(prefix="/api/analytics", tags=["Analytics & AI Insights"])
db = DatabaseManager()
analytics_service = AnalyticsService(db_manager=db)
risk_predictor = AttendanceRiskPredictor(required_attendance_pct=75.0)
anomaly_detector = AttendanceAnomalyDetector()
insights_engine = InsightsEngine()


@router.get("/overview")
def get_analytics_overview(
    department: Optional[str] = None,
    year: Optional[int] = None,
    section: Optional[str] = None,
    subject: Optional[str] = None
):
    """
    Returns high-level institutional and cohort attendance overview KPIs.
    """
    summary = analytics_service.get_overall_attendance_summary(
        department=department,
        year=year,
        section=section,
        subject=subject
    )
    profiles = analytics_service.get_all_student_attendance_profiles(
        department=department,
        year=year,
        section=section
    )
    risk_summary = risk_predictor.evaluate_cohort_risk(profiles)

    return {
        "overall_summary": summary,
        "risk_summary": {
            "required_attendance_threshold": risk_summary["required_attendance_threshold"],
            "high_risk_count": risk_summary["high_risk_count"],
            "medium_risk_count": risk_summary["medium_risk_count"],
            "low_risk_count": risk_summary["low_risk_count"],
            "insufficient_data_count": risk_summary["insufficient_data_count"],
            "below_threshold_count": risk_summary["below_threshold_count"]
        }
    }


@router.get("/attendance-trend")
def get_attendance_trend(days: int = Query(30, ge=1, le=365)):
    """
    Returns date-wise attendance percentages over rolling day windows.
    """
    return analytics_service.get_temporal_attendance_trend(days=days)


@router.get("/subjects")
def get_subject_breakdown():
    """
    Returns attendance performance statistics for all subjects.
    """
    subjects = analytics_service.get_subject_attendance_breakdown()
    return {"subjects": subjects, "count": len(subjects)}


@router.get("/students")
def get_student_profiles(
    department: Optional[str] = None,
    year: Optional[int] = None,
    section: Optional[str] = None
):
    """
    Returns detailed attendance stats and streaks for all cohort students.
    Strictly excludes raw face embeddings and biometric data.
    """
    profiles = analytics_service.get_all_student_attendance_profiles(
        department=department,
        year=year,
        section=section
    )
    return {"students": profiles, "total": len(profiles)}


@router.get("/risk")
def get_attendance_risk_analysis(
    required_threshold: float = Query(75.0, ge=50.0, le=100.0),
    department: Optional[str] = None,
    year: Optional[int] = None,
    section: Optional[str] = None
):
    """
    Returns explainable attendance-risk evaluations and missable class margins.
    """
    predictor = AttendanceRiskPredictor(required_attendance_pct=required_threshold)
    profiles = analytics_service.get_all_student_attendance_profiles(
        department=department,
        year=year,
        section=section
    )
    return predictor.evaluate_cohort_risk(profiles)


@router.get("/security")
def get_security_analytics():
    """
    Returns security analytics across Today, This Week, and This Month.
    """
    return analytics_service.get_security_analytics_summary()


@router.get("/insights")
def get_ai_insights(
    required_threshold: float = Query(75.0, ge=50.0, le=100.0)
):
    """
    Generates explainable natural-language faculty insights grounded in SQL metrics.
    """
    overall = analytics_service.get_overall_attendance_summary()
    profiles = analytics_service.get_all_student_attendance_profiles()
    predictor = AttendanceRiskPredictor(required_attendance_pct=required_threshold)
    risk_summary = predictor.evaluate_cohort_risk(profiles)
    subjects = analytics_service.get_subject_attendance_breakdown()
    temporal = analytics_service.get_temporal_attendance_trend()
    security = analytics_service.get_security_analytics_summary()

    insights = insights_engine.generate_insights(
        overall_summary=overall,
        student_profiles=profiles,
        risk_summary=risk_summary,
        subject_breakdown=subjects,
        temporal_trends=temporal,
        security_summary=security
    )

    anomalies = anomaly_detector.detect_anomalies(
        student_profiles=profiles,
        temporal_trends=temporal,
        security_summary=security
    )

    return {
        "insights": insights,
        "anomalies": anomalies,
        "insights_count": len(insights),
        "anomalies_count": len(anomalies)
    }


@router.get("/student/{student_id_or_roll}/breakdown")
def get_student_detailed_breakdown(student_id_or_roll: str):
    """
    Returns full class-by-class attendance history and statistics for a specific student.
    """
    data = db.get_student_attendance_breakdown(student_id_or_roll)
    if not data:
        raise HTTPException(status_code=404, detail="Student not found or no records available.")
    return data
