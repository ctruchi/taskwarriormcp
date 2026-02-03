"""Metrics collection and monitoring for TaskWarrior MCP server."""

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Generator


@dataclass
class OperationMetrics:
    """Metrics for a specific operation."""
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration_seconds: float = 0.0
    min_duration_seconds: float | None = None
    max_duration_seconds: float | None = None

    def record_success(self, duration: float) -> None:
        """Record a successful operation.

        Args:
            duration: Operation duration in seconds
        """
        self.total_count += 1
        self.success_count += 1
        self.total_duration_seconds += duration

        if self.min_duration_seconds is None or duration < self.min_duration_seconds:
            self.min_duration_seconds = duration
        if self.max_duration_seconds is None or duration > self.max_duration_seconds:
            self.max_duration_seconds = duration

    def record_failure(self, duration: float) -> None:
        """Record a failed operation.

        Args:
            duration: Operation duration in seconds
        """
        self.total_count += 1
        self.failure_count += 1
        self.total_duration_seconds += duration

        if self.min_duration_seconds is None or duration < self.min_duration_seconds:
            self.min_duration_seconds = duration
        if self.max_duration_seconds is None or duration > self.max_duration_seconds:
            self.max_duration_seconds = duration

    def get_average_duration(self) -> float:
        """Get average operation duration.

        Returns:
            Average duration in seconds
        """
        if self.total_count == 0:
            return 0.0
        return self.total_duration_seconds / self.total_count

    def get_success_rate(self) -> float:
        """Get success rate as a percentage.

        Returns:
            Success rate (0-100)
        """
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary.

        Returns:
            Dictionary representation of metrics
        """
        return {
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_duration_seconds": round(self.total_duration_seconds, 4),
            "average_duration_seconds": round(self.get_average_duration(), 4),
            "min_duration_seconds": round(self.min_duration_seconds, 4) if self.min_duration_seconds else None,
            "max_duration_seconds": round(self.max_duration_seconds, 4) if self.max_duration_seconds else None,
            "success_rate_percent": round(self.get_success_rate(), 2)
        }


class MetricsCollector:
    """Thread-safe metrics collector for TaskWarrior MCP operations."""

    def __init__(self):
        """Initialize metrics collector."""
        self._lock = Lock()
        self._operation_metrics: dict[str, OperationMetrics] = defaultdict(OperationMetrics)
        self._sync_metrics = OperationMetrics()
        self._error_counts: dict[str, int] = defaultdict(int)
        self._start_time = time.time()

    @contextmanager
    def track_operation(self, operation_name: str) -> Generator[None, None, None]:
        """Context manager to track operation duration and status.

        Args:
            operation_name: Name of the operation being tracked

        Yields:
            None

        Example:
            with metrics.track_operation("list_tasks"):
                result = do_something()
        """
        start_time = time.time()
        error_occurred = False

        try:
            yield
        except Exception as e:
            error_occurred = True
            # Record error type
            error_type = type(e).__name__
            with self._lock:
                self._error_counts[error_type] += 1
            raise
        finally:
            duration = time.time() - start_time
            with self._lock:
                if error_occurred:
                    self._operation_metrics[operation_name].record_failure(duration)
                else:
                    self._operation_metrics[operation_name].record_success(duration)

    @contextmanager
    def track_sync(self) -> Generator[None, None, None]:
        """Context manager to track sync operation duration and status.

        Yields:
            None

        Example:
            with metrics.track_sync():
                sync_operation()
        """
        start_time = time.time()
        error_occurred = False

        try:
            yield
        except Exception as e:
            error_occurred = True
            # Record error type
            error_type = type(e).__name__
            with self._lock:
                self._error_counts[error_type] += 1
            raise
        finally:
            duration = time.time() - start_time
            with self._lock:
                if error_occurred:
                    self._sync_metrics.record_failure(duration)
                else:
                    self._sync_metrics.record_success(duration)

    def record_error(self, error_type: str) -> None:
        """Record an error occurrence.

        Args:
            error_type: Type/name of the error
        """
        with self._lock:
            self._error_counts[error_type] += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get all collected metrics.

        Returns:
            Dictionary containing all metrics
        """
        with self._lock:
            uptime_seconds = time.time() - self._start_time

            return {
                "uptime_seconds": round(uptime_seconds, 2),
                "operations": {
                    name: metrics.to_dict()
                    for name, metrics in self._operation_metrics.items()
                },
                "sync": self._sync_metrics.to_dict(),
                "errors_by_type": dict(self._error_counts),
                "total_errors": sum(self._error_counts.values())
            }

    def get_operation_metrics(self, operation_name: str) -> dict[str, Any]:
        """Get metrics for a specific operation.

        Args:
            operation_name: Name of the operation

        Returns:
            Dictionary containing operation metrics
        """
        with self._lock:
            if operation_name in self._operation_metrics:
                return self._operation_metrics[operation_name].to_dict()
            return OperationMetrics().to_dict()

    def get_sync_metrics(self) -> dict[str, Any]:
        """Get sync operation metrics.

        Returns:
            Dictionary containing sync metrics
        """
        with self._lock:
            return self._sync_metrics.to_dict()

    def get_error_metrics(self) -> dict[str, Any]:
        """Get error metrics.

        Returns:
            Dictionary containing error counts by type
        """
        with self._lock:
            return {
                "errors_by_type": dict(self._error_counts),
                "total_errors": sum(self._error_counts.values())
            }

    def reset(self) -> None:
        """Reset all metrics.

        Useful for testing or starting fresh metrics collection.
        """
        with self._lock:
            self._operation_metrics.clear()
            self._sync_metrics = OperationMetrics()
            self._error_counts.clear()
            self._start_time = time.time()


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
