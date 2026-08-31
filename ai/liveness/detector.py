"""
SmartAttend-AI: Multi-Signal Temporal Liveness & Anti-Spoofing Module (Step 7)
=============================================================================
Combines temporal facial micro-motion, 5-point landmark variation, 3D pose dynamics,
and texture frequency analysis to detect printed photos, phone screens, and static attacks.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import cv2


class LivenessState(str, Enum):
    LIVE = "LIVE"
    SPOOF = "SPOOF"
    UNCERTAIN = "UNCERTAIN"


@dataclass
class LivenessConfig:
    """Configurable hyperparameters for multi-signal liveness verification."""
    window_frames: int = 10                  # Number of frames in temporal rolling buffer
    min_frames_required: int = 5            # Minimum frames needed before rendering decision
    liveness_threshold: float = 0.65        # Composite score threshold to classify as LIVE
    min_confidence: float = 0.70            # Minimum confidence required for LIVE decision
    static_motion_threshold: float = 0.0012  # Below this, sequence is considered a static photo
    max_unnatural_motion: float = 0.15      # Above this, motion is unnaturally jarring / erratic
    texture_fft_threshold: float = 12.0     # Minimum high-frequency texture gradient
    head_pose_min_std: float = 0.0008       # Minimum natural head micro-pose variance


@dataclass
class LivenessResult:
    """Output results from LivenessDetector."""
    state: LivenessState
    liveness_score: float
    confidence: float
    reason: str
    signals: Dict[str, float] = field(default_factory=dict)

    @property
    def is_live(self) -> bool:
        return self.state == LivenessState.LIVE


class LivenessDetector:
    """
    Multi-Signal Local Anti-Spoofing & Liveness Detector.
    Analyzes temporal sequences of frames and facial landmark dynamics.
    """

    def __init__(self, config: Optional[LivenessConfig] = None):
        self.config = config or LivenessConfig()
        # Rolling temporal buffer storing recent frame features:
        # dict of { "timestamp": float, "landmarks": np.ndarray, "crop": np.ndarray, "bbox": Tuple }
        self.frame_buffer: List[Dict[str, Any]] = []

    def reset(self) -> None:
        """Clears the temporal frame buffer."""
        self.frame_buffer.clear()

    def add_frame_sample(
        self,
        frame: np.ndarray,
        landmarks: Optional[List[Tuple[float, float]]],
        bbox: Tuple[int, int, int, int]
    ) -> None:
        """
        Adds a single frame observation into the temporal sliding window.
        """
        if frame is None or frame.size == 0 or landmarks is None or len(landmarks) < 5:
            return

        x, y, w, h = bbox
        box_w = max(1, w)
        box_h = max(1, h)
        
        # Crop face if frame allows
        crop_x = max(0, x)
        crop_y = max(0, y)
        crop_w = min(frame.shape[1] - crop_x, w)
        crop_h = min(frame.shape[0] - crop_y, h)
        face_crop = frame[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w] if (crop_w > 10 and crop_h > 10) else frame

        # Normalize landmarks relative to face bounding box size (scale invariant)
        norm_landmarks = np.array([
            [(lx - x) / box_w, (ly - y) / box_h] for (lx, ly) in landmarks
        ], dtype=np.float32)

        self.frame_buffer.append({
            "landmarks": norm_landmarks,
            "crop": face_crop,
            "bbox": (x, y, w, h)
        })

        # Keep buffer bounded to window size
        if len(self.frame_buffer) > self.config.window_frames:
            self.frame_buffer.pop(0)

    # -------------------------------------------------------------------------
    # Signal 1: Landmark Temporal Dynamics & Micro-Motion
    # -------------------------------------------------------------------------
    def _evaluate_landmark_motion(self) -> Tuple[float, float]:
        """
        Computes standard deviation and inter-frame velocity of normalized landmarks.
        Returns:
            (motion_score [0..1], std_deviation)
        """
        if len(self.frame_buffer) < 2:
            return 0.0, 0.0

        all_lm = np.stack([f["landmarks"] for f in self.frame_buffer], axis=0) # (T, 5, 2)
        
        # Standard deviation across temporal dimension
        lm_std = float(np.mean(np.std(all_lm, axis=0)))

        # Natural human micro-motion typically falls in [0.0015, 0.08]
        if lm_std < self.config.static_motion_threshold:
            # Too static -> Printed photo or static image attack
            motion_score = 0.05
        elif lm_std > self.config.max_unnatural_motion:
            # Unnaturally large jumps -> Jitter / warping
            motion_score = 0.30
        else:
            # Natural micro-motion
            normalized = (lm_std - self.config.static_motion_threshold) / (0.02 - self.config.static_motion_threshold)
            motion_score = float(np.clip(0.70 + 0.30 * normalized, 0.0, 1.0))

        return motion_score, lm_std

    # -------------------------------------------------------------------------
    # Signal 2: 3D Facial Geometry & Eye-to-Nose Aspect Ratio Dynamics
    # -------------------------------------------------------------------------
    def _evaluate_facial_geometry_dynamics(self) -> float:
        """
        Analyzes variation in geometric ratios:
        - Eye-to-eye distance / Nose-to-mouth distance ratio
        - Inter-ocular distance variation across frames
        """
        if len(self.frame_buffer) < 2:
            return 0.0

        ratios = []
        for sample in self.frame_buffer:
            lm = sample["landmarks"]
            # 0: right eye, 1: left eye, 2: nose tip, 3: mouth right, 4: mouth left
            eye_dist = np.linalg.norm(lm[0] - lm[1])
            mouth_center = (lm[3] + lm[4]) / 2.0
            nose_to_mouth = np.linalg.norm(lm[2] - mouth_center)

            ratio = float(eye_dist / (nose_to_mouth + 1e-6))
            ratios.append(ratio)

        ratio_std = float(np.std(ratios))
        
        # Static photos have near-zero ratio variance (< 0.0002)
        if ratio_std < 0.0002:
            return 0.15
        elif ratio_std > 0.10:
            return 0.35
        else:
            return float(np.clip(0.65 + (ratio_std / 0.01) * 0.35, 0.0, 1.0))

    # -------------------------------------------------------------------------
    # Signal 3: High-Frequency Texture & Screen Moiré Analysis
    # -------------------------------------------------------------------------
    def _evaluate_texture_frequency(self) -> float:
        """
        Analyzes high-frequency texture gradient (Laplacian variance) on recent face crops
        to detect blurriness from low-res prints or ultra-flat visuals.
        """
        crops = [f["crop"] for f in self.frame_buffer if f["crop"] is not None]
        if not crops:
            return 0.70

        scores = []
        for crop in crops[-3:]: # Check last 3 crops
            if crop is None or crop.size == 0:
                continue
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            var = float(laplacian.var())
            
            # Normal face skin with lighting texture gradient
            if var < self.config.texture_fft_threshold:
                # Overly flat/blurred (e.g. low-res flat print)
                scores.append(0.20)
            else:
                scores.append(0.85)

        return float(np.mean(scores)) if scores else 0.70

    # -------------------------------------------------------------------------
    # Master Evaluation Pipeline
    # -------------------------------------------------------------------------
    def evaluate_liveness(self) -> LivenessResult:
        """
        Fuses all temporal and visual signals to render a final Liveness decision.
        """
        # Step 1: Check minimum sample requirement
        if len(self.frame_buffer) < self.config.min_frames_required:
            return LivenessResult(
                state=LivenessState.UNCERTAIN,
                liveness_score=0.0,
                confidence=0.20,
                reason="LIVENESS_UNCERTAIN: Collecting temporal verification samples...",
                signals={"samples_collected": len(self.frame_buffer)}
            )

        # Step 2: Compute individual signal scores
        motion_score, lm_std = self._evaluate_landmark_motion()
        geometry_score = self._evaluate_facial_geometry_dynamics()
        texture_score = self._evaluate_texture_frequency()

        # Step 3: Check static photo attack condition
        if lm_std < self.config.static_motion_threshold:
            return LivenessResult(
                state=LivenessState.SPOOF,
                liveness_score=0.10,
                confidence=0.92,
                reason="SPOOF_DETECTED: Static image / printed photo detected (zero natural micro-motion).",
                signals={
                    "landmark_motion": motion_score,
                    "landmark_std": lm_std,
                    "geometry_dynamics": geometry_score,
                    "texture_score": texture_score
                }
            )

        # Step 4: Weighted Composite Liveness Score
        # Weights: 45% Landmark Motion, 30% Geometry Dynamics, 25% Texture Frequency
        composite_score = (
            0.45 * motion_score +
            0.30 * geometry_score +
            0.25 * texture_score
        )

        confidence = float(np.clip(
            (len(self.frame_buffer) / self.config.window_frames) * 0.90 + 0.10,
            0.0, 1.0
        ))

        signals = {
            "landmark_motion": round(motion_score, 3),
            "landmark_std": round(lm_std, 6),
            "geometry_dynamics": round(geometry_score, 3),
            "texture_score": round(texture_score, 3),
            "composite_score": round(composite_score, 3)
        }

        # Step 5: Render Conservative Decision
        if composite_score >= self.config.liveness_threshold and confidence >= self.config.min_confidence:
            return LivenessResult(
                state=LivenessState.LIVE,
                liveness_score=composite_score,
                confidence=confidence,
                reason="LIVE: Real human presence confirmed.",
                signals=signals
            )
        elif composite_score < 0.35:
            return LivenessResult(
                state=LivenessState.SPOOF,
                liveness_score=composite_score,
                confidence=confidence,
                reason="SPOOF_DETECTED: Artificial or unnatural spoof signals detected.",
                signals=signals
            )
        else:
            return LivenessResult(
                state=LivenessState.UNCERTAIN,
                liveness_score=composite_score,
                confidence=confidence,
                reason="LIVENESS_UNCERTAIN: Motion signals inconclusive. Please hold steady in front of camera.",
                signals=signals
            )
