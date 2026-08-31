"""
SmartAttend-AI: Live Webcam Face Recognition Application (Step 5)
=================================================================
Runs real-time multi-face recognition against local SQLite enrolled database.
Displays live HUD with student name, ID, similarity score, FPS, and face metrics.
"""

import sys
import time
from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from ai.face_recognition.recognizer import (
    FaceRecognizerService,
    RecognitionResult,
    DEFAULT_RECOGNITION_THRESHOLD,
    DEFAULT_DETECTION_CONFIDENCE
)
from database.db_manager import DatabaseManager


class LiveFaceRecognizerApp:
    """
    Real-time live webcam face recognition GUI application.
    """

    def __init__(
        self,
        camera_index: int = 0,
        recognition_threshold: float = DEFAULT_RECOGNITION_THRESHOLD,
        detection_confidence: float = DEFAULT_DETECTION_CONFIDENCE,
        window_title: str = "SmartAttend-AI - Face Recognition (Local)"
    ):
        self.camera_index = camera_index
        self.recognition_threshold = recognition_threshold
        self.detection_confidence = detection_confidence
        self.window_title = window_title

        self.db = DatabaseManager()
        self.recognizer = FaceRecognizerService(
            db_manager=self.db,
            recognition_threshold=self.recognition_threshold,
            confidence_threshold=self.detection_confidence,
            enable_smoothing=True
        )

    def draw_hud(
        self,
        frame: np.ndarray,
        results: List[RecognitionResult],
        fps: float,
        latency_ms: float
    ) -> np.ndarray:
        """
        Renders bounding boxes, recognition cards, and top/bottom metric HUD bars.
        """
        output = frame.copy()
        h, w = output.shape[:2]

        recognized_count = sum(1 for r in results if r.is_recognized)
        unknown_count = len(results) - recognized_count

        # -------------------------------------------------------------
        # 1. Render Face Boxes & Identity Cards
        # -------------------------------------------------------------
        for res in results:
            x1, y1, x2, y2 = res.box.xyxy

            # Color scheme: Emerald Green for RECOGNIZED, Orange/Red for UNKNOWN
            if res.is_recognized:
                box_color = (0, 230, 115)    # Green
                badge_bg = (10, 35, 20)
                status_color = (0, 255, 128)
            else:
                box_color = (0, 140, 255)    # Orange / Amber
                badge_bg = (35, 20, 10)
                status_color = (0, 165, 255)

            # Main bounding box
            cv2.rectangle(output, (x1, y1), (x2, y2), box_color, 2)

            # Corner accents
            c_len = max(10, int(min(res.box.w, res.box.h) * 0.2))
            th = 3
            # Top-left
            cv2.line(output, (x1, y1), (x1 + c_len, y1), box_color, th)
            cv2.line(output, (x1, y1), (x1, y1 + c_len), box_color, th)
            # Top-right
            cv2.line(output, (x2, y1), (x2 - c_len, y1), box_color, th)
            cv2.line(output, (x2, y1), (x2, y1 + c_len), box_color, th)
            # Bottom-left
            cv2.line(output, (x1, y2), (x1 + c_len, y2), box_color, th)
            cv2.line(output, (x1, y2), (x1, y2 - c_len), box_color, th)
            # Bottom-right
            cv2.line(output, (x2, y2), (x2 - c_len, y2), box_color, th)
            cv2.line(output, (x2, y2), (x2, y2 - c_len), box_color, th)

            # Info Card above/below face
            card_h = 42 if res.is_recognized else 36
            card_w = max(160, res.box.w + 20)
            card_y1 = max(55, y1 - card_h - 6)
            card_y2 = card_y1 + card_h
            card_x1 = max(10, x1)
            card_x2 = min(w - 10, card_x1 + card_w)

            # Card background
            card_overlay = output.copy()
            cv2.rectangle(card_overlay, (card_x1, card_y1), (card_x2, card_y2), badge_bg, -1)
            cv2.addWeighted(card_overlay, 0.85, output, 0.15, 0, output)
            cv2.rectangle(output, (card_x1, card_y1), (card_x2, card_y2), box_color, 1)

            if res.is_recognized:
                # Line 1: Student Name & Status
                name_text = f"{res.student_name}"
                cv2.putText(output, name_text, (card_x1 + 6, card_y1 + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
                # Line 2: ID & Similarity
                detail_text = f"ID: {res.student_id} | Sim: {res.similarity:.2f}"
                cv2.putText(output, detail_text, (card_x1 + 6, card_y1 + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.40, status_color, 1, cv2.LINE_AA)
            else:
                # Unknown Card
                cv2.putText(output, "Name: UNKNOWN", (card_x1 + 6, card_y1 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(output, f"NOT RECOGNIZED ({res.similarity:.2f})", (card_x1 + 6, card_y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.38, status_color, 1, cv2.LINE_AA)

        # -------------------------------------------------------------
        # 2. Top Header HUD Bar
        # -------------------------------------------------------------
        top_bar = output.copy()
        cv2.rectangle(top_bar, (0, 0), (w, 48), (15, 23, 42), -1)
        cv2.addWeighted(top_bar, 0.90, output, 0.10, 0, output)

        # Title
        cv2.putText(output, "SmartAttend-AI | Face Recognition", (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)

        # Metrics on top right
        rec_tag = f"Rec: {recognized_count}"
        unk_tag = f"Unk: {unknown_count}"
        fps_tag = f"FPS: {fps:.1f}"
        lat_tag = f"{latency_ms:.1f}ms"

        cv2.putText(output, rec_tag, (w - 380, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 128), 2, cv2.LINE_AA)
        cv2.putText(output, unk_tag, (w - 280, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 165, 255), 2, cv2.LINE_AA)
        cv2.putText(output, fps_tag, (w - 180, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 220, 255), 2, cv2.LINE_AA)
        cv2.putText(output, lat_tag, (w - 85, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)

        # -------------------------------------------------------------
        # 3. Bottom Footer HUD Bar
        # -------------------------------------------------------------
        bot_bar = output.copy()
        cv2.rectangle(bot_bar, (0, h - 35), (w, h), (15, 23, 42), -1)
        cv2.addWeighted(bot_bar, 0.90, output, 0.10, 0, output)

        enrolled_total = len(self.recognizer.enrolled_students)
        info_text = f"Enrolled: {enrolled_total} Students | Threshold: {self.recognition_threshold:.2f} | Press [ESC] to Exit"
        cv2.putText(output, info_text, (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

        return output

    def run(self) -> None:
        """
        Starts the real-time webcam face recognition loop.
        """
        print("=" * 65)
        print("🚀 Starting SmartAttend-AI Local Face Recognition (Step 5)")
        print("=" * 65)
        print(f"[*] Accessing webcam (Device Index: {self.camera_index})...")

        cap = cv2.VideoCapture(self.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            print(f"[ERROR] Could not open webcam at index {self.camera_index}.")
            return

        enrolled_count = len(self.recognizer.enrolled_students)
        print(f"[OK] Loaded {enrolled_count} enrolled students from SQLite database.")
        print(f"[*] Recognition Threshold: {self.recognition_threshold:.2f}")
        print("[*] Controls: Press [ESC] to exit | [R] to reload database cache.")
        print("=" * 65)

        prev_time = time.time()
        fps_smooth = 0.0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.05)
                    continue

                # Calculate smoothed FPS
                curr_time = time.time()
                dt = curr_time - prev_time
                prev_time = curr_time
                instant_fps = (1.0 / dt) if dt > 0 else 0.0
                fps_smooth = (0.9 * fps_smooth) + (0.1 * instant_fps) if fps_smooth > 0 else instant_fps

                # Run Face Recognition Pipeline
                results, latency_ms = self.recognizer.recognize_frame(frame)

                # Render HUD
                display = self.draw_hud(frame, results, fps_smooth, latency_ms)
                cv2.imshow(self.window_title, display)

                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    print("\n[INFO] ESC key pressed. Exiting Face Recognition cleanly...")
                    break
                elif key in (ord('r'), ord('R')):
                    reloaded = self.recognizer.reload_enrolled_cache()
                    print(f"\n[INFO] Database cache reloaded: {reloaded} enrolled students.")

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user.")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("[OK] Webcam released and windows closed cleanly.")


def main():
    app = LiveFaceRecognizerApp(
        camera_index=0,
        recognition_threshold=DEFAULT_RECOGNITION_THRESHOLD,
        detection_confidence=DEFAULT_DETECTION_CONFIDENCE
    )
    app.run()


if __name__ == "__main__":
    main()
