"""
SmartAttend-AI: Local QR Generation & Webcam Scanner Module
Generates secure random QR identity tokens (zero personal data in QR payload)
and decodes QR codes from live video frames.
"""

import uuid
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np
import qrcode

QR_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "database" / "qr_codes"


class QRManager:
    """
    Manages generation of secure student QR tokens and real-time frame scanning.
    """

    def __init__(self, qr_dir: Optional[str] = None):
        self.qr_dir = Path(qr_dir) if qr_dir else QR_STORAGE_DIR
        self.qr_dir.mkdir(parents=True, exist_ok=True)
        self.detector = cv2.QRCodeDetector()

    @staticmethod
    def generate_token() -> str:
        """
        Generates a cryptographically secure unique token for the student.
        Payload contains NO sensitive student information.
        """
        return f"SA-STU-{uuid.uuid4().hex[:16].upper()}"

    def generate_qr_image(self, qr_token: str, student_id: str) -> Path:
        """
        Generates and saves a QR Code image on disk containing only the token.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_token)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        clean_id = student_id.replace("/", "_").replace("\\", "_")
        file_path = self.qr_dir / f"{clean_id}_qr.png"
        img.save(str(file_path))
        return file_path

    def scan_qr_frame(self, frame: np.ndarray) -> Tuple[Optional[str], Optional[np.ndarray]]:
        """
        Detects and decodes a QR code in a video frame.
        
        Returns:
            (decoded_text, points_polygon)
        """
        if frame is None or frame.size == 0:
            return None, None

        decoded_text, points, _ = self.detector.detectAndDecode(frame)
        if decoded_text and decoded_text.strip():
            return decoded_text.strip(), points

        return None, None

    @staticmethod
    def draw_qr_box(frame: np.ndarray, points: np.ndarray, color=(255, 0, 255)) -> np.ndarray:
        """Draws bounding polygon around a detected QR code."""
        if points is not None and len(points) > 0:
            pts = points.astype(np.int32).reshape((-1, 1, 2))
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=3)
        return frame
