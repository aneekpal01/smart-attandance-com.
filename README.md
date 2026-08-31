# SmartAttend-AI 🎯
### **Next-Gen Autonomous Biometric Attendance & Security Intelligence Platform**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3.1-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactjs.org)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-YuNet%20%2B%20SFace-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

---

## 📌 Overview

**SmartAttend-AI** is a high-performance, offline-capable, AI-driven Smart Attendance & Classroom Analytics System engineered for universities and educational institutions.

The platform eliminates proxy attendance and buddy-punching through a dual-factor biometric pipeline: **Dynamic Session QR Tokens** bound with **Live Local Face & Retina Verification (OpenCV YuNet + SFace 128-D Embeddings)** and **AI-based Background Removal**.

Designed with zero external cloud API dependencies, all computer vision inference, feature vector cosine similarity, and liveness checks execute entirely on edge/local hardware in under **50ms**.

---

## ✨ Key Features

- 🔐 **Dual-Factor Anti-Proxy Binding**: Binds dynamic classroom QR session tokens with real-time facial feature vector validation.
- 👁️ **Biometric Face & Retina Ocular Recognition**: 128-D facial vector cosine similarity matching (\(\ge 0.60\) threshold) using SFace DNN.
- ⚡ **Auto & Manual Capture Modes**: Configurable 10-second smart countdown timer with eye reticle alignment HUD and manual single-click capture.
- 🖼️ **Python AI Background Removal**: Automatic OpenCV GrabCut & YuNet facial contour isolation over a sleek dark studio slate.
- 📱 **Zero-Cost BYOD Mobile Check-In**: Students can scan the projector screen QR from any smartphone browser without installing third-party apps.
- 📊 **Faculty Real-Time Dashboard**: Live attendance roster, countdown timers, security telemetry alerts, student directories with batch capacities, and CSV export.
- 🛡️ **Privacy by Design**: Zero raw video frames or unencrypted biometric face crops stored in database tables — only cryptographically separated vector embeddings and audit hashes.
- 📅 **Academic Calendar 2026**: Integrated faculty calendar with active semester tracking and day navigation.

---

## 🏗️ Architecture & Pipeline

```text
                                  +-----------------------------+
                                  |    Classroom Session (DB)   |
                                  | (Timing Windows: Pres / Late)
                                  +--------------+--------------+
                                                 |
                                                 v
+-----------------------+           +------------+------------+
|   Student QR Token    |           |    Temporary Session    |
| (No Personal Payload) |           |       QR Token          |
+-----------+-----------+           +------------+------------+
            |                                    |
            +-----------------+------------------+
                              |
                              v
                  [1] Session Verification
                              |
                              v
              [2] Face Detection (YuNet ONNX)
                              |
              [3] Face Embedding (SFace ONNX)
                              |
              [4] Vector Cosine Similarity
                              |
              [5] Identity Anti-Mismatch Check
               (Does QR Student == Recognized Face?)
                              |
             ┌────────────────┴────────────────┐
             │                                 │
           MATCH                           MISMATCH
             │                                 │
             ▼                                 ▼
   [6] SQLite Attendance Log         [!] ATTENDANCE REJECTED
  (Status: PRESENT / LATE)           (Identity Mismatch Reason)
```

---

## 🚀 Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, SQLite, NumPy, Pydantic v2
- **Computer Vision & AI**: OpenCV DNN (`YuNet` Face Detection, `SFace` 128-D Embeddings), GrabCut Segmentation
- **Frontend**: React 18, Vite, Lucide Icons, Modern CSS Liquid-Glass Theme
- **Testing**: Pytest, Automated 10-Suite Regression Framework

---

## 🛠️ Quick Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/aneekpal01/smart-attandance-com..git
cd smart-attandance-com
```

### 2. Python Backend Setup
```bash
# Create and activate virtual environment
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download pre-trained CV ONNX weights (YuNet + SFace)
python -m ai.models.download_models
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Launch the Complete System
```bash
# Run backend server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# In a separate terminal, launch the frontend dev server:
cd frontend
npm run dev -- --host 0.0.0.0
```

*Or double-click `start_system.bat` on Windows for one-click startup.*

Access the portals:
- **Faculty Dashboard**: `http://localhost:5173`
- **Interactive Swagger API Docs**: `http://localhost:8000/docs`

---

## 🧪 Running Automated Test Suites

The codebase includes comprehensive integration and end-to-end regression suites:

```bash
# Run master 10-suite regression test runner
python -m tests.run_all
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

Developed by **[Aneek Pal](https://github.com/aneekpal01)**.
