# SmartAttend-AI System Architecture

## Overview
SmartAttend-AI is designed with a decoupled architecture separating frontend presentation, backend REST APIs, AI/Computer Vision inference pipelines, and persistent storage.

```text
+-----------------------+           +-----------------------+
|  React + Vite Client  | <=======> |  FastAPI Backend Core |
|  (Port: 5173)         |   HTTP    |  (Port: 8000)         |
+-----------------------+           +-----------+-----------+
                                                |
                      +-------------------------+-------------------------+
                      |                                                   |
                      v                                                   v
           +-----------------------+                           +---------------------+
           |   AI Engine Modules   |                           |  SQLite Database    |
           | - InsightFace / YOLO  |                           |  (Local zero-setup) |
           | - Anti-Spoof Liveness |                           +---------------------+
           | - ByteTrack Tracking  |
           +-----------------------+
```

## Layer Specifications
1. **Frontend**: React + Vite SPA
2. **Backend**: Python 3.10+ / FastAPI asynchronous server
3. **AI Pipeline**: Modular Python CV modules with PyTorch, Ultralytics, InsightFace, OpenCV
4. **Database**: SQLite (Development) / PostgreSQL-ready (Production via SQLAlchemy)
