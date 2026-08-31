"""
SmartAttend-AI: Local Live Webcam Face Detection Module
======================================================
Objective:
    Webcam Capture -> Face Detection -> Bounding Boxes -> Face Count -> FPS Display

Key Characteristics:
    - 100% Local (No external API, No cloud, No database)
    - Pluggable/Extensible Architecture (BaseFaceDetector interface)
    - Clean exit with ESC key
"""

import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import numpy as np

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Data Structures & Base Interface (For Modular & Upgradable Architecture)
# ---------------------------------------------------------------------------

@dataclass
class FaceBox:
    """Represents a single detected face bounding box and metadata."""
    x: int
    y: int
    w: int
    h: int
    confidence: float = 1.0

    @property
    def xyxy(self) -> Tuple[int, int, int, int]:
        """Returns coordinates as (x1, y1, x2, y2)."""
        return self.x, self.y, self.x + self.w, self.y + self.h


class BaseFaceDetector(ABC):
    """
    Abstract Base Class for Face Detectors.
    Allows easy replacement with other models (e.g., YOLO-Face, RetinaFace, MediaPipe)
    without modifying the camera loop or UI rendering logic.
    """

    @abstractmethod
    def detect_faces(self, frame: np.ndarray) -> List[FaceBox]:
        """
        Detects faces in a single frame.
        
        Args:
            frame (np.ndarray): BGR image frame from OpenCV.
            
        Returns:
            List[FaceBox]: List of detected face bounding boxes.
        """
        pass


# ---------------------------------------------------------------------------
# 2. Concrete Detector Implementation (OpenCV YuNet DNN / Haar Cascade)
# ---------------------------------------------------------------------------

