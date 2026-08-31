# SmartAttend-AI API Specification

## Health & Diagnostics
- `GET /api/health`: System health & database connectivity status.

## Attendance Endpoints (v1)
- `GET /api/v1/attendance`: Retrieve attendance logs.
- `POST /api/v1/attendance/verify`: Submit frame or face embeddings for verification.
- `POST /api/v1/attendance/check-in`: Record verified attendance.

## Interactive API Docs
When running FastAPI:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
