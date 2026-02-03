"""Tests for metrics collection system."""

import time
from unittest.mock import Mock

import pytest

from taskwarriormcp.metrics import MetricsCollector, OperationMetrics, get_metrics_collector


class TestOperationMetrics:
    """Tests for OperationMetrics class."""

    def test_initial_state(self):
        """Test initial state of metrics."""
        metrics = OperationMetrics()
        assert metrics.total_count == 0
        assert metrics.success_count == 0
        assert metrics.failure_count == 0
        assert metrics.total_duration_seconds == 0.0
        assert metrics.min_duration_seconds is None
        assert metrics.max_duration_seconds is None

    def test_record_success(self):
        """Test recording successful operations."""
        metrics = OperationMetrics()
        metrics.record_success(0.5)
        metrics.record_success(1.0)
        metrics.record_success(0.75)

        assert metrics.total_count == 3
        assert metrics.success_count == 3
        assert metrics.failure_count == 0
        assert metrics.total_duration_seconds == 2.25
        assert metrics.min_duration_seconds == 0.5
        assert metrics.max_duration_seconds == 1.0
        assert metrics.get_average_duration() == 0.75
        assert metrics.get_success_rate() == 100.0

    def test_record_failure(self):
        """Test recording failed operations."""
        metrics = OperationMetrics()
        metrics.record_failure(0.3)
        metrics.record_failure(0.6)

        assert metrics.total_count == 2
        assert metrics.success_count == 0
        assert metrics.failure_count == 2
        assert abs(metrics.total_duration_seconds - 0.9) < 0.0001
        assert metrics.min_duration_seconds == 0.3
        assert metrics.max_duration_seconds == 0.6
        assert abs(metrics.get_average_duration() - 0.45) < 0.0001
        assert metrics.get_success_rate() == 0.0

    def test_mixed_results(self):
        """Test recording mix of successes and failures."""
        metrics = OperationMetrics()
        metrics.record_success(1.0)
        metrics.record_failure(0.5)
        metrics.record_success(0.8)
        metrics.record_failure(0.6)

        assert metrics.total_count == 4
        assert metrics.success_count == 2
        assert metrics.failure_count == 2
        assert metrics.get_success_rate() == 50.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = OperationMetrics()
        metrics.record_success(1.0)
        metrics.record_failure(0.5)

        data = metrics.to_dict()
        assert isinstance(data, dict)
        assert data["total_count"] == 2
        assert data["success_count"] == 1
        assert data["failure_count"] == 1
        assert "average_duration_seconds" in data
        assert "success_rate_percent" in data


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_track_operation_success(self):
        """Test tracking successful operation."""
        collector = MetricsCollector()

        with collector.track_operation("test_op"):
            time.sleep(0.01)  # Small delay to measure

        metrics = collector.get_operation_metrics("test_op")
        assert metrics["total_count"] == 1
        assert metrics["success_count"] == 1
        assert metrics["failure_count"] == 0
        assert metrics["average_duration_seconds"] > 0

    def test_track_operation_failure(self):
        """Test tracking failed operation."""
        collector = MetricsCollector()

        with pytest.raises(ValueError):
            with collector.track_operation("test_op"):
                raise ValueError("Test error")

        metrics = collector.get_operation_metrics("test_op")
        assert metrics["total_count"] == 1
        assert metrics["success_count"] == 0
        assert metrics["failure_count"] == 1

        error_metrics = collector.get_error_metrics()
        assert error_metrics["errors_by_type"]["ValueError"] == 1
        assert error_metrics["total_errors"] == 1

    def test_track_multiple_operations(self):
        """Test tracking multiple different operations."""
        collector = MetricsCollector()

        with collector.track_operation("op1"):
            pass

        with collector.track_operation("op2"):
            pass

        with collector.track_operation("op1"):
            pass

        op1_metrics = collector.get_operation_metrics("op1")
        op2_metrics = collector.get_operation_metrics("op2")

        assert op1_metrics["total_count"] == 2
        assert op2_metrics["total_count"] == 1

    def test_track_sync_success(self):
        """Test tracking successful sync."""
        collector = MetricsCollector()

        with collector.track_sync():
            time.sleep(0.01)

        sync_metrics = collector.get_sync_metrics()
        assert sync_metrics["total_count"] == 1
        assert sync_metrics["success_count"] == 1
        assert sync_metrics["failure_count"] == 0

    def test_track_sync_failure(self):
        """Test tracking failed sync."""
        collector = MetricsCollector()

        with pytest.raises(RuntimeError):
            with collector.track_sync():
                raise RuntimeError("Sync failed")

        sync_metrics = collector.get_sync_metrics()
        assert sync_metrics["total_count"] == 1
        assert sync_metrics["success_count"] == 0
        assert sync_metrics["failure_count"] == 1

        error_metrics = collector.get_error_metrics()
        assert error_metrics["errors_by_type"]["RuntimeError"] == 1

    def test_record_error(self):
        """Test manual error recording."""
        collector = MetricsCollector()

        collector.record_error("CustomError")
        collector.record_error("CustomError")
        collector.record_error("AnotherError")

        error_metrics = collector.get_error_metrics()
        assert error_metrics["errors_by_type"]["CustomError"] == 2
        assert error_metrics["errors_by_type"]["AnotherError"] == 1
        assert error_metrics["total_errors"] == 3

    def test_get_metrics(self):
        """Test getting all metrics."""
        collector = MetricsCollector()

        # Perform some operations
        with collector.track_operation("op1"):
            pass

        with collector.track_sync():
            pass

        collector.record_error("TestError")

        all_metrics = collector.get_metrics()

        assert "uptime_seconds" in all_metrics
        assert "operations" in all_metrics
        assert "sync" in all_metrics
        assert "errors_by_type" in all_metrics
        assert "total_errors" in all_metrics

        assert "op1" in all_metrics["operations"]
        assert all_metrics["errors_by_type"]["TestError"] == 1

    def test_reset(self):
        """Test resetting metrics."""
        collector = MetricsCollector()

        # Add some metrics
        with collector.track_operation("test"):
            pass
        collector.record_error("TestError")

        # Reset
        collector.reset()

        # Verify everything is cleared
        metrics = collector.get_metrics()
        assert len(metrics["operations"]) == 0
        assert metrics["sync"]["total_count"] == 0
        assert metrics["total_errors"] == 0

    def test_thread_safety(self):
        """Test that metrics collection is thread-safe."""
        import threading

        collector = MetricsCollector()
        num_threads = 10
        ops_per_thread = 20

        def worker():
            for _ in range(ops_per_thread):
                with collector.track_operation("concurrent_op"):
                    pass

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        metrics = collector.get_operation_metrics("concurrent_op")
        assert metrics["total_count"] == num_threads * ops_per_thread
        assert metrics["success_count"] == num_threads * ops_per_thread


class TestGlobalMetricsCollector:
    """Tests for global metrics collector singleton."""

    def test_get_metrics_collector_singleton(self):
        """Test that get_metrics_collector returns same instance."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2

    def test_global_collector_persistence(self):
        """Test that metrics persist across get_metrics_collector calls."""
        collector1 = get_metrics_collector()
        with collector1.track_operation("test"):
            pass

        collector2 = get_metrics_collector()
        metrics = collector2.get_operation_metrics("test")

        assert metrics["total_count"] == 1
