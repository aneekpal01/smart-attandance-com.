from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from datetime import datetime
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True, nullable=False)
    user_code = Column(String, unique=True, index=True, nullable=False)
    face_embedding_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    confidence_score = Column(Float, nullable=False)
    liveness_verified = Column(Boolean, default=True)
    device_id = Column(String, default="camera_default")
    status = Column(String, default="PRESENT")
