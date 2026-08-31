# SmartAttend-AI: Anti-Proxy, Security & Audit Trail Architecture (Step 8)

Hardened classroom attendance security infrastructure for **SmartAttend-AI**, protecting against proxy attendance, QR transfer/replay, photo spoofs, and brute-force verification abuse.

---

## 🛡️ Threat Model & Mitigations

| Threat Vector | Attack Description | Mitigation Mechanism | Severity Level |
| :--- | :--- | :--- | :--- |
| **Proxy Attendance (QR Transfer)** | Student A sends their QR code to Student B to mark attendance for them. | **Face Identity Binding**: The student's facial embedding must match the exact student registered to the QR. Mismatches trigger `IDENTITY_MISMATCH`. | `HIGH` |
| **Transaction Replay** | An attacker captures and replays a successful verification ticket or network token. | **Replay Protection**: Every transaction token is registered in `used_replay_tokens` atomically. Replayed tokens trigger `REPLAY_REJECTED`. | `HIGH` |
| **Session Bleed / Cross-Session Reuse** | A QR code generated for Morning Session A is presented during Afternoon Session B. | **Session-Token Cryptographic Binding**: Session tokens are validated strictly against the active session ID in SQLite. | `HIGH` |
| **Photo / Screen Spoof** | Presenting printed photos, paper cut-outs, or smartphone screen images. | **Multi-Signal Liveness Detector**: Requires dynamic landmark micro-motion, 3D geometry shifts, and high-frequency texture gradient before granting `LIVE` status. | `HIGH` |
| **Duplicate Attendance** | Student attempts to mark attendance multiple times. | **Idempotent DB Uniqueness**: SQLite `UNIQUE(session_id, student_id)` constraint guarantees single-record write. Repeated attempts return `ALREADY_MARKED`. | `WARNING` |
| **Brute-Force Scans** | Repeated rapid scans of fake or random QR codes. | **Rolling Window Rate Limiter**: 3 consecutive failures within 60s trigger `SUSPICIOUS_ACTIVITY` flags for faculty review. | `HIGH` |

---

## 🔒 Complete Verification Pipeline

```text
                     TEMPORARY SESSION QR
                              │
                              ▼
                     [1] Session Validation
                 (Active? Not Expired? Match?)
                              │
                              ▼
                     [2] Student QR Verification
                  (Token Registered in SQLite?)
                              │
                              ▼
                     [3] Face Recognition (YuNet + SFace)
                  (Face Detected & Enrolled in SQLite?)
                              │
                              ▼
                     [4] Identity Anti-Mismatch Check
              (Does QR Student == Recognized Face Student?)
                              │
                              ▼
                     [5] Liveness Verification
                   (Multi-Signal: Must be LIVE)
                              │
                              ▼
                     [6] Replay & Duplicate Check
             (Fresh Transaction Token? Not Already Marked?)
                              │
                              ▼
                     [7] Atomic SQLite Transaction
              ┌───────────────┴───────────────┐
              ▼                               ▼
      ATTENDANCE RECORDED               AUDIT EVENT LOGGED
    (Status: PRESENT / LATE)         (Event: ATTENDANCE_MARKED)
```

If **any checkpoint fails**:
- Zero attendance records are written to the database.
- An immutable security event is logged to `attendance_audit_events` with the exact failure reason.

---

## 📊 Security Audit Events Schema (`attendance_audit_events`)

```sql
CREATE TABLE attendance_audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    session_id INTEGER NOT NULL,
    student_id INTEGER,
    event_type TEXT NOT NULL,          -- e.g. QR_VERIFIED, IDENTITY_MISMATCH, LIVENESS_FAILED, REPLAY_ATTEMPT, SUSPICIOUS_ACTIVITY
    severity TEXT NOT NULL,            -- INFO | WARNING | HIGH
    result TEXT NOT NULL,              -- SUCCESS | REJECTED | FLAGGED
    similarity_score REAL,
    liveness_score REAL,
    reason TEXT NOT NULL,
    metadata_json TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES sessions(id),
    FOREIGN KEY(student_id) REFERENCES students(id)
);
```

---

## 🔐 Strict Privacy & Local Compliance Guarantee
- **Zero Cloud Calls**: 100% offline, on-premise execution.
- **No Biometric Data in Audit Logs**: Audit tables contain event IDs, similarity metrics, timestamps, and reason descriptions—strictly zero raw camera frames, zero face crops, and zero biometric embedding vectors.
- **Neutral Terminology**: Rejections are recorded factually (e.g. `Verification mismatch`, `Inconclusive liveness`) without making defamatory assumptions.

---

## ⚠️ Transparent System Limitations
1. **Identical Twin Verification**: Pure visual cosine similarity at $0.60$ threshold may have overlap on identical twins.
2. **Deepfake Injection at OS Driver Level**: Virtual webcam software feeding synthetic video streams directly into the OS capture pipeline would bypass camera physics; dedicated hardware anti-spoofing or watermarking is required for high-security proctoring environments.

---

## 🧪 Automated Test Suite Run Instructions

```powershell
cd "C:\Users\aneek pal\.gemini\antigravity\scratch\SmartAttend-AI"
.\venv\Scripts\activate

python -m ai.security.test_step8_security
```
