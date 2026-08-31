"""
SmartAttend-AI: Centralized Security Configuration (Step 8)
===========================================================
Defines rate limits, suspicious activity thresholds, audit settings,
and verification tolerances.
"""

from dataclasses import dataclass


@dataclass
class SecurityConfig:
    """Centralized security configuration parameters."""
    max_failed_attempts: int = 3             # Failed attempts before triggering SUSPICIOUS_ACTIVITY flag
    rate_limit_window_seconds: int = 60      # Rolling time window to track failed attempts
    suspicious_activity_threshold: int = 3   # Mismatches or spoof attempts before escalating severity to HIGH
    recognition_threshold: float = 0.60      # SFace cosine similarity threshold
    liveness_threshold: float = 0.65         # Liveness composite score threshold
    liveness_min_confidence: float = 0.70    # Minimum liveness decision confidence
    enable_audit_logging: bool = True        # Enable database security audit logging
    replay_token_expiry_seconds: int = 300   # Verification ticket validity window (5 mins)


# Default global instance
DEFAULT_SECURITY_CONFIG = SecurityConfig()
