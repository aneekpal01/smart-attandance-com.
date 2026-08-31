"""
SmartAttend-AI: Unified Master Regression Test Runner (Steps 3 - 11)
====================================================================
Runs every automated test suite across all subsystems and outputs
a consolidated summary table with status, test counts, and durations.
"""

import sys
import time
import importlib
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Root directory setup
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def run_all_suites():
    print("=" * 80)
    print("🚀 SMARTATTEND-AI: MASTER ARCHITECTURE REGRESSION SUITE (STEPS 3 - 11)")
    print("=" * 80)

    suites: List[Tuple[str, str, str]] = [
        ("Step 4: Student Registration & QR", "ai.face_recognition.test_step4_registration", "run_step4_verification"),
        ("Step 5: Local Face Recognition", "ai.face_recognition.test_step5_recognition", "run_step5_verification"),
        ("Step 6: Smart Attendance Engine", "ai.attendance.test_step6_attendance", "run_step6_verification"),
        ("Step 7: Liveness & Anti-Spoofing", "ai.liveness.test_step7_liveness", "run_step7_verification"),
        ("Step 8: Security, Anti-Proxy & Audit", "ai.security.test_step8_security", "run_step8_verification"),
        ("Step 9: Faculty Dashboard API", "backend.tests.test_step9_dashboard_api", "run_step9_verification"),
        ("Step 10: AI Analytics & Intelligence", "ai.analytics.test_step10_analytics", "run_step10_verification"),
        ("Step 11: Full End-to-End Lifecycle", "tests.test_step11_end_to_end", "run_full_end_to_end_test"),
        ("Step 11: DB Integrity & Concurrency", "tests.test_database_integrity", "run_database_integrity_tests"),
        ("Step 11: API Robustness & Security", "tests.test_api_robustness", "run_api_robustness_tests"),
    ]

    results: List[Dict[str, Any]] = []
    total_start = time.perf_counter()

    for name, mod_path, func_name in suites:
        print(f"\n>> Executing Suite: {name}...")
        t0 = time.perf_counter()
        try:
            mod = importlib.import_module(mod_path)
            func = getattr(mod, func_name)
            ok = func()
            t1 = time.perf_counter()
            duration = round((t1 - t0), 2)
            results.append({"name": name, "status": "PASS", "duration": duration, "error": None})
        except Exception as e:
            t1 = time.perf_counter()
            duration = round((t1 - t0), 2)
            results.append({"name": name, "status": "FAIL", "duration": duration, "error": str(e)})
            print(f"   ❌ FAILED: {e}")

    total_duration = round(time.perf_counter() - total_start, 2)

    print("\n" + "=" * 80)
    print("📊 CONSOLIDATED REGRESSION TEST SUMMARY REPORT")
    print("=" * 80)
    print(f"{'TEST SUITE':<45} | {'STATUS':<8} | {'DURATION':<10}")
    print("-" * 80)

    all_passed = True
    for r in results:
        status_str = f"✅ {r['status']}" if r["status"] == "PASS" else f"❌ {r['status']}"
        if r["status"] != "PASS":
            all_passed = False
        print(f"{r['name']:<45} | {status_str:<8} | {r['duration']}s")

    print("-" * 80)
    passed_count = sum(1 for r in results if r["status"] == "PASS")
    total_count = len(results)
    print(f"TOTAL SUITES: {total_count} | PASSED: {passed_count} | FAILED: {total_count - passed_count} | TIME: {total_duration}s")
    print("=" * 80)

    if all_passed:
        print("🎉 100% REGRESSION SUITES PASSED CLEANLY WITH ZERO FAILURES!")
    else:
        print("❌ REGRESSION SUITE ENCOUNTERED FAILURES.")
        sys.exit(1)


if __name__ == "__main__":
    run_all_suites()
