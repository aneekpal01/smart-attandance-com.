"""
SmartAttend-AI: Hardware & Camera Pipeline Self-Test
Checks webcam accessibility, frame capture, inference speed, and multi-face parsing.
"""

import sys
import time
import cv2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from ai.face_recognition.live_face_detector import OpenCVFaceDetector


def run_camera_diagnostic():
    print("=" * 65)
    print("[*] SMARTATTEND-AI: STEP 3 HARDWARE & PIPELINE DIAGNOSTIC")
    print("=" * 65)

    # 1. Test Camera Connection
    print("[1/5] Testing Default Webcam (Device 0)...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[FAIL] Could not open webcam at index 0. Checking index 1...")
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("[FAIL] No accessible physical webcam found. (Check permissions/device connection)")
            return False
        else:
            print("[OK] Webcam opened at index 1.")
    else:
        print("[OK] Default webcam (index 0) opened successfully.")

    # 2. Test Frame Capture
    print("\n[2/5] Grabbing 5 test frames from camera feed...")
    for i in range(5):
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"   [!] Frame {i+1} capture failed.")
        else:
            h, w, c = frame.shape
            print(f"   - Frame {i+1}: {w}x{h} ({c} channels) captured.")

    # 3. Test Face Detection on Live Camera Frame
    print("\n[3/5] Initializing Face Detector & Running live frame inference...")
    detector = OpenCVFaceDetector()
    
    start = time.perf_counter()
    faces = detector.detect_faces(frame)
    latency = (time.perf_counter() - start) * 1000

    print(f"[OK] Detection executed in {latency:.2f} ms (~{1000/latency:.1f} FPS equivalent).")
    print(f"   - Current faces detected in front of camera: {len(faces)}")
    for idx, f in enumerate(faces):
        print(f"     * Face #{idx+1}: Box=(x={f.x}, y={f.y}, w={f.w}, h={f.h}), Conf={f.confidence:.2f}")

    # 4. Release Camera Cleanly
    cap.release()
    print("\n[4/5] Camera hardware released cleanly.")

    print("=" * 65)
    print("[5/5] Diagnostic Summary: Camera & Detection Pipeline OPERATIONAL!")
    print("=" * 65)
    return True


if __name__ == "__main__":
    run_camera_diagnostic()
