"""
SmartAttend-AI: Local SQLite Database Manager
Handles Student Profiles, QR Tokens, Face Embeddings, Classroom Sessions,
Attendance Records, and Security Audit Trail.
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

DB_FILE_PATH = Path(__file__).resolve().parent.parent / "smartattend.db"


class DatabaseManager:
    """
    Manages local SQLite database operations with strict data isolation,
    session lifecycle tracking, duplicate prevention, and atomic security audit logging.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_FILE_PATH
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a SQLite connection with row factory enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        """Initializes all database tables, constraints, and indexes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Students Table (Personal Profile & QR Token)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    department TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    section TEXT NOT NULL,
                    qr_token TEXT UNIQUE NOT NULL,
                    is_enrolled BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Face Embeddings Table (Separate from student personal info)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER UNIQUE NOT NULL,
                    sample_count INTEGER DEFAULT 1,
                    embedding_dim INTEGER DEFAULT 128,
                    embedding_bytes BLOB NOT NULL,
                    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
                );
            """)

            # 3. Classroom Sessions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_code TEXT UNIQUE NOT NULL,
                    subject TEXT NOT NULL,
                    department TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    section TEXT NOT NULL,
                    room TEXT NOT NULL,
                    faculty_name TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    regular_window_minutes INTEGER DEFAULT 10,
                    late_window_minutes INTEGER DEFAULT 20,
                    end_time TIMESTAMP NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'ACTIVE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. Attendance Records Table (Idempotent uniqueness per student per session)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attendance_code TEXT UNIQUE NOT NULL,
                    session_id INTEGER NOT NULL,
                    student_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    verification_method TEXT DEFAULT 'QR_FACE_LIVENESS',
                    similarity_score REAL NOT NULL,
                    rejection_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
                    UNIQUE(session_id, student_id)
                );
            """)

            # 5. Security & Attendance Audit Events Table (Step 8)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    session_id INTEGER NOT NULL,
                    student_id INTEGER,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    result TEXT NOT NULL,
                    similarity_score REAL,
                    liveness_score REAL,
                    reason TEXT NOT NULL,
                    metadata_json TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE SET NULL
                );
            """)

            # 6. Used Verification Replay Tokens Table (Step 8)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS used_replay_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_hash TEXT UNIQUE NOT NULL,
                    session_id INTEGER NOT NULL,
                    student_id INTEGER,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
            """)

            # Indexes for high-speed queries and audit reviews
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_roll ON students(student_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_qr ON students(qr_token);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_face_student ON face_embeddings(student_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_code ON sessions(session_code);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_token ON sessions(session_token);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_session ON attendance_records(session_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_student ON attendance_records(student_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_timestamp ON attendance_records(timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_session ON attendance_audit_events(session_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_type ON attendance_audit_events(event_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_severity ON attendance_audit_events(severity);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_replay_token ON used_replay_tokens(token_hash);")
            conn.commit()

    # =========================================================================
    # STUDENT PROFILE OPERATIONS
    # =========================================================================

    def add_student(
        self,
        student_id: str,
        full_name: str,
        department: str,
        year: int,
        section: str,
        qr_token: str
    ) -> Tuple[bool, str, Optional[int]]:
        """Registers a new student profile. Rejects duplicates."""
        student_id = student_id.strip().upper()
        full_name = full_name.strip()
        department = department.strip().upper()
        section = section.strip().upper()

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check duplicate Student ID
            cursor.execute("SELECT id FROM students WHERE student_id = ?", (student_id,))
            if cursor.fetchone() is not None:
                return False, f"Duplicate Error: Student ID '{student_id}' is already registered.", None

            # Check duplicate QR Token
            cursor.execute("SELECT id FROM students WHERE qr_token = ?", (qr_token,))
            if cursor.fetchone() is not None:
                return False, f"Duplicate Error: QR Token '{qr_token}' is already assigned.", None

            try:
                cursor.execute("""
                    INSERT INTO students (student_id, full_name, department, year, section, qr_token, is_enrolled)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (student_id, full_name, department, year, section, qr_token))
                conn.commit()
                return True, "Student registered successfully.", cursor.lastrowid
            except sqlite3.IntegrityError as e:
                return False, f"Database Integrity Error: {str(e)}", None

    def get_student_by_qr(self, qr_token: str) -> Optional[Dict[str, Any]]:
        """Looks up a student by their unique QR token."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, fe.enrolled_at 
                FROM students s 
                LEFT JOIN face_embeddings fe ON s.id = fe.student_id 
                WHERE s.qr_token = ?
            """, (qr_token.strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_student_by_id(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Looks up a student by their Student ID/Roll Number."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id.strip().upper(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_student_by_db_id(self, db_id: int) -> Optional[Dict[str, Any]]:
        """Looks up a student by primary key ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE id = ?", (db_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_face_embedding(
        self,
        student_db_id: int,
        embedding: np.ndarray,
        sample_count: int = 5
    ) -> Tuple[bool, str]:
        """Saves or updates the 128-D face embedding vector for a student."""
        if embedding is None or len(embedding) == 0:
            return False, "Error: Empty embedding vector provided."

        embedding_f32 = np.ascontiguousarray(embedding, dtype=np.float32)
        embedding_bytes = embedding_f32.tobytes()
        dim = len(embedding_f32)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO face_embeddings (student_id, sample_count, embedding_dim, embedding_bytes)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(student_id) DO UPDATE SET
                        sample_count = excluded.sample_count,
                        embedding_dim = excluded.embedding_dim,
                        embedding_bytes = excluded.embedding_bytes,
                        enrolled_at = CURRENT_TIMESTAMP
                """, (student_db_id, sample_count, dim, embedding_bytes))

                cursor.execute("UPDATE students SET is_enrolled = 1 WHERE id = ?", (student_db_id,))
                conn.commit()
                return True, "Face embedding saved and student marked as enrolled."
            except Exception as e:
                return False, f"Failed to save face embedding: {str(e)}"

    def get_face_embedding(self, student_db_id: int) -> Optional[np.ndarray]:
        """Retrieves and deserializes the face embedding vector for a student."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT embedding_bytes, embedding_dim FROM face_embeddings WHERE student_id = ?", (student_db_id,))
            row = cursor.fetchone()
            if row:
                raw_bytes = row["embedding_bytes"]
                dim = row["embedding_dim"]
                return np.frombuffer(raw_bytes, dtype=np.float32).reshape((dim,))
            return None

    def list_all_students(self) -> List[Dict[str, Any]]:
        """Returns all registered students."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students ORDER BY id ASC")
            return [dict(row) for row in cursor.fetchall()]

    def load_all_enrolled_students(self) -> List[Dict[str, Any]]:
        """Loads all enrolled students along with their 128-D face embedding vectors."""
        results = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.student_id, s.full_name, s.department, s.year, s.section,
                       fe.embedding_bytes, fe.embedding_dim, fe.sample_count, fe.enrolled_at
                FROM students s
                INNER JOIN face_embeddings fe ON s.id = fe.student_id
                WHERE s.is_enrolled = 1
            """)
            rows = cursor.fetchall()
            for row in rows:
                raw_bytes = row["embedding_bytes"]
                dim = row["embedding_dim"]
                emb_vector = np.frombuffer(raw_bytes, dtype=np.float32).reshape((dim,))
                results.append({
                    "id": row["id"],
                    "student_id": row["student_id"],
                    "full_name": row["full_name"],
                    "department": row["department"],
                    "year": row["year"],
                    "section": row["section"],
                    "sample_count": row["sample_count"],
                    "enrolled_at": row["enrolled_at"],
                    "embedding": emb_vector
                })
        return results

    # =========================================================================
    # CLASSROOM SESSION OPERATIONS
    # =========================================================================

    def create_session(
        self,
        session_code: str,
        subject: str,
        department: str,
        year: int,
        section: str,
        room: str,
        faculty_name: str,
        start_time: datetime,
        regular_window_minutes: int,
        late_window_minutes: int,
        end_time: datetime,
        session_token: str
    ) -> Tuple[bool, str, Optional[int]]:
        """Creates a new classroom session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO sessions (
                        session_code, subject, department, year, section, room,
                        faculty_name, start_time, regular_window_minutes,
                        late_window_minutes, end_time, session_token, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                """, (
                    session_code, subject, department.upper(), year, section.upper(), room,
                    faculty_name, start_time.isoformat(), regular_window_minutes,
                    late_window_minutes, end_time.isoformat(), session_token
                ))
                conn.commit()
                return True, "Session created successfully.", cursor.lastrowid
            except sqlite3.IntegrityError as e:
                return False, f"Integrity Error: {str(e)}", None

    def get_session_by_code(self, session_code: str) -> Optional[Dict[str, Any]]:
        """Retrieves a session by session_code."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_code = ?", (session_code.strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_session_by_token(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Retrieves a session by its random session token."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_token = ?", (session_token.strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_session_by_id(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a session by primary key ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def close_session(self, session_id_or_code: Any) -> Tuple[bool, str]:
        """Closes an active classroom session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if isinstance(session_id_or_code, int) or (isinstance(session_id_or_code, str) and session_id_or_code.isdigit()):
                cursor.execute("UPDATE sessions SET status = 'CLOSED' WHERE id = ?", (int(session_id_or_code),))
            else:
                cursor.execute("UPDATE sessions SET status = 'CLOSED' WHERE session_code = ?", (str(session_id_or_code),))
            conn.commit()
            if cursor.rowcount > 0:
                return True, "Session closed successfully."
            return False, "Session not found."

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """Lists all currently active sessions."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE status = 'ACTIVE' ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # ATTENDANCE RECORD OPERATIONS (ATOMIC TRANSACTION SUPPORT)
    # =========================================================================

    def record_attendance(
        self,
        attendance_code: str,
        session_id: int,
        student_id: int,
        status: str,
        similarity_score: float,
        verification_method: str = "QR_FACE_LIVENESS",
        rejection_reason: Optional[str] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Records student attendance for a session.
        Enforces database-level uniqueness on (session_id, student_id).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check existing record for duplicate prevention
            cursor.execute(
                "SELECT id, status, timestamp FROM attendance_records WHERE session_id = ? AND student_id = ?",
                (session_id, student_id)
            )
            existing = cursor.fetchone()
            if existing:
                return False, f"ALREADY MARKED: Attendance already recorded as {existing['status']}.", existing["id"]

            try:
                cursor.execute("""
                    INSERT INTO attendance_records (
                        attendance_code, session_id, student_id, status,
                        verification_method, similarity_score, rejection_reason
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    attendance_code, session_id, student_id, status,
                    verification_method, similarity_score, rejection_reason
                ))
                conn.commit()
                return True, f"Attendance recorded as {status}.", cursor.lastrowid
            except sqlite3.IntegrityError:
                return False, "ALREADY MARKED: Duplicate attendance attempt rejected.", None

    def get_student_session_attendance(self, session_id: int, student_id: int) -> Optional[Dict[str, Any]]:
        """Checks if a student already has an attendance record in this session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM attendance_records WHERE session_id = ? AND student_id = ?",
                (session_id, student_id)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_session_attendance_records(self, session_id: int) -> List[Dict[str, Any]]:
        """Returns all attendance entries for a given session with student details."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ar.*, s.student_id as roll_no, s.full_name, s.department, s.year, s.section
                FROM attendance_records ar
                INNER JOIN students s ON ar.student_id = s.id
                WHERE ar.session_id = ?
                ORDER BY ar.timestamp ASC
            """, (session_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_session_attendance_summary(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Computes summary statistics and cohort attendance lists."""
        session = self.get_session_by_id(session_id)
        if not session:
            return None

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Total cohort students
            cursor.execute("""
                SELECT id, student_id, full_name, department, year, section
                FROM students
                WHERE department = ? AND year = ? AND section = ?
                ORDER BY student_id ASC
            """, (session["department"], session["year"], session["section"]))
            cohort_students = [dict(r) for r in cursor.fetchall()]

            # 2. Marked attendance records
            cursor.execute("""
                SELECT ar.*, s.student_id as roll_no, s.full_name
                FROM attendance_records ar
                INNER JOIN students s ON ar.student_id = s.id
                WHERE ar.session_id = ?
            """, (session_id,))
            marked_records = [dict(r) for r in cursor.fetchall()]

            marked_student_ids = {r["student_id"]: r for r in marked_records}

            present_students = []
            late_students = []
            rejected_count = sum(1 for r in marked_records if r["status"] == "REJECTED")

            for r in marked_records:
                if r["status"] == "PRESENT":
                    present_students.append({
                        "student_id": r["roll_no"],
                        "full_name": r["full_name"],
                        "timestamp": r["timestamp"],
                        "similarity": r["similarity_score"]
                    })
                elif r["status"] == "LATE":
                    late_students.append({
                        "student_id": r["roll_no"],
                        "full_name": r["full_name"],
                        "timestamp": r["timestamp"],
                        "similarity": r["similarity_score"]
                    })

            absent_students = []
            for s in cohort_students:
                if s["id"] not in marked_student_ids or marked_student_ids[s["id"]]["status"] == "REJECTED":
                    absent_students.append({
                        "student_id": s["student_id"],
                        "full_name": s["full_name"]
                    })

            return {
                "session": session,
                "total_registered": len(cohort_students),
                "present_count": len(present_students),
                "late_count": len(late_students),
                "absent_count": len(absent_students),
                "rejected_count": rejected_count,
                "present_students": present_students,
                "late_students": late_students,
                "absent_students": absent_students
            }

    # =========================================================================
    # SECURITY AUDIT TRAIL & REPLAY TOKEN OPERATIONS (Step 8)
    # =========================================================================

    def log_audit_event(
        self,
        session_id: int,
        event_type: str,
        severity: str,
        result: str,
        reason: str,
        student_id: Optional[int] = None,
        similarity_score: Optional[float] = None,
        liveness_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Records a non-sensitive security audit event into attendance_audit_events.
        Strictly does NOT store raw images or embeddings.
        """
        event_id = f"EVT-{uuid.uuid4().hex[:12].upper()}"
        meta_json = json.dumps(metadata) if metadata else None

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO attendance_audit_events (
                    event_id, session_id, student_id, event_type, severity,
                    result, similarity_score, liveness_score, reason, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, session_id, student_id, event_type, severity,
                result, similarity_score, liveness_score, reason, meta_json
            ))
            conn.commit()

        return event_id

    def check_and_use_replay_token(
        self,
        token_hash: str,
        session_id: int,
        student_id: Optional[int] = None
    ) -> bool:
        """
        Verifies if a transaction token has already been used (Atomic replay check).
        Returns True if token is fresh and successfully claimed, False if replayed.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO used_replay_tokens (token_hash, session_id, student_id)
                    VALUES (?, ?, ?)
                """, (token_hash, session_id, student_id))
                conn.commit()
                return True # Successfully consumed
            except sqlite3.IntegrityError:
                return False # Duplicate replay attack detected

    def get_audit_events_for_session(self, session_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves audit events for a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ae.*, s.student_id as roll_no, s.full_name
                FROM attendance_audit_events ae
                LEFT JOIN students s ON ae.student_id = s.id
                WHERE ae.session_id = ?
                ORDER BY ae.id DESC LIMIT ?
            """, (session_id, limit))
            return [dict(r) for r in cursor.fetchall()]

    def get_recent_suspicious_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent suspicious or high-severity security events for faculty review."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ae.*, s.student_id as roll_no, s.full_name, sess.session_code, sess.subject
                FROM attendance_audit_events ae
                LEFT JOIN students s ON ae.student_id = s.id
                LEFT JOIN sessions sess ON ae.session_id = sess.id
                WHERE ae.severity IN ('HIGH', 'WARNING') OR ae.event_type IN ('SUSPICIOUS_ACTIVITY', 'IDENTITY_MISMATCH', 'LIVENESS_FAILED', 'REPLAY_ATTEMPT', 'DUPLICATE_ATTEMPT')
                ORDER BY ae.id DESC LIMIT ?
            """, (limit,))
            rows = [dict(r) for r in cursor.fetchall()]

        # Parse metadata_json for culprit & target info
        for r in rows:
            meta = {}
            if r.get("metadata_json"):
                try:
                    meta = json.loads(r["metadata_json"])
                except Exception:
                    meta = {}
            r["culprit_roll_no"] = meta.get("culprit_roll_no") or r.get("roll_no") or "Unknown"
            r["culprit_name"] = meta.get("culprit_name") or r.get("full_name") or "Unknown / Unenrolled Face"
            r["target_roll_no"] = meta.get("target_roll_no") or r.get("roll_no")
            r["target_name"] = meta.get("target_name") or r.get("full_name")
            r["parsed_meta"] = meta
        return rows

    def get_session_security_summary(self, session_id: int) -> Dict[str, Any]:
        """
        Computes security audit summary for a session:
        - Total verification attempts
        - Successful verifications
        - Rejected attempts
        - Identity mismatches
        - Liveness failures
        - Unknown faces
        - Duplicate attempts
        - Replay attempts
        - Suspicious events count
        - Per-student breakdown
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_type, result, severity, student_id
                FROM attendance_audit_events
                WHERE session_id = ?
            """, (session_id,))
            events = [dict(r) for r in cursor.fetchall()]

        total_attempts = len(events)
        successes = sum(1 for e in events if e["result"] == "SUCCESS")
        rejected = sum(1 for e in events if e["result"] == "REJECTED")
        mismatches = sum(1 for e in events if e["event_type"] == "IDENTITY_MISMATCH")
        liveness_fails = sum(1 for e in events if e["event_type"] == "LIVENESS_FAILED")
        unknown_faces = sum(1 for e in events if e["event_type"] == "FACE_UNKNOWN")
        duplicates = sum(1 for e in events if e["event_type"] == "DUPLICATE_ATTEMPT")
        replays = sum(1 for e in events if e["event_type"] == "REPLAY_ATTEMPT")
        suspicious = sum(1 for e in events if e["event_type"] == "SUSPICIOUS_ACTIVITY" or e["severity"] == "HIGH")

        # Per-student breakdown
        student_counts: Dict[Any, int] = {}
        for e in events:
            if e["student_id"] and e["result"] != "SUCCESS":
                student_counts[e["student_id"]] = student_counts.get(e["student_id"], 0) + 1

        return {
            "total_attempts": total_attempts,
            "successful_verifications": successes,
            "rejected_attempts": rejected,
            "identity_mismatches": mismatches,
            "liveness_failures": liveness_fails,
            "unknown_faces": unknown_faces,
            "duplicate_attempts": duplicates,
            "replay_attempts": replays,
            "suspicious_events": suspicious,
            "per_student_suspicious_counts": student_counts
        }

    # -------------------------------------------------------------------------
    # 7. Manual Faculty Management & Deletion Operations
    # -------------------------------------------------------------------------
    def delete_session(self, session_id: int) -> bool:
        """Permanently deletes a session and its associated records and audit logs."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM attendance_records WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM attendance_audit_events WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM used_replay_tokens WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] delete_session failed: {e}")
            return False

    def delete_student(self, student_id: str) -> bool:
        """Permanently deletes a student, their face embeddings, and attendance records."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Find student DB ID
                cursor.execute("SELECT id FROM students WHERE student_id = ? OR id = ?", (student_id, student_id))
                row = cursor.fetchone()
                if not row:
                    return False
                db_id = row["id"]

                cursor.execute("DELETE FROM face_embeddings WHERE student_id = ?", (db_id,))
                cursor.execute("DELETE FROM attendance_records WHERE student_id = ?", (db_id,))
                cursor.execute("DELETE FROM attendance_audit_events WHERE student_id = ?", (db_id,))
                cursor.execute("DELETE FROM students WHERE id = ?", (db_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] delete_student failed: {e}")
            return False

    def manual_mark_attendance(
        self,
        session_id: int,
        student_id: int,
        status: str,
        reason: str = "MANUAL_FACULTY_OVERRIDE"
    ) -> Tuple[bool, str]:
        """Allows faculty to manually record or change attendance status for any student."""
        status = status.upper().strip()
        if status not in ("PRESENT", "LATE", "ABSENT"):
            return False, f"Invalid attendance status '{status}'. Must be PRESENT, LATE, or ABSENT."

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # If ABSENT, remove any marked attendance record
                if status == "ABSENT":
                    cursor.execute("DELETE FROM attendance_records WHERE session_id = ? AND student_id = ?", (session_id, student_id))
                    conn.commit()
                    return True, "Student marked as ABSENT."

                # Check if already has a record
                cursor.execute("SELECT id FROM attendance_records WHERE session_id = ? AND student_id = ?", (session_id, student_id))
                existing = cursor.fetchone()

                if existing:
                    cursor.execute("""
                        UPDATE attendance_records
                        SET status = ?, verification_method = 'MANUAL_FACULTY', similarity_score = 1.0, timestamp = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (status, existing["id"]))
                else:
                    att_code = f"ATT-MANUAL-{uuid.uuid4().hex[:8].upper()}"
                    cursor.execute("""
                        INSERT INTO attendance_records (attendance_code, session_id, student_id, status, verification_method, similarity_score)
                        VALUES (?, ?, ?, ?, 'MANUAL_FACULTY', 1.0)
                    """, (att_code, session_id, student_id, status))

                # Log to audit trail
                evt_id = f"EVT-MANUAL-{uuid.uuid4().hex[:8].upper()}"
                cursor.execute("""
                    INSERT INTO attendance_audit_events (event_id, session_id, student_id, event_type, severity, result, similarity_score, reason)
                    VALUES (?, ?, ?, 'MANUAL_FACULTY_OVERRIDE', 'INFO', 'SUCCESS', 1.0, ?)
                """, (evt_id, session_id, student_id, f"Faculty manually set status to {status} ({reason})"))

                conn.commit()
                return True, f"Attendance status successfully set to {status}."
        except Exception as e:
            return False, f"Failed to update attendance: {e}"

    def delete_attendance_record(self, session_id: int, student_id: int) -> bool:
        """Removes an attendance record for a student in a session."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM attendance_records WHERE session_id = ? AND student_id = ?", (session_id, student_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] delete_attendance_record failed: {e}")
            return False

    def clear_all_sessions(self) -> bool:
        """Permanently deletes ALL sessions, attendance records, and audit events."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM attendance_records;")
                cursor.execute("DELETE FROM attendance_audit_events;")
                cursor.execute("DELETE FROM used_replay_tokens;")
                cursor.execute("DELETE FROM sessions;")
                conn.commit()
                return True
        except Exception as e:
            print(f"[ERROR] clear_all_sessions failed: {e}")
            return False

    def get_student_attendance_breakdown(self, student_id_or_roll: Any) -> Dict[str, Any]:
        """
        Returns full class-by-class attendance history and statistics for a single student.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Find student
            cursor.execute("SELECT * FROM students WHERE id = ? OR student_id = ?", (student_id_or_roll, student_id_or_roll))
            student = cursor.fetchone()
            if not student:
                return {}

            student_dict = dict(student)
            db_id = student_dict["id"]

            # Get all sessions matching student's department and year
            cursor.execute("""
                SELECT s.id as session_id, s.session_code, s.subject, s.department, s.year, s.room, s.faculty_name, s.start_time, s.status as session_status,
                       ar.id as record_id, ar.status as attendance_status, ar.timestamp as checkin_time, ar.verification_method, ar.similarity_score
                FROM sessions s
                LEFT JOIN attendance_records ar ON s.id = ar.session_id AND ar.student_id = ?
                WHERE s.department = ? AND s.year = ?
                ORDER BY s.id DESC
            """, (db_id, student_dict["department"], student_dict["year"]))

            records = [dict(r) for r in cursor.fetchall()]

        total_sessions = len(records)
        present_count = sum(1 for r in records if r["attendance_status"] == "PRESENT")
        late_count = sum(1 for r in records if r["attendance_status"] == "LATE")
        absent_count = total_sessions - (present_count + late_count)
        attended = present_count + late_count
        attendance_pct = round((attended / max(1, total_sessions)) * 100, 1) if total_sessions > 0 else 0.0

        for r in records:
            if not r["attendance_status"]:
                r["attendance_status"] = "ABSENT"

        return {
            "student": student_dict,
            "total_classes": total_sessions,
            "present_count": present_count,
            "late_count": late_count,
            "absent_count": absent_count,
            "attendance_rate": attendance_pct,
            "classes": records
        }
