"""
SmartAttend-AI: Live Interactive Classroom Attendance Scanner HUD
=================================================================
Live webcam check-in terminal:
  - Scans Student QR Tokens
  - YuNet Real-Time Face Detection & Alignment
  - SFace 128-D Face Recognition & Cosine Similarity
  - Multi-Signal Temporal Liveness (Blocks Photo & Phone Spoofs)
  - Anti-Proxy Verification (QR Student == Recognized Face)
  - Atomic Attendance Transaction & Live Faculty Dashboard Sync
"""

import sys
import time
from datetime import datetime
from pathlib import Path
import cv2
import numpy as np

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from database.db_manager import DatabaseManager
from ai.face_recognition.detector import FaceDetector
from ai.face_recognition.recognizer import FaceRecognizerService
from ai.face_recognition.qr_manager import QRManager
from ai.liveness.detector import LivenessDetector, LivenessConfig, LivenessState
from ai.attendance.session_manager import SessionManager
from ai.security.audit_service import SecurityAuditService
from ai.models.download_models import download_yunet_model, download_sface_model, YUNET_PATH, SFACE_PATH


def main():
    print("=" * 75)
    print("🎓 SMARTATTEND-AI: LIVE CLASSROOM ATTENDANCE TERMINAL")
    print("=" * 75)

    download_yunet_model()
    download_sface_model()

    db = DatabaseManager()
    db.init_schema()
    qr_mgr = QRManager()
    session_mgr = SessionManager(db_manager=db)
    security_service = SecurityAuditService(db_manager=db)
    security_service.session_mgr = session_mgr
    detector = FaceDetector(model_path=str(YUNET_PATH))
    recognizer = FaceRecognizerService()
    liveness = LivenessDetector(config=LivenessConfig(window_frames=12, min_frames_required=6))

    # 1. Find or prompt for active session
    active_sessions = session_mgr.get_active_sessions()
    if not active_sessions:
        print("\n[!] No active classroom session found.")
        print("[*] Creating a quick live demo session for you now...")
        _, _, active_session = session_mgr.create_session(
            subject="Computer Vision & AI Systems",
            department="COMPUTER SCIENCE",
            year=4,
            section="A",
            room="AUDITORIUM-1",
            faculty_name="Prof. Andrew Ng",
            start_time=datetime.now(),
            regular_window_minutes=30,
            late_window_minutes=60
        )
    else:
        active_session = active_sessions[0]

    session_code = active_session["session_code"]
    subject = active_session["subject"]
    print(f"\n[✓] CONNECTED TO ACTIVE SESSION: '{subject}' [{session_code}]")
    print(f"[*] Window: 30 min PRESENT | Room: {active_session.get('room', 'N/A')}")
    print("[*] Press 'ESC' or 'q' in the camera window to close.")
    print("=" * 75)

    # 2. Open physical webcam
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("\n[!] Camera device index 0 could not be opened.")
        print("[!] Please ensure webcam is connected and permissions are granted.")
        return

    last_scanned_qr = None
    last_qr_time = 0
    verification_status_text = "SCAN STUDENT QR OR FACE"
    verification_color = (255, 255, 255)
    student_display_name = ""

    prev_time = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        now_perf = time.perf_counter()
        fps = 1.0 / max(1e-5, (now_perf - prev_time))
        prev_time = now_perf

        h, w = frame.shape[:2]

        # 1. Detect QR code in frame
        decoded_qr, qr_points = qr_mgr.scan_qr_frame(frame)
        if decoded_qr:
            last_scanned_qr = decoded_qr
            last_qr_time = time.time()
            if qr_points is not None:
                pts = qr_points.astype(int).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (0, 255, 0), 2)

        # 2. Detect Faces
        faces = detector.detect(frame)
        recognized_student = None
        similarity_score = 0.0
        is_recognized = False

        if faces:
            primary_face = faces[0]
            bbox = primary_face.bbox
            landmarks = primary_face.landmarks

            # Add to liveness buffer
            liveness.add_frame_sample(frame, landmarks, bbox)
            liveness_res = liveness.evaluate_liveness()

            # Face recognition match
            rec_res = recognizer.recognize_face(frame, primary_face)
            if rec_res:
                recognized_student = {
                    "id": rec_res.student_db_id,
                    "student_id": rec_res.student_id,
                    "full_name": rec_res.full_name
                }
                similarity_score = rec_res.similarity_score
                is_recognized = True
                student_display_name = rec_res.full_name

            # If we have scanned a QR recently (within 5 seconds) or recognized a student:
            if last_scanned_qr and (time.time() - last_qr_time < 5.0):
                ticket_id = f"TXN-LIVE-{int(time.time()*1000)}"
                ok, msg, data = security_service.execute_secure_attendance_transaction(
                    session_code_or_token=session_code,
                    student_qr_token=last_scanned_qr,
                    recognized_student=recognized_student,
                    similarity_score=similarity_score,
                    is_recognized=is_recognized,
                    liveness_result=liveness_res,
                    verification_ticket_id=ticket_id,
                    current_time=datetime.now()
                )

                if ok:
                    verification_status_text = f"ATTENDANCE MARKED ({data['status']}): {data['student_name']}"
                    verification_color = (0, 255, 100) # Green
                else:
                    if "ALREADY_MARKED" in msg:
                        verification_status_text = f"ALREADY MARKED: {student_display_name or 'STUDENT'}"
                        verification_color = (0, 200, 255) # Amber
                    elif "IDENTITY_MISMATCH" in msg:
                        verification_status_text = "PROXY REJECTED: IDENTITY MISMATCH"
                        verification_color = (0, 0, 255) # Red
                    elif "LIVENESS_FAILED" in msg:
                        verification_status_text = "SPOOF REJECTED: LIVENESS FAILED"
                        verification_color = (0, 0, 255) # Red
                    else:
                        verification_status_text = f"REJECTED: {msg[:35]}"
                        verification_color = (0, 165, 255) # Orange

            # Draw Face Bounding Box
            bx, by, bw, bh = bbox
            cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), verification_color, 2)

            # Draw Landmarks
            for (lx, ly) in landmarks:
                cv2.circle(frame, (int(lx), int(ly)), 3, (0, 255, 255), -1)

            # Name Tag
            tag = f"{student_display_name or 'Scanning...'} ({similarity_score:.2f})"
            cv2.rectangle(frame, (bx, by - 24), (bx + bw, by), verification_color, -1)
            cv2.putText(frame, tag, (bx + 4, by - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        # -------------------------------------------------------------
        # HUD Overlays
        # -------------------------------------------------------------
        # Top Bar
        cv2.rectangle(frame, (0, 0), (w, 45), (20, 24, 33), -1)
        cv2.putText(frame, f"SESSION: {session_code} | {subject[:24]}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        cv2.putText(frame, f"FPS: {fps:4.1f}", (w - 110, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 200), 2)

        # Bottom Status Banner
        cv2.rectangle(frame, (0, h - 45), (w, h), (20, 24, 33), -1)
        cv2.putText(frame, verification_status_text, (12, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.55, verification_color, 2)

        cv2.imshow("SmartAttend-AI - Live Attendance Terminal (ESC to exit)", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n[✓] Camera terminal closed cleanly.")


if __name__ == "__main__":
    main()
