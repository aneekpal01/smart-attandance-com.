"""
SmartAttend-AI: Local Attendance Risk Predictor (Step 10)
=========================================================
Identifies students at risk of falling below attendance thresholds
using explainable rule-based scoring and temporal streaks.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class RiskEvaluationResult:
    """Output for a student risk evaluation."""
    student_id: str
    student_name: str
    current_attendance_pct: float
    required_attendance_pct: float
    risk_level: str                         # LOW | MEDIUM | HIGH | INSUFFICIENT_DATA
    risk_score: float                       # 0.0 to 1.0
    contributing_factors: List[str]
    recommended_action: str
    margin_missable_classes: Optional[int]  # How many future classes student can miss before falling below threshold
    classes_needed_for_target: int          # How many consecutive classes needed to reach threshold if below


class AttendanceRiskPredictor:
    """
    Local explainable attendance risk predictor.
    Transparently evaluates student attendance trajectories against academic thresholds.
    """

    def __init__(
        self,
        required_attendance_pct: float = 75.0,
        min_classes_required_for_prediction: int = 3
    ):
        self.required_pct = required_attendance_pct
        self.min_classes = min_classes_required_for_prediction

    def evaluate_student_risk(self, student_profile: Dict[str, Any]) -> RiskEvaluationResult:
        """
        Evaluates a single student profile and returns a transparent RiskEvaluationResult.
        """
        student_id = student_profile.get("student_id", "")
        name = student_profile.get("full_name", "")
        total_classes = student_profile.get("total_classes", 0)
        attended_classes = student_profile.get("attended_classes", 0)
        att_pct = student_profile.get("attendance_percentage", 0.0)
        trend = student_profile.get("recent_trend", "STABLE")
        history = student_profile.get("session_attendance_history", [])

        # -------------------------------------------------------------
        # 1. Check Small-Data / Minimum Classes Condition
        # -------------------------------------------------------------
        if total_classes < self.min_classes:
            return RiskEvaluationResult(
                student_id=student_id,
                student_name=name,
                current_attendance_pct=att_pct,
                required_attendance_pct=self.required_pct,
                risk_level="INSUFFICIENT_DATA",
                risk_score=0.0,
                contributing_factors=[
                    f"Only {total_classes} class session(s) recorded (minimum {self.min_classes} required for risk evaluation)."
                ],
                recommended_action="Continue recording attendance. Risk evaluation activates once baseline classes are met.",
                margin_missable_classes=None,
                classes_needed_for_target=0
            )

        # -------------------------------------------------------------
        # 2. Extract Contributing Factors
        # -------------------------------------------------------------
        factors: List[str] = []
        risk_score = 0.0

        # Factor A: Current % vs Required %
        gap = self.required_pct - att_pct
        if att_pct < self.required_pct:
            factors.append(f"Current attendance ({att_pct}%) is {abs(gap):.1f}% below the required {self.required_pct}% threshold.")
            risk_score += 0.50 + min(0.35, (gap / 100.0) * 1.5)
        elif att_pct < self.required_pct + 5.0:
            factors.append(f"Borderline attendance ({att_pct}%), within 5% of the minimum {self.required_pct}% requirement.")
            risk_score += 0.30
        else:
            factors.append(f"Attendance is healthy at {att_pct}% (above the {self.required_pct}% threshold).")
            risk_score += 0.05

        # Factor B: Recent Absence Streak in Last 5 Sessions
        recent_sessions = history[-5:] if len(history) >= 5 else history
        recent_absences = sum(1 for s in recent_sessions if s.get("status") == "ABSENT")
        if recent_absences >= 3:
            factors.append(f"Recent absence streak: Missed {recent_absences} of the last {len(recent_sessions)} classes.")
            risk_score += 0.25
        elif recent_absences == 2:
            factors.append(f"Missed {recent_absences} of the last {len(recent_sessions)} classes.")
            risk_score += 0.10

        # Factor C: Trend direction
        if trend == "DECLINING":
            factors.append("Attendance trajectory has declined noticeably compared to earlier baseline sessions.")
            risk_score += 0.15
        elif trend == "IMPROVING":
            factors.append("Attendance trajectory is improving in recent sessions.")
            risk_score = max(0.0, risk_score - 0.15)

        # -------------------------------------------------------------
        # 3. Mathematical Margin Estimation
        # -------------------------------------------------------------
        # Margin missable classes: Floor where (attended) / (total + X) >= required_pct / 100
        # => attended * 100 / required_pct - total >= X
        if att_pct >= self.required_pct:
            max_total_at_req = int(attended_classes / (self.required_pct / 100.0))
            margin_missable = max(0, max_total_at_req - total_classes)
            classes_needed = 0
        else:
            margin_missable = 0
            # Classes needed: (attended + Y) / (total + Y) >= required_pct / 100
            # attended + Y >= req * total + req * Y
            # Y * (1 - req) >= req * total - attended
            # Y = ceil( (req*total - attended) / (1 - req) )
            req_ratio = self.required_pct / 100.0
            numerator = (req_ratio * total_classes) - attended_classes
            denominator = 1.0 - req_ratio
            classes_needed = max(1, int(numerator / denominator) + 1) if denominator > 0 else 1

        # -------------------------------------------------------------
        # 4. Final Risk Classification
        # -------------------------------------------------------------
        risk_score = round(float(min(1.0, max(0.0, risk_score))), 2)

        if risk_score >= 0.60 or att_pct < self.required_pct:
            risk_level = "HIGH"
            action = f"Immediate faculty intervention required. Student must attend next {classes_needed} consecutive classes to recover."
        elif risk_score >= 0.30:
            risk_level = "MEDIUM"
            action = f"Monitor attendance closely. Student can miss approximately {margin_missable} additional class(es) before dropping below requirement."
        else:
            risk_level = "LOW"
            action = f"No immediate risk. Student can miss approximately {margin_missable} class(es) while maintaining compliance."

        return RiskEvaluationResult(
            student_id=student_id,
            student_name=name,
            current_attendance_pct=att_pct,
            required_attendance_pct=self.required_pct,
            risk_level=risk_level,
            risk_score=risk_score,
            contributing_factors=factors,
            recommended_action=action,
            margin_missable_classes=margin_missable if att_pct >= self.required_pct else None,
            classes_needed_for_target=classes_needed
        )

    def evaluate_cohort_risk(self, student_profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluates risk for an entire cohort and summarizes results.
        """
        evaluations = [self.evaluate_student_risk(p) for p in student_profiles]

        high_risk = [e for e in evaluations if e.risk_level == "HIGH"]
        medium_risk = [e for e in evaluations if e.risk_level == "MEDIUM"]
        low_risk = [e for e in evaluations if e.risk_level == "LOW"]
        insufficient = [e for e in evaluations if e.risk_level == "INSUFFICIENT_DATA"]

        below_threshold_count = sum(1 for e in evaluations if e.current_attendance_pct < self.required_pct and e.risk_level != "INSUFFICIENT_DATA")

        return {
            "required_attendance_threshold": self.required_pct,
            "total_students_evaluated": len(evaluations),
            "high_risk_count": len(high_risk),
            "medium_risk_count": len(medium_risk),
            "low_risk_count": len(low_risk),
            "insufficient_data_count": len(insufficient),
            "below_threshold_count": below_threshold_count,
            "students_risk_breakdown": [
                {
                    "student_id": e.student_id,
                    "student_name": e.student_name,
                    "current_attendance_pct": e.current_attendance_pct,
                    "risk_level": e.risk_level,
                    "risk_score": e.risk_score,
                    "contributing_factors": e.contributing_factors,
                    "recommended_action": e.recommended_action,
                    "margin_missable_classes": e.margin_missable_classes,
                    "classes_needed_for_target": e.classes_needed_for_target
                }
                for e in evaluations
            ]
        }
