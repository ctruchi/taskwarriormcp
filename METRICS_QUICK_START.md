# Metrics Quick Start Guide

## Overview

The TaskWarrior MCP server now includes built-in metrics collection to monitor operations, sync performance, and errors.

## Quick Access

### Via MCP Tool

Call the `get_metrics` tool to retrieve all metrics:

```python
# Returns comprehensive metrics as JSON
get_metrics()
```

### From Python Code

```python
from taskwarriormcp.metrics import get_metrics_collector

metrics = get_metrics_collector()
all_metrics = metrics.get_metrics()
print(all_metrics)
```

## What's Tracked

### Operations
- `list_tasks` - Task listing operations
- `add_task` - Task creation operations
- `edit_task` - Task modification operations
- `list_project_tasks` - Project-filtered task listings

### For Each Operation
- Total count
- Success/failure counts
- Success rate %
- Average, min, max duration

### Sync Operations
- Total sync count
- Success/failure counts
- Success rate %
- Duration statistics

### Errors
- Count by exception type
- Total error count

### Server
- Uptime in seconds

## Example Output

```json
{
  "uptime_seconds": 123.45,
  "operations": {
    "list_tasks": {
      "total_count": 10,
      "success_count": 10,
      "failure_count": 0,
      "average_duration_seconds": 0.5234,
      "success_rate_percent": 100.0
    }
  },
  "sync": {
    "total_count": 20,
    "success_count": 18,
    "failure_count": 2,
    "success_rate_percent": 90.0
  },
  "errors_by_type": {
    "TaskWarriorSyncError": 2
  },
  "total_errors": 2
}
```

## Try It Out

Run the example script:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the example
python examples/metrics_example.py
```

## Key Metrics to Monitor

1. **Sync Success Rate** - Should be >95%
   - Low rate indicates connectivity or configuration issues

2. **Operation Durations** - Monitor for increases
   - Increasing times may indicate performance issues

3. **Error Counts** - Should be minimal
   - Review error types to identify root causes

4. **Success Rates** - Should be >95% for all operations
   - Low rates indicate problems with operations

## Integration in Your Code

The metrics system uses context managers for automatic tracking:

```python
from taskwarriormcp.metrics import get_metrics_collector

metrics = get_metrics_collector()

# Track an operation
with metrics.track_operation("my_operation"):
    # Your code here
    result = do_something()

# Track sync
with metrics.track_sync():
    sync_data()

# Record errors manually
try:
    risky_operation()
except Exception as e:
    metrics.record_error(type(e).__name__)
    raise
```

## Testing

Run the metrics test suite:

```bash
source venv/bin/activate
pytest src/tests/test_metrics.py -v
```

## More Information

- Full documentation: `METRICS.md`
- Implementation details: `IMPLEMENTATION_SUMMARY.md`
- Example code: `examples/metrics_example.py`

## Common Questions

**Q: Where are metrics stored?**
A: In-memory. They reset when the server restarts.

**Q: Is there a performance impact?**
A: Minimal (<1ms per operation).

**Q: Can I export to Prometheus?**
A: Not yet, but the system is designed to support it. See `METRICS.md` for details.

**Q: Are metrics thread-safe?**
A: Yes, the collector uses locks for thread safety.

**Q: How do I reset metrics?**
A: `metrics.reset()` - mainly useful for testing.
