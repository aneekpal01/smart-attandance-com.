"""
SmartAttend-AI: Live Classroom Attendance Camera Application (Step 6)
====================================================================
Real-time classroom camera attendance monitoring with dynamic session timer,
instant attendance logging, duplicate prevention, and HUD metrics.
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import cv2
import numpy as np

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from database.db_manager import DatabaseManager
from ai.attendance.session_manager import SessionManager
from ai.attendance.attendance_engine import AttendanceEngine
from ai.face_recognition.recognizer import RecognitionResult


class LiveClassroomAttendanceApp:
    """
    Live classroom attendance GUI application.
    """

    def __init__(
        self,
        session_code: Optional[str] = None,
        camera_index: int = 0,
        recognition_threshold: float = 0.60
    ):
        self.camera_index = camera_index
        self.db = DatabaseManager()
        self.session_mgr = SessionManager(db_manager=self.db)
        self.engine = AttendanceEngine(
            db_manager=self.db,
            recognition_threshold=recognition_threshold
        )
        self.session_code = session_code
        self.session: Optional[Dict[str, Any]] = None

    def select_or_load_session(self) -> bool:
        """Loads the session by code or prompts the user."""
        if self.session_code:
            self.session = self.db.get_session_by_code(self.session_code)

        if not self.session:
            active_sessions = self.db.list_active_sessions()
            if not active_sessions:
                print("[ERROR] No active classroom sessions found. Please create one using faculty_session_cli.py.")
                return False
            # Default to the most recent active session
            self.session = active_sessions[0]
            print(f"[INFO] Using active session: {self.session['subject']} [{self.session['session_code']}]")

        return True

    def draw_hud(
        self,
        frame: np.ndarray,
        recognition_results: List[RecognitionResult],
        fps: float,
        latency_ms: float,
        current_time: datetime
    ) -> np.ndarray:
        """Renders classroom attendance HUD."""
        output = frame.copy()
        h, w = output.shape[:2]

        sess = self.session
        timing_ok, timing_status = self.session_mgr.evaluate_timing_status(sess, current_time)

        # -------------------------------------------------------------
        # 1. Render Face Boxes & Attendance Badges
        # -------------------------------------------------------------
        for res in recognition_results:
            x1, y1, x2, y2 = res.box.xyxy

            if res.is_recognized:
                # Check attendance record in DB
                att_record = self.db.get_student_session_attendance(sess["id"], res.student_db_id)
                if att_record:
                    box_color = (0, 230, 115)  # Green
                    badge_status = f"MARKED: {att_record['status']}"
                else:
                    box_color = (0, 220, 255)  # Cyan
                    badge_status = f"MATCH: {timing_status}"
            else:
                box_color = (0, 140, 255)  # Amber
                badge_status = "NOT RECOGNIZED"

            cv2.rectangle(output, (x1, y1), (x2, y2), box_color, 2)

            # Badge card
            card_y1 = max(55, y1 - 42)
            card_y2 = card_y1 + 38
            card_x1 = max(10, x1)
            card_x2 = min(w - 10, card_x1 + max(160, res.box.w + 20))

            card_overlay = output.copy()
            cv2.rectangle(card_overlay, (card_x1, card_y1), (card_x2, card_y2), (15, 23, 42), -1)
            cv2.addWeighted(card_overlay, 0.85, output, 0.15, 0, output)
            cv2.rectangle(output, (card_x1, card_y1), (card_x2, card_y2), box_color, 1)

            if res.is_recognized:
                cv2.putText(output, f"{res.student_name} ({res.student_id})", (card_x1 + 6, card_y1 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(output, f"{badge_status} | Sim: {res.similarity:.2f}", (card_x1 + 6, card_y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.40, box_color, 1, cv2.LINE_AA)
            else:
                cv2.putText(output, "Name: UNKNOWN", (card_x1 + 6, card_y1 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(output, f"{badge_status} ({res.similarity:.2f})", (card_x1 + 6, card_y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 165, 255), 1, cv2.LINE_AA)

        # -------------------------------------------------------------
        # 2. Top Header HUD Bar
        # -------------------------------------------------------------
        top_bar = output.copy()
        cv2.rectangle(top_bar, (0, 0), (w, 50), (15, 23, 42), -1)
        cv2.addWeighted(top_bar, 0.90, output, 0.10, 0, output)

        cv2.putText(
            output,
            f"Class: {sess['subject']} [{sess['session_code']}]",
            (15, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        cv2.putText(
            output,
            f"Room: {sess['room']} | {sess['department']} Y{sess['year']}-{sess['section']}",
            (15, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            (180, 180, 180),
            1,
            cv2.LINE_AA
        )

        # Attendance Counters
        summary = self.engine.get_session_summary(sess["id"])
        pres_c = summary["present_count"] if summary else 0
        late_c = summary["late_count"] if summary else 0

        cv2.putText(output, f"Pres: {pres_c}", (w - 280, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 128), 2, cv2.LINE_AA)
        cv2.putText(output, f"Late: {late_c}", (w - 200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 220, 255), 2, cv2.LINE_AA)
        cv2.putText(output, f"FPS: {fps:.1f}", (w - 110, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 0), 2, cv2.LINE_AA)

        # -------------------------------------------------------------
        # 3. Bottom Footer Window Status Bar
        # -------------------------------------------------------------
        bot_bar = output.copy()
        cv2.rectangle(bot_bar, (0, h - 35), (w, h), (15, 23, 42), -1)
        cv2.addWeighted(bot_bar, 0.90, output, 0.10, 0, output)

        if timing_status == "PRESENT":
            status_text = "🟢 Regular Attendance Window Active (Marking PRESENT)"
            col = (0, 255, 128)
        elif timing_status == "LATE":
            status_text = "🟡 Late Attendance Window Active (Marking LATE)"
            col = (0, 220, 255)
        else:
            status_text = "🔴 Attendance Window Closed"
            col = (0, 0, 255)

        cv2.putText(output, status_text, (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        cv2.putText(output, "Press [ESC] to Exit", (w - 150, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

        return output

    def run(self) -> None:
        """Starts the live classroom attendance loop."""
        if not self.select_or_load_session():
            return

        print("=" * 65)
        print("🚀 Starting SmartAttend-AI Live Classroom Attendance System")
        print("=" * 65)
        print(f"Session : {self.session['subject']} [{self.session['session_code']}]")
        print(f"Room    : {self.session['room']} | Faculty: {self.session['faculty_name']}")
        print("[*] Accessing camera...")

        cap = cv2.VideoCapture(self.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            print(f"[ERROR] Could not open camera {self.camera_index}.")
            return

        window_title = f"SmartAttend-AI - Classroom Attendance [{self.session['session_code']}]"
        prev_time = time.time()
        fps_smooth = 0.0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.05)
                    continue

                now = datetime.now()
                dt = time.time() - prev_time
                prev_time = time.time()
                instant_fps = (1.0 / dt) if dt > 0 else 0.0
                fps_smooth = (0.9 * fps_smooth) + (0.1 * instant_fps) if fps_smooth > 0 else instant_fps

                # 1. Process recognition and mark attendance
                rec_results, latency_ms = self.engine.recognizer.recognize_frame(frame)

                # 2. Auto-record attendance for recognized students
                timing_ok, timing_status = self.session_mgr.evaluate_timing_status(self.session, now)
                if timing_ok:
                    for r in rec_results:
                        if r.is_recognized and r.student_db_id:
                            # Check and record
                            att_code = f"ATT-{r.student_id}-{self.session['session_code']}"
                            ok, msg, _ = self.db.record_attendance(
                                attendance_code=att_code,
                                session_id=self.session["id"],
                                student_id=r.student_db_id,
                                status=timing_status,
                                similarity_score=r.similarity,
                                verification_method="FACE_RECOGNITION"
                            )
                            if ok:
                                print(f"[+] Attendance Marked: {r.student_name} ({r.student_id}) as {timing_status} (Sim: {r.similarity:.2f})")

                # 3. Render HUD
                display = self.draw_hud(frame, rec_results, fps_smooth, latency_ms, now)
                cv2.imshow(window_title, display)

                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    print("\n[INFO] ESC key pressed. Exiting live attendance...")
                    break

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user.")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("[OK] Camera released cleanly.")


def main():
    app = LiveClassroomAttendanceApp()
    app.run()


if __name__ == "__main__":
    main()
