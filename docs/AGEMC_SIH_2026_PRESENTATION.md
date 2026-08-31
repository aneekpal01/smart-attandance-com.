# SmartAttend-AI — Smart India Hackathon (SIH) 2026
## Official Presentation & Evaluation Dossier
**Institution**: Alipurduar Government Engineering and Management College (AGEMC)  
**Event**: Internal Hackathon for SIH 2026  
**Problem Statement**: **Problem Statement A : Smart Classroom Attendance System**  
**Beneficiaries**: College Administration, Faculty Members, Students  

---

## 👥 1. SIH Team Formation Template (Compliant with Official Guidelines)

| Role | Member Name | Branch / Department | Year | Gender |
| :--- | :--- | :--- | :---: | :---: |
| **Team Leader** | *[Insert Your Name]* | Computer Science & Engineering | 3rd / 4th | Male / Female |
| **Team Member 2** | *[Insert Female Member Name]* | Electronics & Comm. / CSE | 3rd / 4th | **Female** *(Mandatory)* |
| **Team Member 3** | *[Insert Member Name]* | Computer Science & Engineering | 2nd / 3rd | Male / Female |
| **Team Member 4** | *[Insert Member Name]* | Electrical Engineering / CSE | 2nd / 3rd | Male / Female |
| **Team Member 5** | *[Insert Member Name]* | Mechanical / CSE | 2nd / 3rd | Male / Female |
| **Team Member 6** | *[Insert Member Name]* | Civil / CSE | 2nd / 3rd | Male / Female |

*Note: All 6 team members belong to Alipurduar Government Engineering and Management College (AGEMC).*

---

## 📑 2. Official SIH 10-Slide Presentation Pitch Deck

```text
SLIDE 1: Title & Team Overview
SLIDE 2: Problem Statement & Classroom Challenges at AGEMC
SLIDE 3: Proposed Solution — SmartAttend-AI Architecture
SLIDE 4: Working Prototype & Step-by-Step Workflow
SLIDE 5: AI Computer Vision & Multi-Signal Anti-Spoofing Pipeline
SLIDE 6: Dual-Factor Anti-Proxy & Security Hardening
SLIDE 7: Live Faculty Dashboard & Institutional Analytics
SLIDE 8: Privacy-by-Design & 100% Offline Edge Computing
SLIDE 9: Direct Impact on College Administration, Faculty & Students
SLIDE 10: Live Demonstration, Feasibility & Future Scope
```

---

### **SLIDE 1: Title & Overview**
- **Project Title**: **SmartAttend-AI** — Local Edge-AI Classroom Attendance, Anti-Proxy Verification & Institutional Intelligence Platform
- **Category**: Software / AI & Computer Vision / Education Technology
- **Theme**: Smart Education & Smart Classroom Systems
- **Organization**: Alipurduar Government Engineering and Management College (AGEMC)

---

### **SLIDE 2: Problem Understanding & Classroom Realities**
- **Official SIH Problem Statement A**:
  > *"Manual attendance in large colleges consumes classroom time and is prone to proxy attendance, reducing effective teaching hours."*
- **Ground Realities in Engineering Colleges**:
  1. **Lost Instructional Time**: Calling 60+ roll numbers takes $10 - 15\text{ minutes}$ of a 50-minute lecture ($\sim 25\%$ lost teaching time).
  2. **Proxy Attendance Abuse**: Static QR codes, paper roll-calls, and RFID cards are easily handed over to friends.
  3. **Cloud Latency & Privacy Risks**: Commercial cloud facial recognition systems fail on poor campus internet and expose sensitive student biometric photos to third-party cloud servers.

---

### **SLIDE 3: Proposed Solution — SmartAttend-AI Architecture**
- **Core Concept**: An entirely **local, offline-first** edge AI system combining:
  - **Dynamic Classroom Projector QRs** (Time-windowed validity: 15m Present, 30m Late).
  - **Opaque Student Identity Tokens** (Zero PII stored in QR).
  - **Edge-AI Face Recognition** (OpenCV YuNet + SFace ONNX executing in $< 10\text{ ms}$ on CPU).
  - **Multi-Signal Temporal Anti-Spoofing** (Blocks printed photos and phone screen replays).
  - **Dual-Factor Identity Binding** (Student QR owner must match recognized face).
  - **AI Attendance-Risk Analytics** (Predicts students at risk of falling below $75\%$ requirement).

---

### **SLIDE 4: Working Prototype & 13-Stage Workflow**

```text
Student Scans Dynamic Projector QR ──▶ Local Camera HUD Opens
                │
                ▼
1. Decodes Opaque Token (SA-STU-...) ──▶ Identifies Student Record
                │
                ▼
2. YuNet Real-Time Face Detection ────▶ Locates Bounding Box & 5 Landmarks
                │
                ▼
3. SFace 128-D Embedding Extraction ──▶ Computes Cosine Vector Similarity
                │
                ▼
4. Anti-Proxy Binding ────────────────▶ Verifies (QR Student == Recognized Face)
                │
                ▼
5. Multi-Signal Liveness Analysis ────▶ Verifies Real Person (Rejects Photo Spoofs)
                │
                ▼
6. Atomic SQLite Transaction ─────────▶ Marks PRESENT / LATE in DB & Audit Trail
                │
                ▼
7. Real-Time Dashboard Sync ──────────▶ Live Roster Update & CSV Export
```

