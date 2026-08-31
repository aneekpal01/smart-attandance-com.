-- SmartAttend-AI Initial SQLite Schema

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    user_code TEXT UNIQUE NOT NULL,
    face_embedding_id TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS attendance_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence_score REAL NOT NULL,
    liveness_verified BOOLEAN DEFAULT 1,
    device_id TEXT DEFAULT 'camera_default',
    status TEXT DEFAULT 'PRESENT',
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_users_code ON users(user_code);
CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_attendance_user ON attendance_logs(user_id);
