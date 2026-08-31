# SmartAttend-AI: Biometric Data Protection & Privacy Audit Report

**Document Version**: 1.0.0  
**Compliance Standard**: Offline Edge Privacy & Minimal Biometric Retention  
**System**: SmartAttend-AI  

---

## 🔒 1. Executive Summary

SmartAttend-AI is engineered with a **Privacy-by-Design** and **Local-First** architecture. The system executes all artificial intelligence inferences (face detection, face alignment, feature extraction, cosine similarity vector search, and multi-signal temporal liveness verification) completely offline on local compute nodes. **Zero biometric vectors, raw camera feeds, or student identity records are transmitted across the public Internet or uploaded to external cloud APIs.**

---

## 📋 2. Biometric Data Inventory

| Data Element | Format | Stored? | Storage Location | Retention Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Raw Camera Frames** | BGR NumPy Array | ❌ **NEVER** | Transient RAM Only | Processed in-memory for detection/liveness and discarded immediately. |
| **Face Crop Images** | JPEG / PNG / BLOB | ❌ **NEVER** | None | Not persisted to disk, database, or log files. |
| **Face Embedding Vectors** | 128-D Float32 Array | ✅ **YES** | SQLite `face_embeddings` table (`BLOB`) | Required for local vector cosine similarity matching during classroom check-in. |
| **Facial Landmarks** | 5 Point Coordinates $(x, y)$ | ❌ **NEVER** | Transient Rolling Buffer | Used for in-memory liveness micro-motion analysis across 10 frames, then cleared. |
| **Student QR Tokens** | UUID Token (`SA-STU-...`) | ✅ **YES** | SQLite `students` table (`TEXT`) | Random opaque identifier mapped to student record in local DB. |
| **Security Audit Logs** | JSON Metadata | ✅ **YES** | SQLite `attendance_audit_events` | Stores event type, timestamps, confidence scores, and status. Excludes raw vectors. |

---

## 🛡️ 3. What is NOT Stored or Exposed

1. **Zero Raw Facial Images**: The local SQLite database stores strictly zero facial image files, base64 strings, or raw picture files.
2. **Zero Sensitive PII in QR Tokens**: Student identity QR tokens contain only random 16-character hexadecimal strings (`SA-STU-XXXXXXXXXX`). A third party scanning a student's QR code cannot obtain student names, roll numbers, departments, or emails without authenticated database access.
3. **Zero Biometrics in Frontend Responses**: All REST API endpoints (`/api/dashboard`, `/api/sessions`, `/api/attendance`, `/api/students`, `/api/security`, `/api/audit`, `/api/analytics`) have been audited to ensure zero `embedding_bytes` or raw image structures are returned to the client browser.
4. **Zero Biometrics in Audit Logs**: The security audit trail logs mathematical similarity scores ($0.0 - 1.0$) and liveness states, but never stores the raw embedding vectors or face crops.

---

## 💾 4. Local Processing & Edge Security

- **100% Offline Capability**: OpenCV DNN YuNet and SFace ONNX models run directly on local CPU/GPU hardware. No network connectivity is required for face detection, student recognition, liveness verification, or attendance logging.
- **SQL Data Isolation**: The local SQLite database (`smartattend.db`) is stored inside the local application workspace and utilizes native file system access controls.

---

## ⚠️ 5. Known Privacy & Operational Considerations

1. **Local Physical Security**: Since embeddings and attendance logs reside in a local SQLite file, the host machine running the SmartAttend-AI server should have full disk encryption (e.g. BitLocker/LUKS) and restricted OS-level access permissions.
2. **Embedding Invertibility**: SFace generates 128-dimensional mathematical feature representations. While mathematical embeddings cannot be directly converted into high-resolution human photographs, they represent biometric templates and must be safeguarded with standard database access restrictions.
3. **Single-Tenant Deployment**: SmartAttend-AI is designed for on-premise college deployments. In a multi-department multi-server environment, encrypted network transport (TLS/HTTPS) is recommended for client-server communication.
