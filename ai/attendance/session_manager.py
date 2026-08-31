"""
SmartAttend-AI: Classroom Session Management & Temporary QR Engine (Step 6)
===========================================================================
Handles classroom session creation, temporary QR generation, timing window evaluation,
and session validation.
"""

import uuid
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import qrcode

from database.db_manager import DatabaseManager

SESSION_QR_DIR = Path(__file__).resolve().parent.parent.parent / "database" / "qr_codes"


class SessionManager:
    """
    Manages creation and lifecycle of classroom sessions and temporary session QR codes.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None, qr_dir: Optional[str] = None):
        self.db = db_manager or DatabaseManager()
        self.qr_dir = Path(qr_dir) if qr_dir else SESSION_QR_DIR
        self.qr_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_session_code() -> str:
        """Generates human-readable unique session code, e.g. SA-SESSION-8F3A91."""
        return f"SA-SESSION-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    def generate_session_token() -> str:
        """Generates random secure session token."""
        return f"STOKEN-{uuid.uuid4().hex[:16].upper()}"

    def create_session(
        self,
        subject: str,
        department: str,
        year: int,
        section: str = "",
        room: str = "Room-101",
        faculty_name: str = "Faculty",
        start_time: Optional[datetime] = None,
        regular_window_minutes: int = 10,
        late_window_minutes: int = 20
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Creates a new classroom attendance session with dynamic temporary QR code.
        """
        if not subject or not department or not room or not faculty_name:
            return False, "Validation Error: Subject, department, room, and faculty name are required.", None

        if regular_window_minutes <= 0 or late_window_minutes < regular_window_minutes:
            return False, "Timing Error: late_window_minutes must be >= regular_window_minutes > 0.", None

        start = start_time or datetime.now()
        end = start + timedelta(minutes=late_window_minutes)
        session_code = self.generate_session_code()
        session_token = self.generate_session_token()

        success, msg, session_db_id = self.db.create_session(
            session_code=session_code,
            subject=subject,
            department=department,
            year=year,
            section=section,
            room=room,
            faculty_name=faculty_name,
            start_time=start,
            regular_window_minutes=regular_window_minutes,
            late_window_minutes=late_window_minutes,
            end_time=end,
            session_token=session_token
        )

        if not success:
            return False, msg, None

        # Generate temporary session QR code image
        qr_path = self.generate_session_qr(session_code, session_token, end)

        session_data = {
            "id": session_db_id,
            "session_code": session_code,
            "subject": subject,
            "department": department.upper(),
            "year": year,
            "section": section.upper(),
            "room": room,
            "faculty_name": faculty_name,
            "start_time": start.isoformat(),
            "regular_window_minutes": regular_window_minutes,
            "late_window_minutes": late_window_minutes,
            "end_time": end.isoformat(),
            "session_token": session_token,
            "qr_image_path": str(qr_path),
            "status": "ACTIVE"
        }

        return True, "Classroom session created successfully.", session_data

    @staticmethod
    def _get_local_ip() -> str:
        """Retrieves machine LAN IP address for phone hotspot/Wi-Fi scanning."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return 'localhost'

    def generate_session_qr(self, session_code: str, session_token: str, end_time: datetime) -> Path:
        """
        Generates temporary QR image with a direct clickable Web URL.
        Google Lens, Phone Camera, and QR scanners can directly tap to open the mobile check-in portal.
        """
        host_ip = self._get_local_ip()
        web_checkin_url = f"http://{host_ip}:5173/?session={session_code}&token={session_token}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4
        )
        qr.add_data(web_checkin_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        qr_file = self.qr_dir / f"session_{session_code}.png"
        img.save(str(qr_file))
        return qr_file

    def validate_session(
        self,
        session_identifier: str,
        current_time: Optional[datetime] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validates session existence, active status, and timing window.
        """
        now = current_time or datetime.now()

        # Handle direct Web URL query strings: e.g. http://192.168.1.52:5173/?session=SA-SESSION-123&token=STOKEN-456
        session = None
        if "session=" in session_identifier:
            try:
                for part in session_identifier.split("?")[1].split("&"):
                    if part.startswith("session="):
                        session_identifier = part.split("=")[1]
                        break
            except Exception:
                pass

        # Try lookup by session_code or session_token or json payload
        if session_identifier.startswith("{") and "token" in session_identifier:
            try:
                data = json.loads(session_identifier)
                session = self.db.get_session_by_token(data.get("token", ""))
            except Exception:
                pass

        if not session:
            session = self.db.get_session_by_code(session_identifier)
        if not session:
            session = self.db.get_session_by_token(session_identifier)

        if not session:
            return False, "SESSION_NOT_FOUND: Session does not exist.", None

        if session["status"] != "ACTIVE":
            return False, "SESSION_CLOSED: Session has been closed by faculty.", session

        # Check expiration time
        end_time = datetime.fromisoformat(session["end_time"]) if isinstance(session["end_time"], str) else session["end_time"]
        if now > end_time:
            return False, "SESSION_EXPIRED: Attendance window has expired.", session

        return True, "SESSION_VALID", session

    def evaluate_timing_status(
        self,
        session: Dict[str, Any],
        current_time: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        Determines if student is PRESENT, LATE, or EXPIRED based on timing windows.
        """
        now = current_time or datetime.now()
        start = datetime.fromisoformat(session["start_time"]) if isinstance(session["start_time"], str) else session["start_time"]
        reg_min = session["regular_window_minutes"]
        late_min = session["late_window_minutes"]

        reg_deadline = start + timedelta(minutes=reg_min)
        late_deadline = start + timedelta(minutes=late_min)

        if now <= reg_deadline:
            return True, "PRESENT"
        elif now <= late_deadline:
            return True, "LATE"
        else:
            return False, "WINDOW_EXPIRED"
