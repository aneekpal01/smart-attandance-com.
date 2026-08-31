"""
Utility to download pre-trained computer vision model weights.
"""

import os
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).parent.resolve()

YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
YUNET_PATH = MODELS_DIR / "face_detection_yunet_2023mar.onnx"

SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
SFACE_PATH = MODELS_DIR / "face_recognition_sface_2021dec.onnx"


def download_yunet_model() -> Path:
    """Downloads the OpenCV YuNet face detection ONNX model if not already present."""
    if not YUNET_PATH.exists():
        print(f"Downloading YuNet Face Detection model to {YUNET_PATH}...")
        urllib.request.urlretrieve(YUNET_URL, YUNET_PATH)
        print("YuNet Download complete!")
    return YUNET_PATH


def download_sface_model() -> Path:
    """Downloads the OpenCV SFace face recognition ONNX model if not already present."""
    if not SFACE_PATH.exists():
        print(f"Downloading SFace Face Recognition model to {SFACE_PATH}...")
        urllib.request.urlretrieve(SFACE_URL, SFACE_PATH)
        print("SFace Download complete!")
    return SFACE_PATH


def ensure_all_models():
    download_yunet_model()
    download_sface_model()


if __name__ == "__main__":
    ensure_all_models()
