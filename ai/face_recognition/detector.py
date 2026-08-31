"""
Face Detection Module (Step 1)
High-accuracy face detection using OpenCV YuNet / YOLO.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path
import cv2
import numpy as np


@dataclass
class DetectedFace:
    """Represents a detected face with bounding box, score, and facial landmarks."""
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    confidence: float
    landmarks: Optional[List[Tuple[float, float]]] = None  # (right_eye, left_eye, nose_tip, mouth_right, mouth_left)

    @property
    def xyxy(self) -> Tuple[int, int, int, int]:
        """Returns (x1, y1, x2, y2) format."""
        x, y, w, h = self.bbox
        return (x, y, x + w, y + h)

    def crop(self, frame: np.ndarray, margin: float = 0.1) -> np.ndarray:
        """Crops the detected face from the frame with an optional margin."""
        h_img, w_img = frame.shape[:2]
        x1, y1, x2, y2 = self.xyxy
        
        # Add margin
        margin_x = int((x2 - x1) * margin)
        margin_y = int((y2 - y1) * margin)
        
        x1 = max(0, x1 - margin_x)
        y1 = max(0, y1 - margin_y)
        x2 = min(w_img, x2 + margin_x)
        y2 = min(h_img, y2 + margin_y)
        
        return frame[y1:y2, x1:x2]


class FaceDetector:
    """
    High-accuracy, real-time Face Detector.
    Uses OpenCV YuNet ONNX model for face detection + 5-point landmark localization.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        model_path: Optional[str] = None,
        input_size: Tuple[int, int] = (320, 320),
    ):
        self.conf_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.input_size = input_size
        self.detector = None

        if model_path and Path(model_path).exists():
            try:
                # cv2.FaceDetectorYN is OpenCV's official YuNet detector
                self.detector = cv2.FaceDetectorYN.create(
                    model=str(model_path),
                    config="",
                    input_size=self.input_size,
                    score_threshold=self.conf_threshold,
                    nms_threshold=self.nms_threshold,
                    top_k=5000,
                )
            except Exception as e:
                print(f"Warning: Failed to load YuNet detector: {e}")

    def detect(self, frame: np.ndarray) -> List[DetectedFace]:
        """
        Detects faces in a BGR frame.
        Returns a list of DetectedFace objects.
        """
        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]

        if self.detector is not None:
            # Set input frame dimensions
            self.detector.setInputSize((w, h))
            _, faces = self.detector.detect(frame)
            results: List[DetectedFace] = []
            if faces is not None:
                for face in faces:
                    box = [int(v) for v in face[0:4]]
                    conf = float(face[-1])
                    landmarks = [
                        (float(face[4]), float(face[5])),   # right eye
                        (float(face[6]), float(face[7])),   # left eye
                        (float(face[8]), float(face[9])),   # nose tip
                        (float(face[10]), float(face[11])), # mouth right
                        (float(face[12]), float(face[13])), # mouth left
                    ]
                    results.append(
                        DetectedFace(
                            bbox=(box[0], box[1], box[2], box[3]),
                            confidence=conf,
                            landmarks=landmarks,
                        )
                    )
                return results

        return []

    @staticmethod
    def draw_faces(
        frame: np.ndarray,
        faces: List[DetectedFace],
        draw_landmarks: bool = True,
        color: Tuple[int, int, int] = (0, 255, 128),
    ) -> np.ndarray:
        """
        Renders bounding boxes and landmarks onto the frame.
        """
        annotated = frame.copy()
        for i, face in enumerate(faces):
            x1, y1, x2, y2 = face.xyxy
            # Bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Label
            label = f"Face #{i+1} ({face.confidence:.2f})"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(
                annotated,
                (x1, max(0, y1 - 22)),
                (x1 + tw + 6, max(0, y1)),
                color,
                -1,
            )
            cv2.putText(
                annotated,
                label,
                (x1 + 3, max(0, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

            # Landmarks
            if draw_landmarks and face.landmarks:
                for idx, (lx, ly) in enumerate(face.landmarks):
                    pt = (int(lx), int(ly))
                    lm_color = (0, 0, 255) if idx < 2 else ((0, 255, 255) if idx == 2 else (255, 0, 0))
                    cv2.circle(annotated, pt, 3, lm_color, -1)

        return annotated
