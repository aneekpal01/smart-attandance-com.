# SmartAttend-AI: Liveness & Anti-Spoofing Verification (Step 7)

Local multi-signal temporal anti-spoofing and real-person verification engine for **SmartAttend-AI**.

---

## 🎯 Architecture Overview

```text
                     LIVE WEBCAM FRAME SEQUENCE
                                 │
                                 ▼
                     YuNet 5-Point Face Detection
              (Bounding Box + Eye, Nose, Mouth Landmarks)
                                 │
                                 ▼
                   Temporal Sliding Window Buffer
                     (Configurable: 5-15 frames)
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
 [Signal 1]               [Signal 2]               [Signal 3]
Landmark Micro-Motion    Facial Geometry Dynamics  Texture High-Pass
(Std & Velocity)         (Eye/Nose/Mouth Ratios)   (Laplacian Variance)
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                                 ▼
                  Composite Liveness Fusion Score
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
  Score >= 0.65            Score < 0.35              Inconclusive
  Conf >= 0.70           Static Attack / Fake       Frames < Min
        │                        │                        │
        ▼                        ▼                        ▼
  STATUS: LIVE             STATUS: SPOOF          STATUS: UNCERTAIN
  (Proceed to Attendance) (Attendance REJECTED)  (Prompt to Retry)
```

---

## 🔍 Evaluated Anti-Spoofing Signals

1. **Landmark Micro-Motion Dynamics**:
   - Analyzes sub-pixel standard deviation and motion vectors across temporal frame sequences.
   - **Static Printed Photos / Still Pictures** exhibit zero natural coordinate jitter ($\Delta \approx 0$) and are immediately flagged as `SPOOF`.

2. **3D Facial Geometry & Eye-to-Nose Aspect Ratio Dynamics**:
   - Measures continuous ratio between inter-ocular distance and nose-to-mouth center distance.
   - Natural human head tremor and micro-expressions cause subtle dynamic ratio shifts.

3. **High-Frequency Texture Gradient (Laplacian Variance)**:
   - Evaluates texture gradient variance to distinguish real skin under natural lighting from ultra-flat paper prints or low-res captures.

---

## 🛡️ Supported Spoof Types & Known Limitations

### ✅ Supported Spoof Detections:
- **Printed Photographs / Paper Masks**: Rejected due to zero micro-motion and flat geometric ratios.
- **Static Images on Phone/Tablet Screens**: Rejected due to static landmark coordinate vectors.
- **Empty / Cut-out Frames / Blurred Captures**: Rejected due to texture gradient and landmark checks.

### ⚠️ Known Limitations (Honest Disclosure):
- **High-Definition Replay Video Attacks**: A video of a person blinking or moving on a high-resolution display held directly in front of the lens may mimic basic micro-motion.
- *Extensibility*: The module interface (`LivenessDetector`) is designed to easily plug in lightweight ONNX Deep Learning anti-spoofing networks (e.g. MiniFASNet / CDCN) in production deployments.

---

## ⚙️ Configurable Parameters (`LivenessConfig`)

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `window_frames` | `10` | Size of the temporal sliding window buffer |
| `min_frames_required` | `5` | Minimum frames before rendering a decision |
| `liveness_threshold` | `0.65` | Minimum composite score required for `LIVE` |
| `min_confidence` | `0.70` | Minimum confidence threshold |
| `static_motion_threshold`| `0.0012` | Motion threshold below which photo attack is triggered |

---

## 🚀 How to Run

### 1. Run Live Liveness & Anti-Spoofing Demo (Camera GUI)
```powershell
cd "C:\Users\aneek pal\.gemini\antigravity\scratch\SmartAttend-AI"
.\venv\Scripts\activate

python -m ai.liveness.live_liveness_verifier
```

### 2. Run Automated Test Suite (10 Tests)
```powershell
python -m ai.liveness.test_step7_liveness
```

---

## 🔗 Integration with Attendance Pipeline

```text
Temporary Session QR ➔ QR Verification ➔ Face Recognition ➔ Identity Match ➔ Liveness (LIVE) ➔ Attendance Marked (PRESENT/LATE)
```
If Liveness is `SPOOF` or `UNCERTAIN`, attendance is **strictly rejected** and zero records are written to the database.
