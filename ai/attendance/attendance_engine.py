"""
SmartAttend-AI: Attendance Engine (Step 6 & 7)
==============================================
Implements the core classroom attendance verification pipeline:
    1. Session Verification & Window Timing
    2. Student QR Token Lookup
    3. Facial Recognition Identity Match & Anti-Mismatch Verification
    4. Multi-Signal Liveness & Anti-Spoofing Verification (Step 7)
    5. Database-Level Duplicate Prevention & Record Storage
    6. Cohort Attendance Summary & Analytics Generation
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from database.db_manager import DatabaseManager
from ai.attendance.session_manager import SessionManager
from ai.face_recognition.recognizer import FaceRecognizerService, RecognitionResult
from ai.face_recognition.qr_manager import QRManager
from ai.liveness.detector import LivenessDetector, LivenessResult, LivenessState, LivenessConfig


class AttendanceEngine:
    """
    Core attendance processing engine.
    Connects Session validation, QR verification, Face recognition matching,
    Liveness anti-spoofing verification, and SQLite persistence.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        recognition_threshold: float = 0.60,
        liveness_config: Optional[LivenessConfig] = None
    ):
        self.db = db_manager or DatabaseManager()
        self.session_mgr = SessionManager(db_manager=self.db)
        self.qr_mgr = QRManager()
        self.recognizer = FaceRecognizerService(
            db_manager=self.db,
            recognition_threshold=recognition_threshold
        )
        self.liveness_detector = LivenessDetector(config=liveness_config)

    # -------------------------------------------------------------------------
    # 1. Step A: Student Session Entry Verification
    # -------------------------------------------------------------------------
    def verify_student_session_entry(
        self,
        session_code_or_token: str,
        student_qr_token: str,
        current_time: Optional[datetime] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validates that:
        1. Session exists, is ACTIVE, and not expired.
        2. Student QR token is registered and valid.
        3. Timing window is valid (PRESENT vs LATE).
        4. Student has not already been marked attendance for this session.
        """
        now = current_time or datetime.now()

        # 1. Validate Session
        sess_ok, sess_msg, session = self.session_mgr.validate_session(session_code_or_token, now)
        if not sess_ok or not session:
            return False, sess_msg, None

        # 2. Validate Student QR Token
        student = self.db.get_student_by_qr(student_qr_token)
        if not student:
            return False, "INVALID_QR_TOKEN: Student QR code is not registered.", None

        # 3. Check Duplicate Attendance in DB
        existing = self.db.get_student_session_attendance(session["id"], student["id"])
        if existing:
            return False, f"ALREADY_MARKED: Student {student['student_id']} already has attendance ({existing['status']}).", {
                "session": session,
                "student": student,
                "existing_record": existing
            }

        # 4. Evaluate Timing Window
        timing_ok, timing_status = self.session_mgr.evaluate_timing_status(session, now)
        if not timing_ok:
            return False, "WINDOW_EXPIRED: Attendance window for this session has closed.", None

        ticket = {
            "session_id": session["id"],
            "session_code": session["session_code"],
            "subject": session["subject"],
            "student_db_id": student["id"],
            "student_id": student["student_id"],
            "student_name": student["full_name"],
            "department": student["department"],
            "year": student["year"],
            "section": student["section"],
            "timing_status": timing_status,
            "verified_at": now.isoformat()
        }

        return True, f"SESSION_VERIFIED: Ready for Face & Liveness Verification ({timing_status})", ticket

    # -------------------------------------------------------------------------
    # 2. Step B: Face & Liveness Verification (Integrated Pipeline)
    # -------------------------------------------------------------------------
    def process_face_attendance_match(
        self,
        session_ticket: Dict[str, Any],
        recognized_student: Optional[Dict[str, Any]],
        similarity_score: float,
        is_recognized: bool,
        liveness_result: Optional[LivenessResult] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validates that:
        1. Face is detected and recognized (not UNKNOWN).
        2. Recognized student matches the QR ticket student (Anti-mismatch).
        3. Liveness status is verified as LIVE (Rejects SPOOF and UNCERTAIN).
        4. Writes attendance to SQLite database with uniqueness guarantee.
        """
        session_id = session_ticket["session_id"]
        expected_student_id = session_ticket["student_id"]
        student_db_id = session_ticket["student_db_id"]
        status = session_ticket["timing_status"]

        # Check 1: Face Unknown / No Face
        if not is_recognized or not recognized_student:
            return False, "FACE_UNKNOWN: Face not recognized as an enrolled student.", None

        # Check 2: Identity Mismatch (Anti-Proxy / QR Transfer Prevention)
        actual_student_id = recognized_student["student_id"]
        if actual_student_id != expected_student_id:
            reason = f"IDENTITY_MISMATCH: QR belongs to {expected_student_id} ({session_ticket['student_name']}) but recognized face is {actual_student_id} ({recognized_student['full_name']})."
            return False, reason, None

        # Check 3: Multi-Signal Liveness Verification (Step 7)
        if liveness_result is not None:
            if liveness_result.state == LivenessState.SPOOF:
                return False, f"LIVENESS_FAILED: Spoof attempt rejected ({liveness_result.reason}).", None
            elif liveness_result.state == LivenessState.UNCERTAIN:
                return False, f"LIVENESS_UNCERTAIN: Inconclusive liveness ({liveness_result.reason}). Please hold steady.", None
            elif liveness_result.state != LivenessState.LIVE:
                return False, f"LIVENESS_FAILED: Unknown liveness state ({liveness_result.state}).", None

        # Check 4: Record Attendance in SQLite with Database-Level Uniqueness
        attendance_code = f"ATT-{uuid.uuid4().hex[:10].upper()}"
        success, msg, rec_id = self.db.record_attendance(
            attendance_code=attendance_code,
            session_id=session_id,
            student_id=student_db_id,
            status=status,
            similarity_score=similarity_score,
            verification_method="QR_FACE_LIVENESS"
        )

        if not success:
            return False, msg, None

        record_data = {
            "id": rec_id,
            "attendance_code": attendance_code,
            "session_code": session_ticket["session_code"],
            "student_id": expected_student_id,
            "student_name": session_ticket["student_name"],
            "status": status,
            "similarity_score": similarity_score,
            "liveness_verified": True if liveness_result else False,
            "timestamp": datetime.now().isoformat()
        }

        return True, f"ATTENDANCE_RECORDED: Marked as {status}", record_data

    # -------------------------------------------------------------------------
    # 3. Summary & Reports
    # -------------------------------------------------------------------------
    def get_session_summary(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Returns classroom attendance statistics, present/late/absent lists."""
        return self.db.get_session_attendance_summary(session_id)
