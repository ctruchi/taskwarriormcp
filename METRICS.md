# Metrics & Monitoring

The TaskWarrior MCP server includes a built-in metrics collection system that tracks operations, performance, and errors.

## Metrics Collected

The metrics system tracks:

### 1. Operation Metrics
For each MCP tool (list_tasks, add_task, edit_task, list_project_tasks):
- Total operation count
- Success/failure counts
- Success rate percentage
- Operation durations (total, average, min, max)

### 2. Sync Metrics
- Total sync operations
- Success/failure counts
- Success rate percentage
- Sync durations (total, average, min, max)

### 3. Error Metrics
- Error counts by exception type
- Total error count

### 4. Server Metrics
- Server uptime in seconds

## Accessing Metrics

### Via MCP Tool

Use the `get_metrics` MCP tool to retrieve all collected metrics:

```python
# Call the get_metrics tool
get_metrics()

# Returns JSON with comprehensive metrics
{
  "success": true,
  "metrics": {
    "uptime_seconds": 123.45,
    "operations": {
      "list_tasks": {
        "total_count": 10,
        "success_count": 10,
        "failure_count": 0,
        "total_duration_seconds": 5.2341,
        "average_duration_seconds": 0.5234,
        "min_duration_seconds": 0.4123,
        "max_duration_seconds": 0.7234,
        "success_rate_percent": 100.0
      },
      "add_task": {
        "total_count": 5,
        "success_count": 4,
        "failure_count": 1,
        "average_duration_seconds": 0.6123,
        "success_rate_percent": 80.0,
        ...
      }
    },
    "sync": {
      "total_count": 20,
      "success_count": 18,
      "failure_count": 2,
      "average_duration_seconds": 0.1234,
      "success_rate_percent": 90.0,
      ...
    },
    "errors_by_type": {
      "TaskWarriorCommandError": 2,
      "TaskWarriorSyncError": 1,
      "ValueError": 1
    },
    "total_errors": 4
  }
}
```

### Programmatic Access

You can also access metrics programmatically in Python:

```python
from taskwarriormcp.metrics import get_metrics_collector

metrics = get_metrics_collector()

# Get all metrics
all_metrics = metrics.get_metrics()

# Get specific operation metrics
list_tasks_metrics = metrics.get_operation_metrics("list_tasks")
print(f"Success rate: {list_tasks_metrics['success_rate_percent']}%")

# Get sync metrics
sync_metrics = metrics.get_sync_metrics()
print(f"Sync operations: {sync_metrics['total_count']}")

# Get error metrics
error_metrics = metrics.get_error_metrics()
print(f"Total errors: {error_metrics['total_errors']}")
```

## Implementation Details

### MetricsCollector Class

The `MetricsCollector` class provides the main metrics collection functionality:

```python
from taskwarriormcp.metrics import MetricsCollector

collector = MetricsCollector()

# Track an operation
with collector.track_operation("my_operation"):
    # Your code here
    pass

# Track a sync operation
with collector.track_sync():
    # Sync code here
    pass

# Manually record an error
collector.record_error("CustomErrorType")

# Reset all metrics
collector.reset()
```

### Context Managers

The metrics system uses context managers to automatically track operation duration and success/failure:

```python
# Successful operation
with metrics.track_operation("list_tasks"):
    tasks = get_tasks()  # Operation succeeds
    # Metrics automatically record success and duration

# Failed operation
with metrics.track_operation("add_task"):
    raise ValueError("Invalid input")  # Operation fails
    # Metrics automatically record failure, duration, and error type
```

### Thread Safety

The `MetricsCollector` is thread-safe and uses locks to ensure correct operation in concurrent environments. Multiple threads can safely call metrics methods simultaneously.

### Global Singleton

The metrics system uses a global singleton pattern accessed via `get_metrics_collector()`:

```python
from taskwarriormcp.metrics import get_metrics_collector

# Always returns the same instance
collector1 = get_metrics_collector()
collector2 = get_metrics_collector()
assert collector1 is collector2  # True
```

## Example Usage

See `examples/metrics_example.py` for a complete example demonstrating the metrics system:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the metrics example
python examples/metrics_example.py
```

The example demonstrates:
- Simulating various operations
- Tracking successes and failures
- Recording errors
- Retrieving and displaying metrics
- JSON export of metrics

## Testing

The metrics system includes comprehensive tests in `src/tests/test_metrics.py`:

```bash
# Run metrics tests
pytest src/tests/test_metrics.py -v
```

Tests cover:
- Operation tracking (success/failure)
- Sync tracking
- Error recording
- Thread safety
- Metric calculations (averages, success rates, etc.)
- Global singleton behavior

## Future Enhancements

### Prometheus Integration

The current metrics system uses in-memory storage. It can be extended to export metrics to Prometheus:

1. Install the `prometheus-client` package:
   ```bash
   pip install prometheus-client
   ```

2. Create Prometheus metric objects:
   ```python
   from prometheus_client import Counter, Histogram

   operation_counter = Counter(
       'taskwarrior_operations_total',
       'Total operations',
       ['operation', 'status']
   )

   operation_duration = Histogram(
       'taskwarrior_operation_duration_seconds',
       'Operation duration',
       ['operation']
   )
   ```

3. Update `MetricsCollector` to push metrics to Prometheus

4. Expose a `/metrics` endpoint for Prometheus scraping

### Additional Metrics

Potential additional metrics to track:
- Task counts by status (pending, completed, deleted)
- Task counts by project
- Most frequently used operations
- Peak operation times
- Resource usage (memory, CPU)
- Queue depths (if implementing async processing)

### Metric Retention

Currently, metrics are stored in-memory and reset on server restart. For production use, consider:
- Persisting metrics to disk
- Implementing metric rotation
- Configurable retention periods
- Metric aggregation for historical data

### Alerting

Future enhancements could include:
- Threshold-based alerts (e.g., sync failure rate > 10%)
- Webhook notifications
- Email alerts
- Integration with monitoring platforms (PagerDuty, Opsgenie, etc.)

## Best Practices

1. **Monitor Sync Failures**: High sync failure rates indicate connectivity or configuration issues
2. **Track Operation Duration**: Increasing operation times may indicate performance degradation
3. **Review Error Types**: Different error types require different remediation strategies
4. **Success Rates**: Operations should maintain high success rates (>95%)
5. **Regular Review**: Periodically review metrics to identify trends and issues

## Troubleshooting

### High Sync Failure Rate

If sync operations are failing frequently:
1. Check network connectivity
2. Verify GCP credentials and permissions
3. Check TaskWarrior sync configuration
4. Review sync error types in metrics

### Slow Operations

If operations are taking longer than expected:
1. Check sync duration metrics
2. Verify network latency to GCP
3. Review TaskWarrior database size
4. Consider optimizing filters and queries

### High Error Counts

If error counts are increasing:
1. Review error types in metrics
2. Check logs for detailed error messages
3. Verify input validation rules
4. Ensure TaskWarrior is properly configured
