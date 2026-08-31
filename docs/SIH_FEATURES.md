# SmartAttend-AI: Key Features & Technical Differentiators (SIH 2026)

---

## 🌟 Top 10 Core Differentiators

### 1. 100% Offline Edge-AI Computing
- Operates entirely on standard college laptops/desktops without requiring cloud API subscriptions, GPU clusters, or active internet connectivity.
- Inference pipeline executes in **$< 10\text{ ms}$** per frame ($> 100\text{ FPS}$ sustained throughput).

### 2. Dual-Factor Identity Binding (Anti-Proxy Architecture)
- Combines opaque dynamic QR tokens with biometric face embeddings.
- Prevents proxy attendance: scanning a classmate's QR while standing in front of the camera triggers an immediate `IDENTITY_MISMATCH` alert.

### 3. Multi-Signal Temporal Liveness & Anti-Spoofing
- Rejects printed photographs and static phone screen photos.
- Analyzes facial landmark micro-motion, 3D eye-to-nose perspective geometry, and high-frequency Laplacian edge gradients.

### 4. Dynamic Classroom Projector QR Codes
- Faculty project dynamic session QR codes with strict temporal validity windows (e.g. 15 min PRESENT, 30 min LATE).
- Automatic expiration blocks post-lecture attendance logging and cross-session injection.

### 5. Replay Attack & Duplicate Token Protection
- Session-specific cryptographic ticket hashes prevent replayed network transactions.
- Database-level `UNIQUE(session_id, student_id)` constraint ensures impossible duplicate entries even during concurrent network race conditions.

### 6. Atomic Attendance Persistence & Transaction Safety
- Multi-step validation pipeline (Session $\to$ QR $\to$ Detection $\to$ Embedding $\to$ Liveness $\to$ Anti-Proxy) committed in a single atomic database transaction.

### 7. Immutable Security & Audit Trail
- Logs every verification success, failure, proxy attempt, and photo spoof with precise timestamps, confidence metrics, and non-accusatory diagnostic reasons.

### 8. Explainable Predictive Attendance-Risk Analysis
- Evaluates student attendance trajectories against academic compliance thresholds (e.g. $75\%$).
- Calculates the exact mathematical margin of classes a student can miss or consecutive classes needed to recover before academic debarment.

### 9. Fact-Grounded AI Insights Engine (Zero Hallucinations)
- Converts complex SQL statistics into concise natural-language faculty summaries. Every insight is strictly grounded in database telemetry.

### 10. Privacy-by-Design & Minimal Biometric Retention
- **Zero raw camera frames or facial photographs stored.**
- Opaque student QR tokens contain zero personally identifiable information (PII).
- REST API payloads strictly exclude biometric vector BLOBs.
