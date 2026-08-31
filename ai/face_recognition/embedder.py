"""
SmartAttend-AI: Face Embedding & Feature Extraction Module
Uses OpenCV SFace ONNX model for 128-dimensional L2-normalized face embeddings.
"""

from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np


class FaceEmbedder:
    """
    Local face feature extractor.
    Aligns and normalizes face crops using 5 landmarks, then computes 128-D feature vectors.
    """

    def __init__(self, model_path: Optional[str] = None):
        if model_path is None:
            default_path = Path(__file__).resolve().parent.parent / "models" / "face_recognition_sface_2021dec.onnx"
            model_path = str(default_path)

        self.model_path = model_path
        self.recognizer = None

        if Path(model_path).exists():
            try:
                self.recognizer = cv2.FaceRecognizerSF.create(
                    model=str(model_path),
                    config=""
                )
                print(f"[INFO] FaceEmbedder loaded SFace model from: {model_path}")
            except Exception as e:
                print(f"[WARNING] Failed to load SFace model ({e}). Using normalized pixel embedding fallback.")
                self.recognizer = None
        else:
            print(f"[WARNING] SFace model file not found at {model_path}.")

    def extract_embedding(self, frame: np.ndarray, face_raw: np.ndarray) -> np.ndarray:
        """
        Extracts 128-D L2-normalized embedding vector.
        
        Args:
            frame: Full BGR frame.
            face_raw: Face data row from cv2.FaceDetectorYN (15 elements: [x,y,w,h, landmarks..., conf]).
        """
        if self.recognizer is not None and face_raw is not None:
            # 1. Align and crop face based on 5 landmarks
            aligned_face = self.recognizer.alignCrop(frame, face_raw)
            # 2. Extract 128-D feature vector
            feature = self.recognizer.feature(aligned_face)
            # 3. L2 normalize
            feature = feature.flatten()
            norm = np.linalg.norm(feature)
            if norm > 0:
                feature = feature / norm
            return feature.astype(np.float32)

        # Fallback: Crop and extract standard 128-D flattened color histogram
        x, y, w, h = [int(v) for v in face_raw[:4]] if face_raw is not None else (0, 0, frame.shape[1], frame.shape[0])
        x = max(0, x)
        y = max(0, y)
        w = min(frame.shape[1] - x, w)
        h = min(frame.shape[0] - y, h)
        crop = frame[y:y+h, x:x+w]
        if crop.size == 0:
            return np.zeros((128,), dtype=np.float32)

        resized = cv2.resize(crop, (16, 8)) # 128 elements
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY).flatten().astype(np.float32)
        norm = np.linalg.norm(gray)
        if norm > 0:
            gray = gray / norm
        return gray

    @staticmethod
    def compute_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Computes Cosine Similarity between two L2-normalized face embedding vectors.
        Returns score in range [0.0, 1.0].
        """
        if emb1 is None or emb2 is None or len(emb1) == 0 or len(emb2) == 0:
            return 0.0

        e1 = emb1.flatten().astype(np.float32)
        e2 = emb2.flatten().astype(np.float32)
        
        n1 = np.linalg.norm(e1)
        n2 = np.linalg.norm(e2)
        if n1 == 0 or n2 == 0:
            return 0.0

        cosine = float(np.dot(e1, e2) / (n1 * n2))
        return float(np.clip(cosine, 0.0, 1.0))
