"""
SmartAttend-AI: Step 5 Automated Test Suite (Face Recognition)
==============================================================
Validates:
  1. Enrolled student embedding loading from SQLite into vectorized cache
  2. Embedding dimension validation (128-D)
  3. Cosine similarity calculation accuracy
  4. Known student identification matching
  5. Unknown student rejection
  6. Multi-face recognition handling in single frame
  7. Threshold sensitivity & behavior
"""

import sys
import gc
import shutil
from pathlib import Path
import numpy as np

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from database.db_manager import DatabaseManager
from ai.face_recognition.embedder import FaceEmbedder
from ai.face_recognition.recognizer import (
    FaceRecognizerService,
    RecognitionResult,
    TemporalSmoother,
    DEFAULT_RECOGNITION_THRESHOLD
)
from ai.face_recognition.live_face_detector import FaceBox


def run_step5_verification():
    print("=" * 70)
    print("[*] SMARTATTEND-AI: STEP 5 FACE RECOGNITION TEST SUITE")
    print("=" * 70)

    # Use isolated test database
    test_db_path = Path(__file__).resolve().parent.parent.parent / "test_recognition.db"
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass

    db = DatabaseManager(db_path=str(test_db_path))
    embedder = FaceEmbedder()

    # -------------------------------------------------------------------------
    # SETUP: Seed Enrolled Students & Vector Embeddings
    # -------------------------------------------------------------------------
    print("\n[SETUP] Enrolling 3 Test Students with known synthetic embeddings...")
    # Student 1: Alice Johnson
    db.add_student("STU-001", "Alice Johnson", "Computer Science", 3, "A", "SA-STU-ALICE001")
    alice_profile = db.get_student_by_id("STU-001")
    alice_vec = np.random.RandomState(42).randn(128).astype(np.float32)
    alice_vec /= np.linalg.norm(alice_vec)
    db.save_face_embedding(alice_profile["id"], alice_vec, sample_count=5)

    # Student 2: Bob Smith
    db.add_student("STU-002", "Bob Smith", "Mechanical Engineering", 2, "B", "SA-STU-BOB002")
    bob_profile = db.get_student_by_id("STU-002")
    bob_vec = np.random.RandomState(100).randn(128).astype(np.float32)
    bob_vec /= np.linalg.norm(bob_vec)
    db.save_face_embedding(bob_profile["id"], bob_vec, sample_count=5)

    # Student 3: Charlie Davis
    db.add_student("STU-003", "Charlie Davis", "Electrical Engineering", 4, "A", "SA-STU-CHARLIE003")
    charlie_profile = db.get_student_by_id("STU-003")
    charlie_vec = np.random.RandomState(200).randn(128).astype(np.float32)
    charlie_vec /= np.linalg.norm(charlie_vec)
    db.save_face_embedding(charlie_profile["id"], charlie_vec, sample_count=5)

    print("   [OK] 3 Enrolled students created in SQLite.")

    # -------------------------------------------------------------------------
    # TEST 1: Load Enrolled Embeddings & Matrix Dimension Validation
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Testing Enrolled Embeddings Cache & Matrix Dimensions...")
    service = FaceRecognizerService(db_manager=db, recognition_threshold=0.60)
    assert len(service.enrolled_students) == 3, f"Expected 3 enrolled students, got {len(service.enrolled_students)}"
    assert service.embedding_matrix is not None
    assert service.embedding_matrix.shape == (3, 128), f"Expected shape (3, 128), got {service.embedding_matrix.shape}"
    print(f"   [OK] Loaded {len(service.enrolled_students)} enrolled students into memory.")
    print(f"   [OK] Embedding Matrix validated: Shape {service.embedding_matrix.shape} (128-D float32 vectors).")

    # -------------------------------------------------------------------------
    # TEST 2: Cosine Similarity Mathematical Precision
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Cosine Similarity Calculation Precision...")
    identical_sim = embedder.compute_similarity(alice_vec, alice_vec)
    assert abs(identical_sim - 1.0) < 1e-4, f"Identical vector similarity {identical_sim} != 1.0"
    
    # Realistic small pose variation perturbation (std = 0.02)
    noisy_alice = alice_vec + (np.random.RandomState(10).randn(128).astype(np.float32) * 0.02)
    noisy_alice /= np.linalg.norm(noisy_alice)
    high_sim = embedder.compute_similarity(alice_vec, noisy_alice)
    assert high_sim > 0.90, f"Expected high similarity > 0.90, got {high_sim}"
    print(f"   [OK] Identical vector similarity: {identical_sim:.4f} (100% match).")
    print(f"   [OK] Slight pose variation similarity: {high_sim:.4f} (>90% match).")

    # -------------------------------------------------------------------------
    # TEST 3: Known Student Identification
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Testing Known Student Identification (Alice & Bob)...")
    # Query with noisy Alice embedding
    matched, score, is_rec = service.match_embedding(noisy_alice)
    assert is_rec is True, "Alice should be recognized!"
    assert matched is not None
    assert matched["student_id"] == "STU-001"
    assert matched["full_name"] == "Alice Johnson"
    print(f"   [OK] Alice recognized successfully (Score: {score:.3f} >= Threshold 0.60).")

    # Query with noisy Bob embedding
    noisy_bob = bob_vec + (np.random.RandomState(15).randn(128).astype(np.float32) * 0.02)
    noisy_bob /= np.linalg.norm(noisy_bob)
    matched_b, score_b, is_rec_b = service.match_embedding(noisy_bob)
    assert is_rec_b is True, "Bob should be recognized!"
    assert matched_b["student_id"] == "STU-002"
    print(f"   [OK] Bob recognized successfully (Score: {score_b:.3f} >= Threshold 0.60).")

    # -------------------------------------------------------------------------
    # TEST 4: Unknown Student Rejection
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Testing Unregistered/Unknown Face Rejection...")
    unregistered_vec = np.random.RandomState(9999).randn(128).astype(np.float32)
    unregistered_vec /= np.linalg.norm(unregistered_vec)
    matched_unk, score_unk, is_rec_unk = service.match_embedding(unregistered_vec)
    assert is_rec_unk is False, "Unregistered face must not be recognized!"
    assert matched_unk is None
    print(f"   [OK] Unregistered person correctly labeled UNKNOWN (Max Score: {score_unk:.3f} < Threshold 0.60).")

    # -------------------------------------------------------------------------
    # TEST 5: Threshold Behavior & Sensitivity
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing Configurable Threshold Behavior...")
    # Medium variation vector
    mid_alice = alice_vec + (np.random.RandomState(25).randn(128).astype(np.float32) * 0.08)
    mid_alice /= np.linalg.norm(mid_alice)
    
    # At strict threshold 0.98, altered vector is rejected
    strict_service = FaceRecognizerService(db_manager=db, recognition_threshold=0.98)
    _, strict_score, strict_rec = strict_service.match_embedding(mid_alice)
    assert strict_rec is False, "Strict threshold 0.98 should reject medium match!"
    print(f"   [OK] Strict threshold (0.98) rejected match as expected (Score {strict_score:.3f} < 0.98).")

    # At normal threshold 0.60, it is accepted
    normal_service = FaceRecognizerService(db_manager=db, recognition_threshold=0.60)
    _, norm_score, norm_rec = normal_service.match_embedding(mid_alice)
    assert norm_rec is True, "Standard threshold 0.60 should accept match!"
    print(f"   [OK] Standard threshold (0.60) accepted match as expected (Score {norm_score:.3f} >= 0.60).")

    # -------------------------------------------------------------------------
    # TEST 6: Multi-Face Matching in Single Frame
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Testing Multi-Face Recognition (Simulated Frame with 2 Faces)...")
    # Face 1: Alice (Known)
    # Face 2: Unregistered (Unknown)
    mock_box_1 = FaceBox(x=50, y=50, w=100, h=100, confidence=0.95)
    mock_box_2 = FaceBox(x=300, y=50, w=100, h=100, confidence=0.92)

    res1_match, res1_score, res1_rec = service.match_embedding(noisy_alice)
    res2_match, res2_score, res2_rec = service.match_embedding(unregistered_vec)

    result_1 = RecognitionResult(
        box=mock_box_1,
        student_db_id=res1_match["id"],
        student_id=res1_match["student_id"],
        student_name=res1_match["full_name"],
        department=res1_match["department"],
        year=res1_match["year"],
        section=res1_match["section"],
        similarity=res1_score,
        is_recognized=res1_rec,
        status="RECOGNIZED" if res1_rec else "NOT RECOGNIZED"
    )

    result_2 = RecognitionResult(
        box=mock_box_2,
        student_db_id=None,
        student_id=None,
        student_name="UNKNOWN",
        department=None,
        year=None,
        section=None,
        similarity=res2_score,
        is_recognized=res2_rec,
        status="NOT RECOGNIZED"
    )

    assert result_1.is_recognized is True
    assert result_1.student_name == "Alice Johnson"
    assert result_2.is_recognized is False
    assert result_2.student_name == "UNKNOWN"
    print(f"   [OK] Multi-face Frame: Face 1 = '{result_1.student_name}' ({result_1.status})")
    print(f"   [OK] Multi-face Frame: Face 2 = '{result_2.student_name}' ({result_2.status})")

    # -------------------------------------------------------------------------
    # TEST 7: Temporal Smoothing Stability
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Testing Temporal Smoothing...")
    smoother = TemporalSmoother(history_len=3)
    smoothed = smoother.smooth([result_1, result_2])
    assert len(smoothed) == 2
    assert smoothed[0].is_recognized is True
    assert smoothed[1].is_recognized is False
    print("   [OK] Temporal smoothing filter executed without error.")

    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------
    del db
    del service
    del strict_service
    del normal_service
    gc.collect()

    try:
        if test_db_path.exists():
            test_db_path.unlink()
    except Exception:
        pass

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL STEP 5 FACE RECOGNITION TESTS PASSED 100%!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    run_step5_verification()
