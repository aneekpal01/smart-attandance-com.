# SmartAttend-AI: Technical Architecture & System Engineering

**System Classification**: Edge-AI Offline Biometric Attendance & Institutional Intelligence System  
**Deployment Model**: On-Premise / Edge Node / Zero Cloud API Dependency  
**Version**: 1.0.0 (SIH Production Baseline)  

---

## 🏛️ 1. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 SMARTATTEND-AI CLIENT HUD                              │
│                                                                                        │
│   [Webcam Capture] ──▶ [YuNet Face Detection] ──▶ [5 Landmark Alignment]              │
│                               │                                │                       │
│                               ▼                                ▼                       │
│                    [SFace 128-D Embedding]        [Multi-Signal Liveness]              │
│                               │                   (Micro-motion + Gradient)            │
│                               ▼                                │                       │
│                  [Cosine Similarity Search] ◀──────────────────┘                       │
│                               │                                                        │
│                               ▼                                                        │
│                  [Anti-Proxy Identity Binding] ◀── [QR Token Decoder]                  │
└───────────────────────────────┬────────────────────────────────────────────────────────┘
                                │ (Atomic Verification Payload)
                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               FASTAPI LOCAL BACKEND ENGINE                             │
│                                                                                        │
│  [Session Lifecycle Manager]  [Atomic Security Service]  [Explainable Analytics]       │
│  - Time-window validity       - Token replay protection  - Risk trajectory engine      │
│  - Dynamic Session QR         - Anti-proxy verification  - Fact-grounded insights      │
│                                                                                        │
│                                  │ (WAL SQLite Connection)                             │
│                                  ▼                                                     │
│                ┌───────────────────────────────────┐                                   │
│                │      LOCAL SQLITE DATABASE        │                                   │
│                │  - students (Roll, Dept, QR)      │                                   │
│                │  - face_embeddings (128-D BLOB)   │                                   │
│                │  - sessions (Code, Windows)       │                                   │
│                │  - attendance_records (UNIQUE)    │                                   │
│                │  - attendance_audit_events (Logs) │                                   │
│                │  - used_replay_tokens (Hashes)    │                                   │
│                └───────────────────────────────────┘                                   │
└───────────────────────────────┬────────────────────────────────────────────────────────┘
                                │ (REST API / JSON Payloads)
                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FACULTY DASHBOARD (REACT + VITE)                          │
│                                                                                        │
│  [Active Session Projector]  [Live Attendance Roster]  [AI Analytics & Risk Panel]     │
│  - High-contrast Session QR  - 3s Live polling         - Missable class margins        │
│  - Countdown Timer           - 1-Click CSV export      - Anomaly alert feed            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 2. Computer Vision & Neural Network Specifications

### A. Face Detection: OpenCV YuNet ONNX (`face_detection_yunet_2023mar.onnx`)
- **Input Dimension**: $640 \times 480 \times 3$ BGR
- **Architecture**: Lightweight single-stage feature pyramid detector
- **Outputs**: Bounding box coordinates $[x, y, w, h]$, detection confidence ($0.0 - 1.0$), and 5 facial landmark keypoints:
  1. Right Eye $[x_1, y_1]$
  2. Left Eye $[x_2, y_2]$
  3. Nose Tip $[x_3, y_3]$
  4. Right Mouth Corner $[x_4, y_4]$
  5. Left Mouth Corner $[x_5, y_5]$
- **Inference Speed**: **$9.17\text{ ms}$** on standard CPU ($> 100\text{ FPS}$).

### B. Face Recognition: SFace ONNX (`face_recognition_sface_2021dec.onnx`)
- **Input Dimension**: $112 \times 112 \times 3$ aligned face crop
- **Feature Vector**: 128-Dimensional continuous embedding vector
- **Normalization**: $L_2$ unit hypersphere ($\|v\|_2 = 1.0$)
- **Similarity Metric**: Cosine Distance $\cos(\theta) = \frac{u \cdot v}{\|u\| \|v\|} = u \cdot v$
- **Recognition Threshold**: $\cos(\theta) \ge 0.60$
- **Inference Speed**: **$0.09\text{ ms}$** per face crop.

---

## 🛡️ 3. Security & Anti-Proxy Mechanisms

```text
Classroom Check-In Attempt
          │
          ├─► [1] Dynamic Session Valid? ──(No)──▶ Reject: SESSION_CLOSED / EXPIRED
          │
          ├─► [2] Student QR Valid? ──────(No)──▶ Reject: INVALID_QR
          │
          ├─► [3] Face Detected? ─────────(No)──▶ Reject: NO_FACE
          │
          ├─► [4] Cosine Sim >= 0.60? ────(No)──▶ Reject: FACE_UNKNOWN
          │
          ├─► [5] QR Student == Face? ────(No)──▶ Reject: IDENTITY_MISMATCH (Flag Proxy)
          │
          ├─► [6] Liveness State == LIVE? (No)──▶ Reject: LIVENESS_FAILED (Flag Spoof)
          │
          ├─► [7] Already Attended? ──────(Yes)─▶ Reject: ALREADY_MARKED
          │
          ├─► [8] Token Replay Detected? ─(Yes)─▶ Reject: REPLAY_REJECTED
          │
          └─► [COMMIT ATOMIC TRANSACTION] ───────▶ Log PRESENT/LATE in DB & Audit Trail
```

1. **Cryptographic Identity Binding**: An attendance record is ONLY written if $\text{Student}(\text{QR Token}) \equiv \text{Student}(\text{Recognized Embedding})$. Scanning a classmate's QR code with a different face results in immediate proxy interception (`IDENTITY_MISMATCH`).
2. **Multi-Signal Liveness Analysis**: Combines rolling facial landmark micro-motion across 10 temporal frames, 3D eye-to-nose geometric perspective variation, and Laplacian high-frequency edge gradients to prevent printed paper and phone screen attacks.
3. **Database-Level Unique Constraints**: `UNIQUE(session_id, student_id)` strictly enforced at the SQLite schema level guarantees zero duplicate entries even under concurrent multi-threaded network requests.

---

## 📊 4. AI Analytics & Explainable Intelligence

- **Mathematical Risk Classification**:
  - Distance from institutional target: $\Delta = \text{Threshold} - \text{CurrentAttendance}$
  - Trailing absence streak in last 5 sessions ($\ge 3$ consecutive misses $\implies \text{HIGH RISK}$)
  - Margin of missable classes: $\lfloor \frac{\text{Attended} \times 100}{\text{Threshold}} \rfloor - \text{TotalClasses}$
- **Zero-Hallucination AI Insights Engine**:
  - Synthesizes natural-language feedback strictly derived from SQL aggregation metrics with full grounding metadata.
- **Small-Data Safety**:
  - Automatically activates `INSUFFICIENT_DATA` mode for cohorts with $< 3$ classes, preventing false mathematical claims.

---

## 🔒 5. Privacy & Data Protection Architecture

- **Zero Cloud Footprint**: 100% offline edge execution; no external API calls or telemetry.
- **Zero Raw Image Storage**: No pictures, frames, or face crops are saved on disk or in the database.
- **Biometric Minimization**: Only 128-D mathematical feature vectors are stored locally in SQLite BLOB format.
