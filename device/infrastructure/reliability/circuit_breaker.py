"""Circuit breaker implementation for protecting outbound HTTP calls.

Provides a simple state machine (CLOSED -> OPEN -> HALF_OPEN) that rejects
calls when the downstream service is unhealthy, preventing cascade failures.
"""

import threading
import time
from typing import Callable, Optional, TypeVar

T = TypeVar("T")


class CircuitBreakerOpenException(Exception):
    """Raised when the circuit breaker is OPEN and rejects the call."""
    pass


class CircuitBreaker:
    """Simple thread-safe circuit breaker.

    States:
        CLOSED  — Normal operation; failures are counted.
        OPEN    — Threshold exceeded; calls are rejected fast.
        HALF_OPEN — Recovery timeout elapsed; one probe call allowed.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    def call(self, fn: Callable[..., T], *args, **kwargs) -> T:
        """Execute fn if the circuit allows it.

        Args:
            fn: Callable to protect.
            *args, **kwargs: Arguments for fn.

        Returns:
            Result of fn.

        Raises:
            CircuitBreakerOpenException: If the circuit is OPEN.
            Exception: Any exception raised by fn (counts as failure).
        """
        with self._lock:
            if self._state == self.OPEN:
                if time.time() - self._last_failure_time > self.recovery_timeout:
                    self._state = self.HALF_OPEN
                else:
                    raise CircuitBreakerOpenException("Circuit breaker is OPEN")

        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise exc

    def _on_success(self) -> None:
        with self._lock:
            if self._state == self.HALF_OPEN:
                self._state = self.CLOSED
            self._failure_count = 0

    def _on_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == self.HALF_OPEN:
                self._state = self.OPEN
            elif self._failure_count >= self.failure_threshold:
                self._state = self.OPEN

    @property
    def state(self) -> str:
        return self._state
