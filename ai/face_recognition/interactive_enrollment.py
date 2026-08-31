"""
SmartAttend-AI: Interactive Student Enrollment Application (Step 4)
Complete Flow:
    1. Scan & Verify Student QR Code
    2. Enforce 1-Face Rule (reject 0 or >1 face)
    3. Multi-sample Face Enrollment
    4. Store Embeddings in Local SQLite Database
"""

import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import cv2
import numpy as np

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from ai.face_recognition.live_face_detector import OpenCVFaceDetector, FaceBox
from ai.face_recognition.embedder import FaceEmbedder
from ai.face_recognition.qr_manager import QRManager
from ai.face_recognition.enrollment_service import StudentEnrollmentService
from database.db_manager import DatabaseManager


class InteractiveEnrollmentApp:
    """
    GUI application that walks a student through QR verification
    and multi-sample face embedding enrollment.
    """

    STATE_SCAN_QR = "SCAN_QR"
    STATE_FACE_ENROLL = "FACE_ENROLL"
    STATE_SUCCESS = "SUCCESS"

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.db = DatabaseManager()
        self.service = StudentEnrollmentService(db_manager=self.db)
        self.detector = OpenCVFaceDetector()
        self.embedder = FaceEmbedder()
        self.qr_manager = QRManager()

        # Session state
        self.current_state = self.STATE_SCAN_QR
        self.verified_student: Optional[Dict[str, Any]] = None
        self.status_message = "Point your Student QR Code to the Camera"
        self.sample_embeddings: List[np.ndarray] = []
        self.target_samples = 5
        self.sample_instructions = [
            "Sample 1/5: Look directly at the camera",
            "Sample 2/5: Slightly turn head left",
            "Sample 3/5: Slightly turn head right",
            "Sample 4/5: Slightly tilt head up/down",
            "Sample 5/5: Look straight and hold steady"
        ]
        self.last_capture_time = 0.0
        self.capture_delay = 0.8  # Seconds between auto sample captures

    def draw_hud(self, frame: np.ndarray, fps: float) -> np.ndarray:
        """Renders step-specific overlays and guides."""
        h, w = frame.shape[:2]
        output = frame.copy()

        # Top banner
        header = output.copy()
        cv2.rectangle(header, (0, 0), (w, 50), (15, 23, 42), -1)
        cv2.addWeighted(header, 0.9, output, 0.1, 0, output)

        cv2.putText(
            output,
            "SmartAttend-AI | Student Enrollment (Step 4)",
            (15, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            output,
            f"FPS: {fps:.1f}",
            (w - 120, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 220, 255),
            2,
            cv2.LINE_AA
        )

        # Bottom info card
        card = output.copy()
        cv2.rectangle(card, (0, h - 85), (w, h), (15, 23, 42), -1)
        cv2.addWeighted(card, 0.9, output, 0.1, 0, output)

        # Status text
        cv2.putText(
            output,
            self.status_message,
            (15, h - 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2,
            cv2.LINE_AA
        )

        # Exit hint
        cv2.putText(
            output,
            "Press [ESC] to Exit | [R] to Reset to QR Scan",
            (15, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 180, 180),
            1,
            cv2.LINE_AA
        )

        return output

    def run(self) -> None:
        """Main execution loop for enrollment."""
        print("=" * 65)
        print("🚀 Starting SmartAttend-AI Student Enrollment & QR Verification")
        print("=" * 65)

        cap = cv2.VideoCapture(self.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            print(f"[ERROR] Could not open webcam at index {self.camera_index}.")
            return

        window_name = "SmartAttend-AI - Student Enrollment"
        prev_time = time.time()
        fps_smooth = 0.0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.05)
                    continue

                # Compute FPS
                curr_time = time.time()
                dt = curr_time - prev_time
                prev_time = curr_time
                instant_fps = (1.0 / dt) if dt > 0 else 0.0
                fps_smooth = (0.9 * fps_smooth) + (0.1 * instant_fps) if fps_smooth > 0 else instant_fps

                h, w = frame.shape[:2]

                # -------------------------------------------------------------
                # STATE 1: SCAN QR CODE
                # -------------------------------------------------------------
                if self.current_state == self.STATE_SCAN_QR:
                    self.status_message = "Step 1/2: Show Student QR Code to Camera"

                    token, points = self.qr_manager.scan_qr_frame(frame)
                    if points is not None:
                        self.qr_manager.draw_qr_box(frame, points, color=(0, 255, 255))

                    if token:
                        is_valid, msg, student_info = self.service.verify_qr(token)
                        if is_valid and student_info:
                            self.verified_student = student_info
                            self.current_state = self.STATE_FACE_ENROLL
                            self.sample_embeddings = []
                            self.last_capture_time = time.time()
                            print(f"\n[VERIFIED] QR Validated: {student_info['full_name']} ({student_info['student_id']})")
                        else:
                            self.status_message = f"[INVALID QR] {msg}"

                # -------------------------------------------------------------
                # STATE 2: FACE ENROLLMENT (Strict 1-Face Rule)
                # -------------------------------------------------------------
                elif self.current_state == self.STATE_FACE_ENROLL:
                    stu = self.verified_student
                    stu_header = f"Enrolling: {stu['full_name']} ({stu['student_id']}) - {stu['department']} Y{stu['year']}"
                    cv2.putText(frame, stu_header, (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 120), 2)

                    # Detect faces using Step 3 detector
                    detected_faces = self.detector.detect_faces(frame)
                    face_count = len(detected_faces)

                    # Enforce Exactly 1 Face
                    if face_count == 0:
                        self.status_message = "[ALERT] No face detected. Please face the camera."
                        # Draw guide box in center
                        center_box = (int(w*0.25), int(h*0.2), int(w*0.5), int(h*0.6))
                        cv2.rectangle(frame, (center_box[0], center_box[1]), (center_box[0]+center_box[2], center_box[1]+center_box[3]), (0, 165, 255), 2)
                    
                    elif face_count > 1:
                        self.status_message = f"[ERROR] {face_count} faces detected! Only 1 person allowed during enrollment."
                        for f in detected_faces:
                            cv2.rectangle(frame, (f.x, f.y), (f.x + f.w, f.y + f.h), (0, 0, 255), 2)
                    
                    else: # Exactly 1 face
                        face = detected_faces[0]
                        # Draw green box
                        cv2.rectangle(frame, (face.x, face.y), (face.x + face.w, face.y + face.h), (0, 255, 120), 2)

                        current_step_idx = len(self.sample_embeddings)
                        instruction = self.sample_instructions[min(current_step_idx, len(self.sample_instructions) - 1)]
                        self.status_message = instruction

                        # Check capture timer
                        if curr_time - self.last_capture_time >= self.capture_delay:
                            # Extract embedding from face
                            # Format mock/detected face for embedder
                            face_raw = np.array([face.x, face.y, face.w, face.h, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, face.confidence], dtype=np.float32)
                            emb = self.embedder.extract_embedding(frame, face_raw)
                            if emb is not None and len(emb) > 0:
                                self.sample_embeddings.append(emb)
                                self.last_capture_time = curr_time
                                print(f"[+] Captured face sample {len(self.sample_embeddings)}/{self.target_samples}")

                            # If all samples collected, save to database
                            if len(self.sample_embeddings) >= self.target_samples:
                                success, save_msg = self.service.store_face_embeddings(
                                    student_db_id=stu["id"],
                                    embeddings_list=self.sample_embeddings
                                )
                                if success:
                                    self.current_state = self.STATE_SUCCESS
                                    self.status_message = f"[COMPLETE] {stu['full_name']} registered and face enrolled!"
                                    print(f"\n[SUCCESS] {save_msg}")
                                else:
                                    self.status_message = f"[ERROR] Failed to save embeddings: {save_msg}"

                # -------------------------------------------------------------
                # STATE 3: ENROLLMENT SUCCESS
                # -------------------------------------------------------------
                elif self.current_state == self.STATE_SUCCESS:
                    stu = self.verified_student
                    cv2.putText(frame, "REGISTRATION & FACE ENROLLMENT COMPLETE!", (30, int(h*0.4)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 120), 2)
                    cv2.putText(frame, f"Student: {stu['full_name']} ({stu['student_id']})", (30, int(h*0.48)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    cv2.putText(frame, f"Face Embedding Stored in SQLite (128-D Vector)", (30, int(h*0.56)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)
                    cv2.putText(frame, "Press [R] to register another student or [ESC] to exit", (30, int(h*0.68)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 2)

                # Render master HUD
                display = self.draw_hud(frame, fps_smooth)
                cv2.imshow(window_name, display)

                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    print("\n[INFO] ESC key pressed. Exiting enrollment application...")
                    break
                elif key in (ord('r'), ord('R')):
                    # Reset
                    self.current_state = self.STATE_SCAN_QR
                    self.verified_student = None
                    self.sample_embeddings = []
                    print("\n[INFO] Resetting to QR Scanner mode...")

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user.")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("[OK] Camera released and windows closed cleanly.")


def main():
    app = InteractiveEnrollmentApp()
    app.run()


if __name__ == "__main__":
    main()
