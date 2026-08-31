# SmartAttend-AI: Face Recognition & Enrollment Module

Comprehensive local face detection, student enrollment, and real-time live recognition for **SmartAttend-AI**.

---

## 🎯 Architecture Overview

```text
               LIVE WEBCAM FRAME (640x480)
                           │
                           ▼
          [Step 3] Face Detection (YuNet ONNX)
                           │  (Bounding Box + 5 Landmarks)
                           ▼
          [Step 4] Face Alignment & Feature Crop
                           │  (112x112 Normalized Crop)
                           ▼
          [Step 5] SFace Embedding Extraction
                           │  (128-D L2-Normalized Feature Vector)
                           ▼
             Vectorized Cosine Similarity
        (Matrix Dot Product vs Enrolled SQLite DB)
                           │
             ┌─────────────┴─────────────┐
             │                           │
   Similarity >= Threshold     Similarity < Threshold
             │                           │
             ▼                           ▼
   STATUS: RECOGNIZED          STATUS: NOT RECOGNIZED
   Student Name & Roll No      Label: "UNKNOWN"
```

---

## 🧠 Technical Specifications

### 1. Vector Similarity Formula
Cosine similarity between normalized query vector $\vec{q}$ and enrolled vector $\vec{e}_i$:
$$\text{Similarity}(\vec{q}, \vec{e}_i) = \frac{\vec{q} \cdot \vec{e}_i}{\|\vec{q}\|_2 \|\vec{e}_i\|_2} = \vec{q} \cdot \vec{e}_i$$
Computed across all $N$ enrolled students simultaneously via batch matrix multiplication:
$$\mathbf{S} = \mathbf{E} \cdot \vec{q} \quad \text{where } \mathbf{E} \in \mathbb{R}^{N \times 128}$$

### 2. Configurable Recognition Threshold
- **Default Value**: `0.60`
- **Configurable**: Modify `DEFAULT_RECOGNITION_THRESHOLD` in `ai/face_recognition/recognizer.py` or pass `recognition_threshold=0.65` in `LiveFaceRecognizerApp`.
- Match rule:
  - If $\max(\mathbf{S}) \ge \text{Threshold} \implies \text{RECOGNIZED}$
  - If $\max(\mathbf{S}) < \text{Threshold} \implies \text{UNKNOWN}$

### 3. Temporal Smoothing
Maintains a rolling history across recent frames to eliminate rapid label flickering and ensure stable bounding box tags.

---

## 🚀 How to Run

### Step A: Register & Enroll a Student
```powershell
cd "C:\Users\aneek pal\.gemini\antigravity\scratch\SmartAttend-AI"
.\venv\Scripts\activate

# 1. Register student in SQLite and generate unique token QR image:
python database/register_student_cli.py

# 2. Open camera to scan QR & enroll 5 face angles into SQLite:
python -m ai.face_recognition.interactive_enrollment
```

### Step B: Launch Live Face Recognition Demo (Step 5)
```powershell
python -m ai.face_recognition.live_face_recognizer
```

---

## 🧪 Run Automated Verification Test Suites

### Step 5: Face Recognition Tests
```powershell
python -m ai.face_recognition.test_step5_recognition
```

### Step 4: Registration & QR Verification Tests
```powershell
python -m ai.face_recognition.test_step4_registration
```

### Step 3: Face Detection Tests
```powershell
python -m ai.face_recognition.test_detector
```

---

## 🎮 Live Camera HUD Controls
- **`ESC` Key**: Safely close camera stream.
- **`R` Key**: Reload database cache in memory (picks up newly enrolled students without restarting).
