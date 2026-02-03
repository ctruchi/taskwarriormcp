"""Example demonstrating the metrics system."""

import json
import time
from taskwarriormcp.metrics import get_metrics_collector


def simulate_operations():
    """Simulate various operations with metrics tracking."""
    metrics = get_metrics_collector()

    print("Simulating TaskWarrior MCP operations...\n")

    # Simulate successful list_tasks operations
    print("1. Simulating 5 successful list_tasks operations...")
    for i in range(5):
        with metrics.track_operation("list_tasks"):
            time.sleep(0.1 + i * 0.02)  # Varying durations
    print("   ✓ Completed\n")

    # Simulate add_task operations with some failures
    print("2. Simulating 3 add_task operations (1 will fail)...")
    for i in range(3):
        try:
            with metrics.track_operation("add_task"):
                time.sleep(0.15)
                if i == 1:  # Simulate failure on second operation
                    raise ValueError("Simulated task validation error")
        except ValueError:
            pass
    print("   ✓ Completed (with 1 expected failure)\n")

    # Simulate edit_task operations
    print("3. Simulating 2 edit_task operations...")
    for _ in range(2):
        with metrics.track_operation("edit_task"):
            time.sleep(0.12)
    print("   ✓ Completed\n")

    # Simulate sync operations
    print("4. Simulating 10 sync operations (2 will fail)...")
    for i in range(10):
        try:
            with metrics.track_sync():
                time.sleep(0.05)
                if i in [3, 7]:  # Simulate failures
                    raise RuntimeError("Simulated sync error")
        except RuntimeError:
            pass
    print("   ✓ Completed (with 2 expected failures)\n")

    # Manually record some errors
    print("5. Recording additional errors...")
    metrics.record_error("TaskWarriorCommandError")
    metrics.record_error("TaskWarriorCommandError")
    metrics.record_error("TaskWarriorParseError")
    print("   ✓ Completed\n")


def print_metrics_summary():
    """Print formatted metrics summary."""
    metrics = get_metrics_collector()
    all_metrics = metrics.get_metrics()

    print("=" * 80)
    print("METRICS SUMMARY")
    print("=" * 80)
    print()

    # Server uptime
    print(f"Server Uptime: {all_metrics['uptime_seconds']:.2f} seconds")
    print()

    # Operations metrics
    print("OPERATION METRICS:")
    print("-" * 80)
    if all_metrics['operations']:
        for op_name, op_metrics in all_metrics['operations'].items():
            print(f"\n{op_name}:")
            print(f"  Total Operations:     {op_metrics['total_count']}")
            print(f"  Successful:           {op_metrics['success_count']}")
            print(f"  Failed:               {op_metrics['failure_count']}")
            print(f"  Success Rate:         {op_metrics['success_rate_percent']:.1f}%")
            print(f"  Average Duration:     {op_metrics['average_duration_seconds']:.4f}s")
            if op_metrics['min_duration_seconds']:
                print(f"  Min Duration:         {op_metrics['min_duration_seconds']:.4f}s")
            if op_metrics['max_duration_seconds']:
                print(f"  Max Duration:         {op_metrics['max_duration_seconds']:.4f}s")
    else:
        print("  No operations recorded yet")
    print()

    # Sync metrics
    print("SYNC METRICS:")
    print("-" * 80)
    sync_metrics = all_metrics['sync']
    print(f"  Total Syncs:          {sync_metrics['total_count']}")
    print(f"  Successful:           {sync_metrics['success_count']}")
    print(f"  Failed:               {sync_metrics['failure_count']}")
    print(f"  Success Rate:         {sync_metrics['success_rate_percent']:.1f}%")
    if sync_metrics['total_count'] > 0:
        print(f"  Average Duration:     {sync_metrics['average_duration_seconds']:.4f}s")
    print()

    # Error metrics
    print("ERROR METRICS:")
    print("-" * 80)
    if all_metrics['errors_by_type']:
        print(f"  Total Errors:         {all_metrics['total_errors']}")
        print("  Errors by Type:")
        for error_type, count in all_metrics['errors_by_type'].items():
            print(f"    {error_type:30s} {count:>5d}")
    else:
        print("  No errors recorded")
    print()

    print("=" * 80)


def print_json_metrics():
    """Print metrics as JSON."""
    metrics = get_metrics_collector()
    all_metrics = metrics.get_metrics()

    print("\nMETRICS AS JSON:")
    print("-" * 80)
    print(json.dumps(all_metrics, indent=2))
    print()


def main():
    """Main example function."""
    print("\n" + "=" * 80)
    print("TaskWarrior MCP Metrics System Example")
    print("=" * 80)
    print()

    # Run simulations
    simulate_operations()

    # Print formatted summary
    print_metrics_summary()

    # Print JSON format
    print_json_metrics()

    # Demonstrate individual metric retrieval
    print("\nINDIVIDUAL METRIC QUERIES:")
    print("-" * 80)
    metrics = get_metrics_collector()

    list_tasks_metrics = metrics.get_operation_metrics("list_tasks")
    print(f"list_tasks success rate: {list_tasks_metrics['success_rate_percent']:.1f}%")

    sync_metrics = metrics.get_sync_metrics()
    print(f"sync operations: {sync_metrics['total_count']} total, "
          f"{sync_metrics['success_count']} successful, "
          f"{sync_metrics['failure_count']} failed")

    error_metrics = metrics.get_error_metrics()
    print(f"Total errors: {error_metrics['total_errors']}")
    print()

    print("=" * 80)
    print("Example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
