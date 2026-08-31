"""
SmartAttend-AI: Student Enrollment Service
Orchestrates student registration, QR generation, QR identity lookup, and face embedding storage.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from database.db_manager import DatabaseManager
from ai.face_recognition.qr_manager import QRManager
from ai.face_recognition.embedder import FaceEmbedder


@dataclass
class StudentProfile:
    id: int
    student_id: str
    full_name: str
    department: str
    year: int
    section: str
    qr_token: str
    is_enrolled: bool


class StudentEnrollmentService:
    """
    Core business logic for Step 4 Enrollment flow:
    Student Info -> QR Token Generation -> QR Scan & Verify -> Multi-sample Face Embedding -> Storage.
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.qr_manager = QRManager()
        self.embedder = FaceEmbedder()

    def register_new_student(
        self,
        student_id: str,
        full_name: str,
        department: str,
        year: int,
        section: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        1. Validates inputs
        2. Generates unique secure QR token
        3. Generates QR PNG image locally
        4. Saves student profile into SQLite
        """
        if not student_id or not full_name or not department or not section:
            return False, "Validation Error: All student fields are required.", None

        if int(year) <= 0 or int(year) > 6:
            return False, "Validation Error: Year must be between 1 and 6.", None

        # Check existing student ID
        existing = self.db.get_student_by_id(student_id)
        if existing:
            return False, f"Duplicate Error: Student ID '{student_id}' is already registered.", None

        # Generate secure random token
        qr_token = self.qr_manager.generate_token()

        # Save to DB
        success, msg, student_db_id = self.db.add_student(
            student_id=student_id,
            full_name=full_name,
            department=department,
            year=int(year),
            section=section,
            qr_token=qr_token
        )

        if not success:
            return False, msg, None

        # Generate QR code image
        qr_path = self.qr_manager.generate_qr_image(qr_token, student_id)

        student_data = {
            "id": student_db_id,
            "student_id": student_id.upper(),
            "full_name": full_name,
            "department": department.upper(),
            "year": int(year),
            "section": section.upper(),
            "qr_token": qr_token,
            "qr_image_path": str(qr_path),
            "is_enrolled": False
        }

        return True, "Student registered and QR code generated.", student_data

    def verify_qr(self, qr_token: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Decodes and verifies a QR token against registered students.
        """
        if not qr_token or not qr_token.strip():
            return False, "INVALID: Empty QR token.", None

        student = self.db.get_student_by_qr(qr_token)
        if not student:
            return False, "INVALID: QR code is not recognized or unregistered.", None

        return True, "VERIFIED: Student identity confirmed.", student

    def store_face_embeddings(
        self,
        student_db_id: int,
        embeddings_list: List[np.ndarray]
    ) -> Tuple[bool, str]:
        """
        Combines multiple face sample embeddings into a master normalized embedding
        and stores it in the local database.
        """
        if not embeddings_list or len(embeddings_list) == 0:
            return False, "Error: No face embeddings captured."

        # Compute average feature vector across sample poses
        stacked = np.stack(embeddings_list, axis=0) # shape (N, 128)
        mean_embedding = np.mean(stacked, axis=0)
        
        # L2-normalize
        norm = np.linalg.norm(mean_embedding)
        if norm > 0:
            master_embedding = mean_embedding / norm
        else:
            master_embedding = mean_embedding

        # Save to SQLite
        success, msg = self.db.save_face_embedding(
            student_db_id=student_db_id,
            embedding=master_embedding,
            sample_count=len(embeddings_list)
        )
        return success, msg
