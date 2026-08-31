"""
SmartAttend-AI: Live Liveness & Anti-Spoofing Verification Demo (Step 7)
=======================================================================
Real-time webcam verification checking multi-signal temporal motion,
landmark dynamics, and texture against photo/screen spoofs.
"""

import sys
import time
from typing import List, Optional
import cv2
import numpy as np

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from ai.face_recognition.detector import FaceDetector, DetectedFace
from ai.face_recognition.recognizer import FaceRecognizerService
from ai.liveness.detector import LivenessDetector, LivenessConfig, LivenessResult, LivenessState
from ai.models.download_models import download_yunet_model, YUNET_PATH


class LiveLivenessApp:
    """
    Live webcam GUI application for testing and demonstrating anti-spoofing and liveness.
    """

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        download_yunet_model()
        self.detector = FaceDetector(model_path=str(YUNET_PATH))
        self.liveness_detector = LivenessDetector(
            config=LivenessConfig(
                window_frames=12,
                min_frames_required=6,
                liveness_threshold=0.65,
                min_confidence=0.70
            )
        )
        self.recognizer = FaceRecognizerService()

    def draw_hud(
        self,
        frame: np.ndarray,
        faces: List[DetectedFace],
        liveness_res: LivenessResult,
        fps: float
    ) -> np.ndarray:
        """Renders step-specific liveness HUD and telemetry."""
        output = frame.copy()
        h, w = output.shape[:2]

        face_count = len(faces)

        # -------------------------------------------------------------
        # 1. Evaluate Visual Style based on Liveness State
        # -------------------------------------------------------------
        if face_count == 0:
            box_color = (0, 165, 255) # Orange
            state_text = "NO FACE DETECTED"
            state_color = (0, 165, 255)
        elif face_count > 1:
            box_color = (0, 0, 255)   # Red
            state_text = f"MULTIPLE FACES ({face_count}) - ONLY 1 PERSON ALLOWED"
            state_color = (0, 0, 255)
        elif liveness_res.state == LivenessState.LIVE:
            box_color = (0, 230, 115) # Green
            state_text = "LIVE (READY FOR ATTENDANCE)"
            state_color = (0, 255, 128)
        elif liveness_res.state == LivenessState.SPOOF:
            box_color = (0, 0, 255)   # Red
            state_text = "SPOOF DETECTED (ATTENDANCE REJECTED)"
            state_color = (0, 0, 255)
        else: # UNCERTAIN / CHECKING
            box_color = (0, 220, 255) # Cyan
            state_text = "CHECKING LIVENESS..."
            state_color = (0, 220, 255)

        # -------------------------------------------------------------
        # 2. Draw Face Bounding Boxes & Landmarks
        # -------------------------------------------------------------
        for face in faces:
            x1, y1, x2, y2 = face.xyxy
            cv2.rectangle(output, (x1, y1), (x2, y2), box_color, 2)

            # Draw 5 facial landmarks
            if face.landmarks:
                for idx, (lx, ly) in enumerate(face.landmarks):
                    pt = (int(lx), int(ly))
                    cv2.circle(output, pt, 3, (0, 255, 255), -1)

            # Face label tag
            cv2.rectangle(output, (x1, max(0, y1 - 22)), (x1 + 180, max(0, y1)), (15, 23, 42), -1)
            cv2.putText(
                output,
                f"Face #{1} ({liveness_res.state.value})",
                (x1 + 4, max(0, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                box_color,
                1,
                cv2.LINE_AA
            )

        # -------------------------------------------------------------
        # 3. Top Header Bar
        # -------------------------------------------------------------
        top_bar = output.copy()
        cv2.rectangle(top_bar, (0, 0), (w, 50), (15, 23, 42), -1)
        cv2.addWeighted(top_bar, 0.90, output, 0.10, 0, output)

        cv2.putText(
            output,
            "SmartAttend-AI | Liveness & Anti-Spoofing (Step 7)",
            (15, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        cv2.putText(
            output,
            f"FPS: {fps:.1f}",
            (w - 110, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            (0, 220, 255),
            2,
            cv2.LINE_AA
        )

        # -------------------------------------------------------------
        # 4. Bottom Status & Multi-Signal HUD Card
        # -------------------------------------------------------------
        bot_bar = output.copy()
        cv2.rectangle(bot_bar, (0, h - 90), (w, h), (15, 23, 42), -1)
        cv2.addWeighted(bot_bar, 0.90, output, 0.10, 0, output)

        # Primary Liveness State
        cv2.putText(
            output,
            f"Status: {state_text}",
            (15, h - 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            state_color,
            2,
            cv2.LINE_AA
        )

        # Signal Telemetry
        sig = liveness_res.signals
        telemetry = (
            f"Score: {liveness_res.liveness_score:.2f} | "
            f"Conf: {liveness_res.confidence:.2f} | "
            f"Motion: {sig.get('landmark_motion', 0.0):.2f} | "
            f"Geometry: {sig.get('geometry_dynamics', 0.0):.2f} | "
            f"Texture: {sig.get('texture_score', 0.0):.2f}"
        )
        cv2.putText(
            output,
            telemetry,
            (15, h - 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (200, 200, 200),
            1,
            cv2.LINE_AA
        )

        # Exit hint
        cv2.putText(
            output,
            "Press [ESC] to Exit | [R] to Reset Buffer",
            (15, h - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (150, 150, 150),
            1,
            cv2.LINE_AA
        )

        return output

    def run(self) -> None:
        """Starts live webcam liveness verification loop."""
        print("=" * 68)
        print("🛡️ Starting SmartAttend-AI Live Liveness & Anti-Spoofing Demo")
        print("=" * 68)
        print(f"[*] Accessing webcam (Device Index: {self.camera_index})...")

        cap = cv2.VideoCapture(self.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            print(f"[ERROR] Could not open webcam {self.camera_index}.")
            return

        window_name = "SmartAttend-AI - Liveness & Anti-Spoofing (Local)"
        prev_time = time.time()
        fps_smooth = 0.0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.05)
                    continue

                curr_time = time.time()
                dt = curr_time - prev_time
                prev_time = curr_time
                instant_fps = (1.0 / dt) if dt > 0 else 0.0
                fps_smooth = (0.9 * fps_smooth) + (0.1 * instant_fps) if fps_smooth > 0 else instant_fps

                # 1. Detect faces & extract 5 landmarks
                faces = self.detector.detect(frame)

                # 2. Process Liveness
                if len(faces) == 1:
                    face = faces[0]
                    self.liveness_detector.add_frame_sample(
                        frame=frame,
                        landmarks=face.landmarks,
                        bbox=face.bbox
                    )
                    liveness_res = self.liveness_detector.evaluate_liveness()
                elif len(faces) == 0:
                    self.liveness_detector.reset()
                    liveness_res = LivenessResult(
                        state=LivenessState.UNCERTAIN,
                        liveness_score=0.0,
                        confidence=0.0,
                        reason="NO_FACE_DETECTED"
                    )
                else:
                    self.liveness_detector.reset()
                    liveness_res = LivenessResult(
                        state=LivenessState.SPOOF,
                        liveness_score=0.0,
                        confidence=0.95,
                        reason="MULTIPLE_FACES_DETECTED"
                    )

                # 3. Draw HUD
                display = self.draw_hud(frame, faces, liveness_res, fps_smooth)
                cv2.imshow(window_name, display)

                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    print("\n[INFO] ESC pressed. Exiting liveness verifier cleanly...")
                    break
                elif key in (ord('r'), ord('R')):
                    self.liveness_detector.reset()
                    print("\n[INFO] Liveness temporal frame buffer reset.")

        except KeyboardInterrupt:
            print("\n[INFO] Interrupted by user.")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            print("[OK] Camera released and windows closed cleanly.")


def main():
    app = LiveLivenessApp()
    app.run()


if __name__ == "__main__":
    main()
