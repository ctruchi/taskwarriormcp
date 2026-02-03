"""Integration tests for TaskWarrior MCP server."""

import json
import os
import pytest

from taskwarriormcp.config import Config
from taskwarriormcp.taskwarrior import TaskWarriorWrapper
from taskwarriormcp.exceptions import TaskWarriorError


@pytest.fixture
def config():
    """Create test configuration."""
    return Config.from_env()


@pytest.fixture
def taskwarrior(config):
    """Create TaskWarrior wrapper instance."""
    return TaskWarriorWrapper(config)


def test_config_from_env():
    """Test configuration loading from environment."""
    # Save original environment variable
    original_task_command = os.environ.get("TASK_COMMAND")

    try:
        config = Config.from_env()
        assert config.task_command is not None

        # Test with custom command
        os.environ["TASK_COMMAND"] = "custom-task"
        config = Config.from_env()
        assert config.task_command == "custom-task"
    finally:
        # Restore original environment variable
        if original_task_command is not None:
            os.environ["TASK_COMMAND"] = original_task_command
        elif "TASK_COMMAND" in os.environ:
            del os.environ["TASK_COMMAND"]


def test_config_validation():
    """Test configuration validation."""
    from taskwarriormcp.exceptions import TaskWarriorValidationError

    config = Config(task_command="task")
    config.validate()  # Should not raise

    config = Config(task_command="")
    with pytest.raises(TaskWarriorValidationError):
        config.validate()


@pytest.mark.integration
def test_list_tasks(taskwarrior):
    """Test listing all tasks."""
    tasks = taskwarrior.list_tasks()
    assert isinstance(tasks, list)


@pytest.mark.integration
def test_add_and_list_task(taskwarrior):
    """Test adding a task and verifying it appears in list."""
    # Add a task
    task = taskwarrior.add_task(
        description="Test task from integration test",
        project="testing",
        priority="H",
        tags=["integration"]
    )

    assert task is not None
    assert "id" in task
    assert task.get("description") == "Test task from integration test"
    assert task.get("project") == "testing"
    assert task.get("priority") == "H"

    # Verify task appears in list
    tasks = taskwarrior.list_tasks()
    task_ids = [t.get("id") for t in tasks]
    assert task.get("id") in task_ids


@pytest.mark.integration
def test_edit_task(taskwarrior):
    """Test editing a task."""
    # Add a task
    task = taskwarrior.add_task(
        description="Task to edit",
        project="testing"
    )
    task_id = str(task.get("id"))

    # Edit the task
    updated_task = taskwarrior.edit_task(
        task_id=task_id,
        description="Updated task description",
        priority="M"
    )

    assert updated_task is not None
    assert updated_task.get("description") == "Updated task description"
    assert updated_task.get("priority") == "M"
    assert updated_task.get("project") == "testing"


@pytest.mark.integration
def test_list_project_tasks(taskwarrior):
    """Test listing tasks for a specific project."""
    # Add tasks to a project
    project_name = "test-project-filter"

    task1 = taskwarrior.add_task(
        description="Task 1",
        project=project_name
    )

    task2 = taskwarrior.add_task(
        description="Task 2",
        project=project_name
    )

    # List tasks for the project
    tasks = taskwarrior.list_project_tasks(project_name)

    assert len(tasks) >= 2
    task_descriptions = [t.get("description") for t in tasks]
    assert "Task 1" in task_descriptions
    assert "Task 2" in task_descriptions


@pytest.mark.integration
def test_sync_operations(taskwarrior):
    """Test that sync operations are called (implicitly tested by other tests)."""
    # This test verifies that operations complete without sync errors
    # Actual sync functionality is tested by two-instance tests
    try:
        taskwarrior.list_tasks()
    except TaskWarriorError as e:
        pytest.fail(f"Sync or list operation failed: {e}")
