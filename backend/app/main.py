from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.db_manager import DatabaseManager
from backend.routes import (
    health,
    session_routes,
    attendance_routes,
    dashboard_routes,
    student_routes,
    security_routes,
    audit_routes,
    analytics_routes
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize local SQLite schema on startup
    db = DatabaseManager()
    db.init_schema()
    yield

app = FastAPI(
    title="SmartAttend-AI Faculty API",
    description="Local AI-powered Attendance & Faculty Management System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(dashboard_routes.router)
app.include_router(session_routes.router)
app.include_router(attendance_routes.router)
app.include_router(student_routes.router)
app.include_router(security_routes.router)
app.include_router(audit_routes.router)
app.include_router(analytics_routes.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