class OpenCVFaceDetector(BaseFaceDetector):
    """
    High-accuracy local face detector using OpenCV DNN / YuNet model.
    Falls back gracefully to OpenCV Cascade Classifier if ONNX weights are not present.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.5,
        nms_threshold: float = 0.3
    ):
        self.conf_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.yunet_detector = None
        
        # Resolve default model path if not provided
        if model_path is None:
            default_path = Path(__file__).resolve().parent.parent / "models" / "face_detection_yunet_2023mar.onnx"
            if default_path.exists():
                model_path = str(default_path)

        # Attempt to load OpenCV YuNet ONNX detector
        if model_path and Path(model_path).exists():
            try:
                self.yunet_detector = cv2.FaceDetectorYN.create(
                    model=str(model_path),
                    config="",
                    input_size=(320, 320),
                    score_threshold=self.conf_threshold,
                    nms_threshold=self.nms_threshold,
                    top_k=5000
                )
                print(f"[INFO] Loaded OpenCV YuNet DNN model from: {model_path}")
            except Exception as err:
                print(f"[WARNING] Could not load YuNet model ({err}). Falling back to Haar Cascade.")
                self.yunet_detector = None

        # Fallback to Haar Cascade
        self.haar_cascade = None
        if self.yunet_detector is None:
            haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            if Path(haar_path).exists():
                self.haar_cascade = cv2.CascadeClassifier(haar_path)
                print(f"[INFO] Loaded Haar Cascade fallback from: {haar_path}")

    def detect_faces(self, frame: np.ndarray) -> List[FaceBox]:
        """Runs face detection on the input frame."""
        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]

        # Method 1: YuNet DNN Detector
        if self.yunet_detector is not None:
            self.yunet_detector.setInputSize((w, h))
            _, faces = self.yunet_detector.detect(frame)
            results = []
            if faces is not None:
                for face in faces:
                    x, y, box_w, box_h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                    # Bound values inside frame dimensions
                    x = max(0, x)
                    y = max(0, y)
                    box_w = min(w - x, box_w)
                    box_h = min(h - y, box_h)
                    conf = float(face[-1])
                    results.append(FaceBox(x=x, y=y, w=box_w, h=box_h, confidence=conf))
            return results

        # Method 2: Haar Cascade Fallback
        if self.haar_cascade is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.haar_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(40, 40)
            )
            return [FaceBox(x=int(x), y=int(y), w=int(bw), h=int(bh), confidence=0.85) for (x, y, bw, bh) in faces]

        return []


# ---------------------------------------------------------------------------
# 3. Live Webcam Stream & HUD Visualizer
# ---------------------------------------------------------------------------

class LiveWebcamFaceApp:
    """
    Manages webcam capture loop, real-time face detection, HUD rendering,
    and clean shutdown handling.
    """

    def __init__(
        self,
        camera_index: int = 0,
        detector: Optional[BaseFaceDetector] = None,
        window_title: str = "SmartAttend-AI - Face Detection (Local)"
    ):
        self.camera_index = camera_index
        self.detector = detector or OpenCVFaceDetector()
        self.window_title = window_title

    def draw_hud(
        self,
        frame: np.ndarray,
        faces: List[FaceBox],
        fps: float
    ) -> np.ndarray:
        """
        Draws bounding boxes around detected faces and renders HUD metrics
        (Face count, FPS counter, status indicator, exit instructions).
        """
        output = frame.copy()
        h, w = output.shape[:2]

        # 1. Draw Bounding Boxes for each detected face
        for idx, face in enumerate(faces):
            x1, y1, x2, y2 = face.xyxy

            # Main bounding box
            color = (0, 255, 120)  # Bright Green
            cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)

            # Corner accents for a modern UI look
            line_len = max(10, int(min(face.w, face.h) * 0.2))
            thickness = 3
            # Top-left
            cv2.line(output, (x1, y1), (x1 + line_len, y1), color, thickness)
            cv2.line(output, (x1, y1), (x1, y1 + line_len), color, thickness)
            # Top-right
            cv2.line(output, (x2, y1), (x2 - line_len, y1), color, thickness)
            cv2.line(output, (x2, y1), (x2, y1 + line_len), color, thickness)
            # Bottom-left
            cv2.line(output, (x1, y2), (x1 + line_len, y2), color, thickness)
            cv2.line(output, (x1, y2), (x1, y2 - line_len), color, thickness)
            # Bottom-right
            cv2.line(output, (x2, y2), (x2 - line_len, y2), color, thickness)
            cv2.line(output, (x2, y2), (x2, y2 - line_len), color, thickness)

            # Face label tag
            label = f"Face #{idx + 1} ({int(face.confidence * 100)}%)"
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(
                output,
                (x1, max(0, y1 - 20)),
                (x1 + label_w + 8, max(0, y1)),
                (20, 20, 20),
                -1
            )
            cv2.putText(
                output,
                label,
                (x1 + 4, max(0, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 255, 120),
                1,
                cv2.LINE_AA
            )

        # 2. Top Status HUD Bar
        overlay = output.copy()
        cv2.rectangle(overlay, (0, 0), (w, 45), (15, 23, 42), -1)
        cv2.addWeighted(overlay, 0.85, output, 0.15, 0, output)

        # 3. Status Badges & Text
        face_count_text = f"Faces: {len(faces)}"
        fps_text = f"FPS: {fps:.1f}"
        exit_hint = "Press [ESC] to Exit"

        # Brand / Module Name
        cv2.putText(
            output,
            "SmartAttend-AI | Vision Module",
            (15, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        # Face Count Badge
        badge_color = (0, 220, 100) if len(faces) > 0 else (120, 120, 120)
        cv2.putText(
            output,
            face_count_text,
            (w - 300, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            badge_color,
            2,
            cv2.LINE_AA
        )

        # FPS Counter
        cv2.putText(
            output,
            fps_text,
            (w - 180, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 215, 255),
            2,
            cv2.LINE_AA
        )

        # Bottom Exit Instruction Bar
        cv2.putText(
            output,
            exit_hint,
            (15, h - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 180, 180),
            1,
            cv2.LINE_AA
        )

        return output

    def run(self) -> None:
        """
        Starts the continuous live webcam capture loop.
        Processes frames, detects faces, renders HUD, and listens for ESC key to exit.
        """
        print("=" * 65)
        print("📹 Starting SmartAttend-AI Local Face Detection Module")
        print("=" * 65)
        print(f"[*] Accessing default webcam (Device Index: {self.camera_index})...")

        # Open webcam
        cap = cv2.VideoCapture(self.camera_index)

        # Optimize camera stream properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        if not cap.isOpened():
            print(f"[ERROR] Could not open webcam (Device Index: {self.camera_index}).")
            print("[HINT] Please ensure your webcam is connected and not in use by another application.")
            return

        print("[OK] Webcam connected successfully.")
        print("[*] Controls: Press [ESC] key inside the camera window to exit cleanly.")
        print("=" * 65)

        prev_time = time.time()
        fps_smooth = 0.0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("[WARNING] Failed to grab frame from webcam. Retrying...")
                    time.sleep(0.05)
                    continue

                # Compute real-time FPS with simple exponential smoothing
                current_time = time.time()
                delta = current_time - prev_time
                prev_time = current_time
                instant_fps = (1.0 / delta) if delta > 0 else 0.0
                fps_smooth = (0.9 * fps_smooth) + (0.1 * instant_fps) if fps_smooth > 0 else instant_fps

                # 1. Detect faces in current frame
                detected_faces = self.detector.detect_faces(frame)

                # 2. Render HUD (Bounding boxes, Face count, FPS counter)
                display_frame = self.draw_hud(frame, detected_faces, fps_smooth)

                # 3. Display live feed
                cv2.imshow(self.window_title, display_frame)

                # 4. Listen for ESC key (ASCII code 27) to exit cleanly
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC key
                    print("\n[INFO] ESC key pressed. Exiting camera stream cleanly...")
                    break

        except KeyboardInterrupt:
            print("\n[INFO] KeyboardInterrupt received. Exiting...")
        finally:
            # Clean resource release
            cap.release()
            cv2.destroyAllWindows()
            print("[OK] Webcam released and windows closed cleanly.")


# ---------------------------------------------------------------------------
# 4. Entry Point
# ---------------------------------------------------------------------------

def main():
    """Main execution function."""
    app = LiveWebcamFaceApp(camera_index=0)
    app.run()


if __name__ == "__main__":
    main()
