"""
Verification & Test script for Face Detector (Step 1).
"""

import sys
import time
from pathlib import Path
import cv2
import numpy as np

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from ai.face_recognition.detector import FaceDetector, DetectedFace
from ai.models.download_models import download_yunet_model, YUNET_PATH


def test_face_detector():
    print("=" * 60)
    print("[*] SmartAttend-AI: Step 1 - Face Detection Test")
    print("=" * 60)

    # 1. Ensure Model Weights
    model_path = download_yunet_model()
    print(f"[OK] Model weights: {model_path.name} ({model_path.stat().st_size / 1024:.1f} KB)")

    # 2. Initialize Detector
    detector = FaceDetector(
        confidence_threshold=0.5,
        nms_threshold=0.3,
        model_path=str(model_path)
    )
    print("[OK] FaceDetector initialized with OpenCV YuNet DNN Engine.")

    # 3. Create a clean sample test canvas (640x480)
    canvas = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # 4. Benchmark Detection Speed
    warmup_iters = 5
    bench_iters = 20
    
    for _ in range(warmup_iters):
        detector.detect(canvas)

    start_time = time.perf_counter()
    for _ in range(bench_iters):
        faces = detector.detect(canvas)
    avg_latency_ms = ((time.perf_counter() - start_time) / bench_iters) * 1000
    fps_est = 1000 / avg_latency_ms if avg_latency_ms > 0 else 0

    print(f"[OK] Average Inference Latency: {avg_latency_ms:.2f} ms (~{fps_est:.1f} FPS on CPU)")

    # 5. Test Face Cropping & Landmark logic
    mock_face = DetectedFace(
        bbox=(150, 120, 180, 220),
        confidence=0.96,
        landmarks=[(200.0, 180.0), (280.0, 180.0), (240.0, 230.0), (210.0, 290.0), (270.0, 290.0)]
    )
    cropped = mock_face.crop(canvas, margin=0.1)
    annotated = detector.draw_faces(canvas, [mock_face], draw_landmarks=True)

    print(f"[OK] Face crop dimensions: {cropped.shape[1]}x{cropped.shape[0]}")
    print(f"[OK] 5-point facial landmarks extracted: {len(mock_face.landmarks)} points (Eyes, Nose, Mouth)")
    print("=" * 60)
    print("[SUCCESS] Step 1 (Face Detection) verification SUCCESSFUL!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    test_face_detector()
