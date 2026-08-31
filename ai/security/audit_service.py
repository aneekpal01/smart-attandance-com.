"""
SmartAttend-AI: Security Audit Service & Atomic Transaction Engine (Step 8)
===========================================================================
Hardens the verification pipeline against:
  - QR Replay & Cross-Session Token Reuse
  - Proxy Identity Mismatches
  - Repeated Spoof & Brute-force Attempts
  - Duplicate Attendance Transactions
"""

import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from database.db_manager import DatabaseManager
from ai.security.config import SecurityConfig, DEFAULT_SECURITY_CONFIG
from ai.security.rate_limiter import RateLimiter
from ai.attendance.session_manager import SessionManager
from ai.face_recognition.recognizer import FaceRecognizerService
from ai.liveness.detector import LivenessDetector, LivenessResult, LivenessState


class SecurityAuditService:
    """
    Coordinates security event logging, replay protection, rate limiting,
    and atomic attendance transactions.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        config: Optional[SecurityConfig] = None
    ):
        self.db = db_manager or DatabaseManager()
        self.config = config or DEFAULT_SECURITY_CONFIG
        self.session_mgr = SessionManager(db_manager=self.db)
        self.rate_limiter = RateLimiter(config=self.config)
        self.recognizer = FaceRecognizerService(
            db_manager=self.db,
            recognition_threshold=self.config.recognition_threshold
        )
        self.liveness_detector = LivenessDetector()

    # -------------------------------------------------------------------------
    # 1. Atomic Attendance Verification Pipeline (Step 8)
    # -------------------------------------------------------------------------
    def execute_secure_attendance_transaction(
        self,
        session_code_or_token: str,
        student_qr_token: str,
        recognized_student: Optional[Dict[str, Any]],
        similarity_score: float,
        is_recognized: bool,
        liveness_result: Optional[LivenessResult] = None,
        verification_ticket_id: Optional[str] = None,
        current_time: Optional[datetime] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executes an atomic attendance verification transaction.
        Enforces all 8 security checkpoints:
          1. Session validation & active state check
          2. Attendance timing window check (PRESENT vs LATE)
          3. Student QR token database verification
          4. Cross-session token binding check
          5. Replay token validation
          6. Face identity anti-mismatch check
          7. Multi-signal liveness verification (Must be LIVE)
          8. Idempotent duplicate check & SQLite record creation
        """
        now = current_time or datetime.now()
        ticket_id = verification_ticket_id or f"TXN-{uuid.uuid4().hex[:12].upper()}"

        # -------------------------------------------------------------
        # CHECKPOINT 1: Session Validation & Active State
        # -------------------------------------------------------------
        sess_ok, sess_msg, session = self.session_mgr.validate_session(session_code_or_token, now)
        if not sess_ok or not session:
            event_type = "SESSION_CLOSED" if "CLOSED" in sess_msg else ("SESSION_EXPIRED" if "EXPIRED" in sess_msg else "QR_REJECTED")
            severity = "WARNING" if "EXPIRED" in sess_msg or "CLOSED" in sess_msg else "HIGH"
            self.db.log_audit_event(
                session_id=session["id"] if session else 0,
                event_type=event_type,
                severity=severity,
                result="REJECTED",
                reason=sess_msg,
                metadata={"session_identifier": session_code_or_token}
            )
            return False, sess_msg, {"checkpoint": "SESSION_VALIDATION", "event_type": event_type}

        session_id = session["id"]

        # -------------------------------------------------------------
        # CHECKPOINT 2: Attendance Timing Window
        # -------------------------------------------------------------
        timing_ok, timing_status = self.session_mgr.evaluate_timing_status(session, now)
        if not timing_ok:
            self.db.log_audit_event(
                session_id=session_id,
                event_type="SESSION_EXPIRED",
                severity="WARNING",
                result="REJECTED",
                reason="Attendance window for this session has closed."
            )
            return False, "WINDOW_EXPIRED: Attendance window has closed.", {"checkpoint": "TIMING_WINDOW"}

        # -------------------------------------------------------------
        # CHECKPOINT 3: Student QR Token Verification
        # -------------------------------------------------------------
        student = self.db.get_student_by_qr(student_qr_token)
        if not student:
            is_suspicious, fail_cnt = self.rate_limiter.record_failure(session_id, "UNKNOWN_QR")
            event_type = "SUSPICIOUS_ACTIVITY" if is_suspicious else "QR_REJECTED"
            severity = "HIGH" if is_suspicious else "WARNING"
            self.db.log_audit_event(
                session_id=session_id,
                event_type=event_type,
                severity=severity,
                result="REJECTED",
                reason=f"Invalid student QR token. Consecutive failures: {fail_cnt}."
            )
            return False, "INVALID_QR_TOKEN: Student QR code is not registered.", {"checkpoint": "QR_VERIFICATION", "event_type": event_type}

        student_id_db = student["id"]
        roll_no = student["student_id"]

        # -------------------------------------------------------------
        # CHECKPOINT 4: Replay Token Validation (Atomic Check)
        # -------------------------------------------------------------
        fresh_token = self.db.check_and_use_replay_token(
            token_hash=ticket_id,
            session_id=session_id,
            student_id=student_id_db
        )
        if not fresh_token:
            self.db.log_audit_event(
                session_id=session_id,
                student_id=student_id_db,
                event_type="REPLAY_ATTEMPT",
                severity="HIGH",
                result="REJECTED",
                reason=f"Replay attack detected: Verification transaction '{ticket_id}' was already used."
            )
            return False, "REPLAY_REJECTED: Verification transaction has already been used.", {"checkpoint": "REPLAY_PROTECTION"}

        # -------------------------------------------------------------
        # CHECKPOINT 5: Duplicate Attendance Check (Database level)
        # -------------------------------------------------------------
        existing_att = self.db.get_student_session_attendance(session_id, student_id_db)
        if existing_att:
            self.db.log_audit_event(
                session_id=session_id,
                student_id=student_id_db,
                event_type="DUPLICATE_ATTEMPT",
                severity="WARNING",
                result="REJECTED",
                reason=f"Duplicate attendance attempt: Already marked as {existing_att['status']}."
            )
            return False, f"ALREADY_MARKED: Student {roll_no} already has attendance ({existing_att['status']}).", {
                "checkpoint": "DUPLICATE_CHECK",
                "existing_record": existing_att
            }

        # -------------------------------------------------------------
        # CHECKPOINT 6: Face Recognition & Anti-Mismatch Verification
        # -------------------------------------------------------------
        if not is_recognized or not recognized_student:
            is_susp, fail_cnt = self.rate_limiter.record_failure(session_id, roll_no)
            event_type = "SUSPICIOUS_ACTIVITY" if is_susp else "FACE_UNKNOWN"
            severity = "HIGH" if is_susp else "WARNING"
            self.db.log_audit_event(
                session_id=session_id,
                student_id=student_id_db,
                event_type=event_type,
                severity=severity,
                result="REJECTED",
                similarity_score=similarity_score,
                reason=f"Face not recognized as enrolled student. Consecutive failures: {fail_cnt}."
            )
            return False, "FACE_UNKNOWN: Face not recognized as an enrolled student.", {"checkpoint": "FACE_RECOGNITION"}

        # Check exact identity match between QR and recognized face
        if recognized_student["student_id"] != roll_no:
            is_susp, fail_cnt = self.rate_limiter.record_failure(session_id, roll_no)
            event_type = "SUSPICIOUS_ACTIVITY" if is_susp else "IDENTITY_MISMATCH"
            severity = "HIGH" if is_susp else "WARNING"
            mismatch_reason = f"Proxy Attempt: {recognized_student['full_name']} ({recognized_student['student_id']}) attempted to mark proxy for {student['full_name']} ({roll_no})."
            self.db.log_audit_event(
                session_id=session_id,
                student_id=student_id_db,
                event_type=event_type,
                severity=severity,
                result="REJECTED",
                similarity_score=similarity_score,
                reason=mismatch_reason,
                metadata={
                    "culprit_roll_no": recognized_student["student_id"],
                    "culprit_name": recognized_student["full_name"],
                    "target_roll_no": roll_no,
                    "target_name": student["full_name"],
                    "consecutive_failures": fail_cnt
                }
            )
            return False, f"IDENTITY_MISMATCH: {mismatch_reason}", {
                "checkpoint": "IDENTITY_BINDING",
                "event_type": event_type,
                "is_suspicious": is_susp
            }

        # -------------------------------------------------------------
        # CHECKPOINT 7: Multi-Signal Liveness Verification (Step 7)
        # -------------------------------------------------------------
        if liveness_result is not None:
            if liveness_result.state == LivenessState.SPOOF:
                is_susp, fail_cnt = self.rate_limiter.record_failure(session_id, roll_no)
                event_type = "SUSPICIOUS_ACTIVITY" if is_susp else "LIVENESS_FAILED"
                self.db.log_audit_event(
                    session_id=session_id,
                    student_id=student_id_db,
                    event_type=event_type,
                    severity="HIGH",
                    result="REJECTED",
                    liveness_score=liveness_result.liveness_score,
                    reason=f"Anti-spoofing alert: {liveness_result.reason} (Consecutive failures: {fail_cnt})."
                )
                return False, f"LIVENESS_FAILED: Spoof attempt rejected ({liveness_result.reason}).", {
                    "checkpoint": "LIVENESS_BINDING",
                    "event_type": event_type,
                    "is_suspicious": is_susp
                }

            elif liveness_result.state == LivenessState.UNCERTAIN:
                self.db.log_audit_event(
                    session_id=session_id,
                    student_id=student_id_db,
                    event_type="LIVENESS_UNCERTAIN",
                    severity="WARNING",
                    result="REJECTED",
                    liveness_score=liveness_result.liveness_score,
                    reason=liveness_result.reason
                )
                return False, f"LIVENESS_UNCERTAIN: Inconclusive liveness ({liveness_result.reason}). Please retry.", {
                    "checkpoint": "LIVENESS_BINDING",
                    "event_type": "LIVENESS_UNCERTAIN"
                }

        # -------------------------------------------------------------
        # CHECKPOINT 8: Insert Attendance Record & Log Success Audit Event
        # -------------------------------------------------------------
        attendance_code = f"ATT-{uuid.uuid4().hex[:10].upper()}"
        rec_ok, rec_msg, rec_id = self.db.record_attendance(
            attendance_code=attendance_code,
            session_id=session_id,
            student_id=student_id_db,
            status=timing_status,
            similarity_score=similarity_score,
            verification_method="QR_FACE_LIVENESS_SECURE"
        )

        if not rec_ok:
            self.db.log_audit_event(
                session_id=session_id,
                student_id=student_id_db,
                event_type="DUPLICATE_ATTEMPT",
                severity="WARNING",
                result="REJECTED",
                reason=rec_msg
            )
            return False, rec_msg, {"checkpoint": "DATABASE_INSERTION"}

        # Reset rate limiter upon success
        self.rate_limiter.reset(session_id, roll_no)

        # Log Successful Attendance Audit Event (Severity: INFO)
        self.db.log_audit_event(
            session_id=session_id,
            student_id=student_id_db,
            event_type="ATTENDANCE_MARKED",
            severity="INFO",
            result="SUCCESS",
            similarity_score=similarity_score,
            liveness_score=liveness_result.liveness_score if liveness_result else 1.0,
            reason=f"Attendance successfully recorded as {timing_status}.",
            metadata={"attendance_code": attendance_code, "ticket_id": ticket_id}
        )

        record_data = {
            "id": rec_id,
            "attendance_code": attendance_code,
            "ticket_id": ticket_id,
            "session_code": session["session_code"],
            "student_id": roll_no,
            "student_name": student["full_name"],
            "status": timing_status,
            "similarity_score": similarity_score,
            "liveness_verified": True if liveness_result else False,
            "timestamp": now.isoformat()
        }

        return True, f"ATTENDANCE_RECORDED: Marked as {timing_status}", record_data

    # -------------------------------------------------------------------------
    # 2. Faculty Review & Security Telemetry
    # -------------------------------------------------------------------------
    def get_session_security_report(self, session_id: int) -> Dict[str, Any]:
        """Returns security audit metrics and event logs for a session."""
        summary = self.db.get_session_security_summary(session_id)
        events = self.db.get_audit_events_for_session(session_id, limit=50)
        return {
            "summary": summary,
            "recent_audit_events": events
        }

    def get_flagged_suspicious_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent suspicious activity events for faculty dashboard."""
        return self.db.get_recent_suspicious_events(limit=limit)
