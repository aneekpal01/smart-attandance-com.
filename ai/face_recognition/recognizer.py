"""
SmartAttend-AI: Face Recognition Service (Step 5)
Handles real-time multi-face identification using SFace embeddings,
vectorized cosine similarity, configurable thresholding, and temporal smoothing.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
import time
import numpy as np
import cv2

from database.db_manager import DatabaseManager
from ai.face_recognition.live_face_detector import OpenCVFaceDetector, FaceBox
from ai.face_recognition.embedder import FaceEmbedder


# Central Default Configuration
DEFAULT_RECOGNITION_THRESHOLD = 0.60
DEFAULT_DETECTION_CONFIDENCE = 0.50


@dataclass
class RecognitionResult:
    """Represents recognition output for a single face."""
    box: FaceBox
    student_db_id: Optional[int]
    student_id: Optional[str]
    student_name: str
    department: Optional[str]
    year: Optional[int]
    section: Optional[str]
    similarity: float
    is_recognized: bool
    status: str  # "RECOGNIZED" or "NOT RECOGNIZED"

    @property
    def label(self) -> str:
        """Returns standard display label."""
        if self.is_recognized:
            return f"{self.student_name} ({self.student_id})"
        return "UNKNOWN"


class TemporalSmoother:
    """
    Lightweight temporal filter to prevent rapid identity flickering across consecutive frames.
    Maintains a rolling window of match predictions for tracked face locations.
    """

    def __init__(self, history_len: int = 5, iou_threshold: float = 0.4):
        self.history_len = history_len
        self.iou_threshold = iou_threshold
        # Stores track history: list of { "box": FaceBox, "history": [ (student_id, similarity) ], "last_seen": timestamp }
        self.tracks: List[Dict[str, Any]] = []

    @staticmethod
    def compute_iou(box1: FaceBox, box2: FaceBox) -> float:
        """Calculates Intersection over Union between two face boxes."""
        x1_a, y1_a, x2_a, y2_a = box1.xyxy
        x1_b, y1_b, x2_b, y2_b = box2.xyxy

        x_left = max(x1_a, x1_b)
        y_top = max(y1_a, y1_b)
        x_right = min(x2_a, x2_b)
        y_bottom = min(y2_a, y2_b)

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        area_a = (x2_a - x1_a) * (y2_a - y1_a)
        area_b = (x2_b - x1_b) * (y2_b - y1_b)
        union_area = float(area_a + area_b - intersection_area)

        return (intersection_area / union_area) if union_area > 0 else 0.0

    def smooth(self, results: List[RecognitionResult]) -> List[RecognitionResult]:
        """Applies temporal smoothing across current frame results."""
        current_time = time.time()
        smoothed_results: List[RecognitionResult] = []

        # Remove stale tracks older than 1.5 seconds
        self.tracks = [t for t in self.tracks if current_time - t["last_seen"] < 1.5]

        for res in results:
            best_iou = 0.0
            matched_track = None

            for track in self.tracks:
                iou = self.compute_iou(res.box, track["box"])
                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    matched_track = track

            if matched_track is not None:
                # Update existing track
                matched_track["box"] = res.box
                matched_track["last_seen"] = current_time
                matched_track["history"].append((res.student_id, res.similarity, res.student_name, res.is_recognized))
                if len(matched_track["history"]) > self.history_len:
                    matched_track["history"].pop(0)

                # Compute majority vote / smoothed similarity
                rec_entries = [h for h in matched_track["history"] if h[3]]  # is_recognized
                if len(rec_entries) >= (len(matched_track["history"]) // 2 + 1):
                    # Average similarity
                    avg_sim = float(np.mean([h[1] for h in rec_entries]))
                    res.similarity = max(res.similarity, avg_sim)
                    res.is_recognized = True
                    res.status = "RECOGNIZED"
                else:
                    if not res.is_recognized:
                        res.student_name = "UNKNOWN"
                        res.status = "NOT RECOGNIZED"
            else:
                # Register new track
                self.tracks.append({
                    "box": res.box,
                    "history": [(res.student_id, res.similarity, res.student_name, res.is_recognized)],
                    "last_seen": current_time
                })

            smoothed_results.append(res)

        return smoothed_results


class FaceRecognizerService:
    """
    Dedicated Face Recognition Service.
    Loads enrolled student embeddings from SQLite into memory and performs
    high-speed vectorized cosine distance matching.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        recognition_threshold: float = DEFAULT_RECOGNITION_THRESHOLD,
        confidence_threshold: float = DEFAULT_DETECTION_CONFIDENCE,
        enable_smoothing: bool = True
    ):
        self.db = db_manager or DatabaseManager()
        self.recognition_threshold = recognition_threshold
        self.confidence_threshold = confidence_threshold
        self.enable_smoothing = enable_smoothing

        self.detector = OpenCVFaceDetector(confidence_threshold=self.confidence_threshold)
        self.embedder = FaceEmbedder()
        self.smoother = TemporalSmoother() if enable_smoothing else None

        # Cached enrolled embeddings in memory for fast matrix multiplication
        self.enrolled_students: List[Dict[str, Any]] = []
        self.embedding_matrix: Optional[np.ndarray] = None  # Shape (N, 128)
        self.reload_enrolled_cache()

    def reload_enrolled_cache(self) -> int:
        """
        Loads or refreshes enrolled student profiles and their 128-D embeddings from SQLite.
        Returns the total number of loaded enrolled students.
        """
        self.enrolled_students = self.db.load_all_enrolled_students()
        if self.enrolled_students:
            # Build 2D matrix (N, 128) of normalized vectors
            embeddings = [s["embedding"] for s in self.enrolled_students]
            self.embedding_matrix = np.vstack(embeddings).astype(np.float32)
            # Ensure all cached rows are strictly L2 normalized
            norms = np.linalg.norm(self.embedding_matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.embedding_matrix = self.embedding_matrix / norms
            print(f"[INFO] FaceRecognizerService loaded {len(self.enrolled_students)} enrolled students into memory cache.")
        else:
            self.embedding_matrix = None
            print("[INFO] FaceRecognizerService: No enrolled students found in database.")
        return len(self.enrolled_students)

    def match_embedding(self, query_embedding: np.ndarray) -> Tuple[Optional[Dict[str, Any]], float, bool]:
        """
        Compares a 128-D face embedding vector against all enrolled students using
        vectorized Cosine Similarity.
        
        Returns:
            (matched_student_dict_or_None, similarity_score, is_recognized_bool)
        """
        if query_embedding is None or self.embedding_matrix is None or len(self.enrolled_students) == 0:
            return None, 0.0, False

        # Ensure query is 1D and normalized
        q = query_embedding.flatten().astype(np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm > 0:
            q = q / q_norm

        # Vectorized dot product (Cosine Similarity because both are unit vectors)
        # Shape: (N, 128) @ (128,) -> (N,)
        similarities = np.dot(self.embedding_matrix, q)
        
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])

        # SFace cosine similarity ranges roughly between -1.0 and 1.0; 
        # Standard positive range normalization:
        best_score_clamped = max(0.0, min(1.0, best_score))

        if best_score_clamped >= self.recognition_threshold:
            return self.enrolled_students[best_idx], best_score_clamped, True
        else:
            return None, best_score_clamped, False

    def recognize_frame(self, frame: np.ndarray) -> Tuple[List[RecognitionResult], float]:
        """
        Performs full end-to-end detection and recognition on a single camera frame.
        
        Returns:
            (list_of_recognition_results, latency_ms)
        """
        if frame is None or frame.size == 0:
            return [], 0.0

        start_time = time.perf_counter()

        # 1. Detect all faces in frame
        detected_faces = self.detector.detect_faces(frame)
        results: List[RecognitionResult] = []

        # 2. Process each detected face
        for face in detected_faces:
            face_raw = np.array([face.x, face.y, face.w, face.h, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, face.confidence], dtype=np.float32)
            
            # Extract 128-D SFace embedding
            emb = self.embedder.extract_embedding(frame, face_raw)
            
            # Match against database
            matched_student, similarity, is_recognized = self.match_embedding(emb)

            if is_recognized and matched_student:
                res = RecognitionResult(
                    box=face,
                    student_db_id=matched_student["id"],
                    student_id=matched_student["student_id"],
                    student_name=matched_student["full_name"],
                    department=matched_student["department"],
                    year=matched_student["year"],
                    section=matched_student["section"],
                    similarity=similarity,
                    is_recognized=True,
                    status="RECOGNIZED"
                )
            else:
                res = RecognitionResult(
                    box=face,
                    student_db_id=None,
                    student_id=None,
                    student_name="UNKNOWN",
                    department=None,
                    year=None,
                    section=None,
                    similarity=similarity,
                    is_recognized=False,
                    status="NOT RECOGNIZED"
                )
            results.append(res)

        # 3. Apply temporal smoothing
        if self.enable_smoothing and self.smoother:
            results = self.smoother.smooth(results)

        latency_ms = (time.perf_counter() - start_time) * 1000
        return results, latency_ms
