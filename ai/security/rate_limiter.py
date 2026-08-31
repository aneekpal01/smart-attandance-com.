"""
SmartAttend-AI: Rate Limiting & Suspicious Activity Detector (Step 8)
====================================================================
Tracks consecutive failed verification attempts within rolling time windows
to detect brute-force scans, repeated identity mismatches, and spoof attempts.
"""

import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from ai.security.config import SecurityConfig, DEFAULT_SECURITY_CONFIG


class RateLimiter:
    """
    In-memory rolling window rate limiter and suspicious pattern monitor.
    Tracks failure events per session and per student.
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or DEFAULT_SECURITY_CONFIG
        # Key: (session_id, identifier_str), Value: List of timestamps (float)
        self.failure_history: Dict[Tuple[int, str], List[float]] = defaultdict(list)

    def record_failure(self, session_id: int, identifier: str) -> Tuple[bool, int]:
        """
        Records a failed attempt (mismatch, invalid QR, spoof, unknown).
        
        Returns:
            (is_suspicious_flagged_bool, current_failure_count)
        """
        now = time.time()
        key = (session_id, str(identifier))
        
        # Clean older timestamps outside the rate limit window
        window_start = now - self.config.rate_limit_window_seconds
        self.failure_history[key] = [t for t in self.failure_history[key] if t >= window_start]

        # Add current timestamp
        self.failure_history[key].append(now)
        count = len(self.failure_history[key])

        is_suspicious = count >= self.config.max_failed_attempts
        return is_suspicious, count

    def reset(self, session_id: int, identifier: str) -> None:
        """Resets failure count upon successful verification."""
        key = (session_id, str(identifier))
        if key in self.failure_history:
            del self.failure_history[key]

    def clear_all(self) -> None:
        """Clears entire history."""
        self.failure_history.clear()
