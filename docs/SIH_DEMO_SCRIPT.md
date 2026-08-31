# SmartAttend-AI: 5-Minute SIH Live Demonstration Script

**Target Audience**: Smart India Hackathon Evaluation Jury & Faculty Evaluators  
**Total Duration**: 5 Minutes (Timed Stage Progression)  
**System Architecture**: 100% Local / Offline Edge AI (YuNet + SFace + SQLite + FastAPI + React)  

---

## ⏱️ Timeline & Presentation Flow

```text
[0:00 - 0:30] ➔ The Real Classroom Problem & Challenge
[0:30 - 1:15] ➔ Faculty Dashboard: One-Click Session & Dynamic Projector QR
[1:15 - 2:00] ➔ Student Verification: Dynamic QR + Local AI Face Recognition
[2:00 - 2:45] ➔ Multi-Signal Liveness & Anti-Proxy Interception
[2:45 - 3:30] ➔ Live Dashboard Telemetry & Real-Time Roster Updates
[3:30 - 4:15] ➔ AI Analytics, Predictive Attendance Risk & Anomaly Detection
[4:15 - 5:00] ➔ Offline Privacy Guarantee, Architectural Impact & Q&A
```

---

### **[0:00 – 0:30] Phase 1: Problem Introduction**
* **Presenter Voice**:
  > *"Respected Jury Members, across Indian higher education institutions, classical classroom attendance takes 10 to 15 minutes of instructional time every lecture, while conventional RFID or static QR codes suffer from widespread proxy attendance. Cloud-based facial recognition systems face severe internet latency, bandwidth bottlenecks, and serious student biometric privacy risks.*
  >
  > *We present **SmartAttend-AI** — an entirely offline, privacy-first, edge-AI attendance and intelligence system powered by lightweight ONNX computer vision models, dynamic cryptographic QR binding, multi-signal liveness verification, and explainable attendance-risk analytics."*

---

### **[0:30 – 1:15] Phase 2: Faculty Session Creation & Dynamic Classroom QR**
* **Action on Screen**:
  1. Open Faculty Dashboard (`http://localhost:5173`).
  2. Click **"Create Session"** (`SessionsPage.jsx`).
  3. Enter Subject (*"High Performance Computing & AI Systems"*), Room (*"AUD-101"*), and set 15m Regular / 30m Late window.
  4. Click **"Create & Start Classroom Session"**.
  5. The **Active Session Projector Screen** displays a high-contrast dynamic QR code with live countdown timer.
* **Presenter Voice**:
  > *"When the professor begins class, they create a time-windowed session with a single click. A temporary, dynamic session QR code is projected onto the classroom screen. This token contains a session hash with a strict temporal validity window — completely blocking cross-session injection or attendance logging after the lecture."*

---

### **[1:15 – 2:00] Phase 3: Student Verification & Local Face Recognition**
* **Action on Screen**:
  1. Show student presenting their personal identity QR code.
  2. The local camera HUD immediately decodes the random token `SA-STU-...` and maps it to the local student record (e.g. *Margaret Hamilton, CS-2026-01*).
  3. OpenCV **YuNet DNN** detects the face bounding box and 5 facial landmarks in **< 10 ms**.
  4. **SFace ONNX** extracts a 128-dimensional normalized embedding and computes cosine similarity against the local vector database in **< 1 ms**.
* **Presenter Voice**:
  > *"The student presents their unique QR token. In under 12 milliseconds, our local ONNX YuNet detector locates the face, and our SFace neural net matches the 128-dimensional embedding against the database. Notice that no student names or roll numbers are stored in the QR — it contains only an opaque cryptographic token."*

---

### **[2:00 – 2:45] Phase 4: Multi-Signal Liveness & Anti-Proxy Interception**
* **Action on Screen / Live Demo**:
  1. Demonstrate a real student receiving `LIVE` state and `PRESENT` status.
  2. **Attack Demo 1 (Photo Spoof)**: Hold up a printed photo or phone screen image. The system analyzes eye-to-nose 3D ratios, texture gradients, and landmark temporal jitter, instantly flagging `SPOOF` and rejecting attendance.
  3. **Attack Demo 2 (Proxy Mismatch)**: Scan Student B's QR while Student A's face is in front of the camera. The system triggers `IDENTITY_MISMATCH` with zero database writes.
* **Presenter Voice**:
  > *"SmartAttend-AI enforces two layers of defense against proxies: First, a multi-signal temporal liveness engine that inspects high-frequency texture and facial micro-dynamics, rejecting flat prints or phone screens. Second, an atomic anti-proxy binding that ensures the scanned QR owner strictly matches the recognized biometric face. Proxy attempts are blocked and logged in our immutable security audit trail."*

---

### **[2:45 – 3:30] Phase 5: Live Faculty Dashboard & Instant CSV Compliance**
* **Action on Screen**:
  1. Switch back to **"Active Session"** / **"Live Monitor"** on the faculty dashboard.
  2. Observe the live counters update immediately: `Present: 1`, `Late: 0`, `Absent: 5`.
  3. Click **"Export CSV"** to demonstrate immediate generation of formatted institutional attendance reports.
* **Presenter Voice**:
  > *"As students walk in, the faculty dashboard updates in real-time. With one click, faculty can close the attendance window and export university-compliant CSV reports — eliminating manual tallying entirely."*

---

### **[3:30 – 4:15] Phase 6: AI Analytics, Predictive Risk & Explainable Insights**
* **Action on Screen**:
  1. Click **"AI Analytics & Risk"** in the sidebar (`AnalyticsPage.jsx`).
  2. Highlight the **Overall Attendance %**, **Attendance Trajectory Bar Chart**, and **Subject Breakdown**.
  3. Scroll to **Student Risk Analysis Table**: Highlight *John von Neumann (CS-2026-06)* marked as `HIGH` risk with margin explanation: *"Needs 4 consecutive classes to reach 75% requirement."*
  4. Highlight **Explainable AI Insights Feed** (100% grounded in SQL metrics).
* **Presenter Voice**:
  > *"Beyond attendance tracking, SmartAttend-AI features an explainable intelligence layer. It evaluates student attendance trajectories against academic thresholds (e.g. 75%), calculates exact margins of missable classes, and generates natural-language insights with zero AI hallucination — enabling proactive faculty intervention before exam debarment."*

---

### **[4:15 – 5:00] Phase 7: Offline Edge Privacy & Conclusion**
* **Presenter Voice**:
  > *"To summarize: SmartAttend-AI operates 100% offline at over 100 FPS on ordinary college laptops. No raw face photos or video streams are ever stored on disk or transmitted over the internet. It delivers unmatched privacy, zero proxy tolerance, and actionable academic intelligence for Indian universities. Thank you!"*
