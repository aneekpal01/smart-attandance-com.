# SmartAttend-AI: Local AI Analytics & Intelligence Layer (Step 10)

Offline-first, explainable intelligence layer for **SmartAttend-AI**, transforming raw classroom attendance logs into statistical trends, attendance-risk predictions, behavioral anomalies, and natural-language faculty insights.

---

## 🏗️ Analytics & Intelligence Architecture

```text
                     RAW SQLite ATTENDANCE & AUDIT LOGS
                                     │
                                     ▼
                        [Analytics Service]
            (Overall Stats, Cohort Profiles, Subject Breakdown)
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
[Temporal Trend Engine]    [Risk Prediction Engine]    [Anomaly Detection]
(Moving Avg & Trajectory)  (Explainable Risk Scoring)   (Z-Score & Streaks)
        │                            │                            │
        └────────────────────────────┼────────────────────────────┘
                                     │
                                     ▼
                        [Explainable Insights Engine]
            (Fact-Grounded Natural-Language Insights Generator)
                                     │
                                     ▼
                    [Faculty Analytics Dashboard UI]
```

---

## 📊 Core Analytic Capabilities

### 1. Attendance Risk Prediction Methodology
- **Academic Baseline Threshold**: Configurable (e.g. $75\%$ or $80\%$).
- **Features Evaluated**:
  - Distance from threshold ($\Delta \% = \text{Target} - \text{Current}$)
  - Recent absence streaks in last $5$ sessions
  - Temporal trajectory direction (`IMPROVING`, `DECLINING`, `STABLE`)
- **Outputs**:
  - `Risk Level`: `LOW`, `MEDIUM`, `HIGH`, or `INSUFFICIENT_DATA`.
  - `Margin of Missable Classes`: Mathematically estimated future classes student can miss before falling below threshold.
  - `Classes to Recover`: Number of consecutive classes needed to recover from below-threshold status.

### 2. Temporal Trend Detection
- Analyzes daily attendance percentages across 7-day, 30-day, and semester windows.
- Compares rolling baseline averages to classify cohort trajectories:
  - $\Delta \ge +3\% \implies \text{IMPROVING}$
  - $\Delta \le -3\% \implies \text{DECLINING}$
  - Otherwise $\implies \text{STABLE}$

### 3. Anomaly Detection
- **Session Attendance Drops**: Identifies abnormal drops where $Z\text{-score} < -1.5$ relative to historical class averages.
- **Student Absence Streaks**: Identifies students with $\ge 3$ consecutive missed sessions.
- **Verification Failure Spikes**: Flags sessions with unusually high rejection or spoof attempts ($\ge 4$ failures).

### 4. Explainable AI Insights Engine
- Generates concise natural-language statements for faculty.
- **Zero Hallucination Guarantee**: Every single insight is strictly grounded in database SQL aggregates and returns the exact numerical `grounding_metric`.

---

## 🛡️ Small-Data Safety & Privacy Guarantees

### ✅ Small-Data Safety:
- If fewer than $3$ classes are recorded for a student, the system returns `INSUFFICIENT_DATA` with a transparent explanation rather than manufacturing false predictions.

### 🔒 Biometric Privacy:
- Strictly excludes raw face embeddings, image crops, and biometric vectors from all analytics outputs.

---

## ⚠️ Transparent Limitations Disclosure
1. **Educational Estimates**: Risk predictions and missable class margins are mathematical trajectory estimates based on historical records, not infallible future certainties.
2. **External Factors**: The model evaluates recorded attendance metrics and cannot account for excused medical leaves unless logged in the institutional database.

---

## 🚀 How to Run

### 1. Run Automated Test Suite (16 Tests)
```powershell
cd "C:\Users\aneek pal\.gemini\antigravity\scratch\SmartAttend-AI"
.\venv\Scripts\activate

python -m ai.analytics.test_step10_analytics
```

### 2. View in Faculty Dashboard
Start the backend and frontend servers, then navigate to **"AI Analytics & Risk"** in the sidebar.