---

### **SLIDE 5: AI Computer Vision & Anti-Spoofing Pipeline**
- **Face Detection**: OpenCV **YuNet ONNX** ($640 \times 480$ input, $9.17\text{ ms}$ inference on standard CPU, $> 100\text{ FPS}$).
- **Face Recognition**: **SFace ONNX** ($112 \times 112$ crop, 128-D normalized embedding vector, Cosine distance matching against local SQLite DB in $0.09\text{ ms}$).
- **Multi-Signal Liveness Detection**:
  1. *Signal 1*: Facial landmark micro-motion dynamics across rolling 10-frame buffer.
  2. *Signal 2*: 3D eye-to-nose perspective geometry variation.
  3. *Signal 3*: High-frequency Laplacian texture edge gradients (detects flat paper prints & low-res phone screens).

---

### **SLIDE 6: Dual-Factor Anti-Proxy & Security Hardening**
1. **Identity Binding**: Scanning a classmate's QR code while presenting a different face triggers an immediate `IDENTITY_MISMATCH` rejection and logs a security audit event.
2. **Replay Protection**: Single-use cryptographic ticket tokens prevent duplicate transaction replays.
3. **Database Constraints**: SQLite `UNIQUE(session_id, student_id)` constraint strictly prevents duplicate attendance records.
4. **Immutable Audit Trail**: Chronologically logs all verification successes, mismatches, and spoof attempts with non-accusatory diagnostic reasons.

---

### **SLIDE 7: Live Faculty Dashboard & Institutional Analytics**
- **Modern React + Vite Frontend**:
  - **Classroom Projection Screen**: High-contrast QR with real-time countdown timer.
  - **Live Attendance Roster**: Filter by `Present`, `Late`, `Absent` with auto-polling every 3 seconds.
  - **1-Click CSV Export**: Instant university-compliant attendance report generation.
  - **AI Analytics & Risk Engine**:
    - Evaluates attendance trajectory against academic threshold ($75\%$).
    - Computes exact mathematical margins of missable classes or classes needed to recover before debarment.
    - Generates natural-language insights **100% grounded in SQL metrics (Zero Hallucinations)**.

---

### **SLIDE 8: Privacy-by-Design & 100% Offline Edge Computing**
- **Zero Cloud API Subscriptions**: Eliminates external recurring costs for colleges.
- **Zero Raw Image Persistence**: No facial photographs, camera frames, or video clips are ever saved on disk or in the database.
- **Minimal Biometric Storage**: Only 128-D mathematical feature vectors are stored locally in SQLite.
- **Opaque QR Tokens**: QR codes contain random hexadecimal strings (`SA-STU-XXXXXXXX`), revealing zero personal names or roll numbers to outside scanners.

---

### **SLIDE 9: Direct Impact on Beneficiaries**

| Beneficiary | Problem Faced Before | Transformation with SmartAttend-AI |
| :--- | :--- | :--- |
| **Faculty Members** | 10–15 mins wasted per lecture on roll calling | **Zero time wasted**; 1-click session start and automatic live roster. |
| **Students** | Unfair proxy attendance by peers; lack of warning before $75\%$ debarment | Transparent attendance, anti-proxy fairness, and proactive risk warning. |
| **College Administration** | Manual register compilation; delayed data; biometric privacy liabilities | Real-time institutional analytics, instant CSV exports, 100% offline privacy compliance. |

---

### **SLIDE 10: Live Demonstration & Hackathon Evaluation Readiness**
- **Working Prototype**: 100% functional working prototype tested across 10 automated test suites.
- **Measured Hardware Performance**: Sustained **$107.6\text{ FPS}$** throughput on native CPU; total memory footprint $< 125\text{ MB}$.
- **Tested Scenarios**: Real student check-in, photo spoof rejection, proxy mismatch rejection, duplicate prevention, and CSV export.

---

## 🎯 3. Five-Minute Live Jury Demonstration Script

1. **[0:00 - 0:30] Introduction**: Introduce AGEMC team and highlight Problem Statement A.
2. **[0:30 - 1:15] Faculty Setup**: Create a session on the Faculty Dashboard (`http://localhost:5173`) and project the dynamic classroom QR.
3. **[1:15 - 2:00] Live Check-In**: Run `python run_live_attendance.py` and scan a student QR $\to$ Instant face match ($< 12\text{ ms}$) and green `PRESENT` badge.
4. **[2:00 - 2:45] Anti-Proxy & Anti-Spoofing Test**:
   - Hold up a printed photo $\to$ `SPOOF REJECTED: LIVENESS FAILED`.
   - Scan Student B's QR with Student A's face $\to$ `PROXY REJECTED: IDENTITY MISMATCH`.
5. **[2:45 - 3:30] Live Dashboard & CSV Export**: Show the live roster updated in real-time and export formatted CSV report.
6. **[3:30 - 4:15] AI Analytics & Risk Tab**: Show student risk evaluations and explainable natural-language recommendations.
7. **[4:15 - 5:00] Conclusion**: Summarize edge-AI privacy, zero cloud costs, and direct value to AGEMC administration.
