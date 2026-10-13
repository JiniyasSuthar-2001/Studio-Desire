import time
import threading
from typing import Dict, List
from fastapi import Request, HTTPException, status
from app.core.config import settings


class InMemoryRateLimiter:
    """
    Sliding window in-memory rate limiter with thread safety.
    """
    def __init__(self):
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check_rate_limit(self, client_ip: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            timestamps = self._requests.get(client_ip, [])
            # Filter timestamps within window
            timestamps = [t for t in timestamps if now - t < window_seconds]
            if len(timestamps) >= max_requests:
                self._requests[client_ip] = timestamps
                return False
            timestamps.append(now)
            self._requests[client_ip] = timestamps
            return True

    def is_allowed(self, client_ip: str, max_requests: int, window_seconds: int) -> bool:
        return self.check_rate_limit(client_ip, max_requests, window_seconds)


rate_limiter = InMemoryRateLimiter()


def enforce_enquiry_rate_limit(request: Request):
    """
    Enforces rate limits on public submission endpoints based on client IP.
    """
    # Extract client IP
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    limit = settings.ENQUIRY_RATE_LIMIT
    window = settings.ENQUIRY_RATE_WINDOW_SECONDS

    if not rate_limiter.check_rate_limit(client_ip, limit, window):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a few minutes before submitting another enquiry."
        )
