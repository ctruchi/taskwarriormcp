"""Tests for input validation."""

import pytest
from pydantic import ValidationError as PydanticValidationError

from taskwarriormcp.validation import (
    TaskDescriptionValidator,
    PriorityValidator,
    TaskIdValidator,
    ProjectNameValidator,
    TagValidator,
    TagListValidator,
    DueDateValidator,
    TaskCommandValidator,
    AddTaskValidator,
    EditTaskValidator,
    ListProjectTasksValidator,
    ValidationError,
    validate_add_task_params,
    validate_edit_task_params,
    validate_list_project_tasks_params,
    validate_task_command,
)


class TestTaskDescriptionValidator:
    """Tests for task description validation."""

    def test_valid_description(self):
        """Test that valid descriptions are accepted."""
        validator = TaskDescriptionValidator(description="This is a valid task")
        assert validator.description == "This is a valid task"

    def test_description_with_special_chars(self):
        """Test that descriptions with normal special characters are accepted."""
        validator = TaskDescriptionValidator(description="Task: review PR #123 (urgent!)")
        assert validator.description == "Task: review PR #123 (urgent!)"

    def test_empty_description(self):
        """Test that empty descriptions are rejected."""
        with pytest.raises(PydanticValidationError):
            TaskDescriptionValidator(description="")

    def test_whitespace_only_description(self):
        """Test that whitespace-only descriptions are rejected."""
        with pytest.raises(PydanticValidationError):
            TaskDescriptionValidator(description="   ")

    def test_description_too_long(self):
        """Test that descriptions exceeding max length are rejected."""
        long_desc = "x" * 1001
        with pytest.raises(PydanticValidationError):
            TaskDescriptionValidator(description=long_desc)

    def test_description_with_shell_injection(self):
        """Test that descriptions with shell injection patterns are rejected."""
        dangerous_inputs = [
            "Task $(rm -rf /)",
            "Task `whoami`",
            "Task && echo hacked",
            "Task || cat /etc/passwd",
            "Task ; ls -la",
            "Task | grep secret",
            "Task > /tmp/output",
            "Task < /etc/passwd",
        ]
        for dangerous in dangerous_inputs:
            with pytest.raises(PydanticValidationError):
                TaskDescriptionValidator(description=dangerous)

    def test_description_trimmed(self):
        """Test that descriptions are trimmed."""
        validator = TaskDescriptionValidator(description="  Task with spaces  ")
        assert validator.description == "Task with spaces"


class TestPriorityValidator:
    """Tests for priority validation."""

    def test_valid_priority_h(self):
        """Test that high priority is accepted."""
        validator = PriorityValidator(priority="H")
        assert validator.priority == "H"

    def test_valid_priority_m(self):
        """Test that medium priority is accepted."""
        validator = PriorityValidator(priority="M")
        assert validator.priority == "M"

    def test_valid_priority_l(self):
        """Test that low priority is accepted."""
        validator = PriorityValidator(priority="L")
        assert validator.priority == "L"

    def test_valid_priority_lowercase(self):
        """Test that lowercase priorities are converted to uppercase."""
        validator = PriorityValidator(priority="h")
        assert validator.priority == "H"

    def test_none_priority(self):
        """Test that None priority is accepted."""
        validator = PriorityValidator(priority=None)
        assert validator.priority is None

    def test_invalid_priority(self):
        """Test that invalid priorities are rejected."""
        with pytest.raises(PydanticValidationError):
            PriorityValidator(priority="X")

    def test_invalid_priority_number(self):
        """Test that numeric priorities are rejected."""
        with pytest.raises(PydanticValidationError):
            PriorityValidator(priority="1")


class TestTaskIdValidator:
    """Tests for task ID validation."""

    def test_valid_uuid(self):
        """Test that valid UUIDs are accepted."""
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        validator = TaskIdValidator(task_id=uuid)
        assert validator.task_id == uuid

    def test_valid_numeric_id(self):
        """Test that numeric IDs are accepted."""
        validator = TaskIdValidator(task_id="123")
        assert validator.task_id == "123"

    def test_invalid_task_id(self):
        """Test that invalid task IDs are rejected."""
        with pytest.raises(PydanticValidationError):
            TaskIdValidator(task_id="not-a-valid-id")

    def test_empty_task_id(self):
        """Test that empty task IDs are rejected."""
        with pytest.raises(PydanticValidationError):
            TaskIdValidator(task_id="")

    def test_task_id_with_injection(self):
        """Test that task IDs with injection patterns are rejected."""
        with pytest.raises(PydanticValidationError):
            TaskIdValidator(task_id="123; rm -rf /")


class TestProjectNameValidator:
    """Tests for project name validation."""

    def test_valid_project_name(self):
        """Test that valid project names are accepted."""
        validator = ProjectNameValidator(project="my-project")
        assert validator.project == "my-project"

    def test_project_with_underscore(self):
        """Test that project names with underscores are accepted."""
        validator = ProjectNameValidator(project="my_project")
        assert validator.project == "my_project"

    def test_project_with_period(self):
        """Test that project names with periods are accepted."""
        validator = ProjectNameValidator(project="my.project")
        assert validator.project == "my.project"

    def test_none_project(self):
        """Test that None project is accepted."""
        validator = ProjectNameValidator(project=None)
        assert validator.project is None

    def test_empty_project(self):
        """Test that empty project names are rejected."""
        with pytest.raises(PydanticValidationError):
            ProjectNameValidator(project="")

    def test_project_with_spaces(self):
        """Test that project names with spaces are rejected."""
        with pytest.raises(PydanticValidationError):
            ProjectNameValidator(project="my project")

    def test_project_with_special_chars(self):
        """Test that project names with special characters are rejected."""
        with pytest.raises(PydanticValidationError):
            ProjectNameValidator(project="my@project")

    def test_project_too_long(self):
        """Test that project names exceeding max length are rejected."""
        long_project = "x" * 101
        with pytest.raises(PydanticValidationError):
            ProjectNameValidator(project=long_project)


class TestTagValidator:
    """Tests for tag validation."""

    def test_valid_tag(self):
        """Test that valid tags are accepted."""
        validator = TagValidator(tag="urgent")
        assert validator.tag == "urgent"

    def test_tag_with_hyphen(self):
        """Test that tags with hyphens are accepted."""
        validator = TagValidator(tag="high-priority")
        assert validator.tag == "high-priority"

    def test_empty_tag(self):
        """Test that empty tags are rejected."""
        with pytest.raises(PydanticValidationError):
            TagValidator(tag="")

    def test_tag_with_spaces(self):
        """Test that tags with spaces are rejected."""
        with pytest.raises(PydanticValidationError):
            TagValidator(tag="high priority")

    def test_tag_too_long(self):
        """Test that tags exceeding max length are rejected."""
        long_tag = "x" * 51
        with pytest.raises(PydanticValidationError):
            TagValidator(tag=long_tag)


class TestTagListValidator:
    """Tests for tag list validation."""

    def test_valid_tag_list(self):
        """Test that valid tag lists are accepted."""
        validator = TagListValidator(tags=["urgent", "bug", "frontend"])
        assert validator.tags == ["urgent", "bug", "frontend"]

    def test_none_tags(self):
        """Test that None tags are accepted."""
        validator = TagListValidator(tags=None)
        assert validator.tags is None

    def test_empty_tag_list(self):
        """Test that empty tag lists are accepted."""
        validator = TagListValidator(tags=[])
        assert validator.tags == []

    def test_duplicate_tags(self):
        """Test that duplicate tags are rejected."""
        with pytest.raises(PydanticValidationError):
            TagListValidator(tags=["urgent", "urgent"])

    def test_invalid_tag_in_list(self):
        """Test that lists with invalid tags are rejected."""
        with pytest.raises(PydanticValidationError):
            TagListValidator(tags=["valid", "invalid tag"])


class TestDueDateValidator:
    """Tests for due date validation."""

    def test_valid_iso_date(self):
        """Test that ISO dates are accepted."""
        validator = DueDateValidator(due="2024-12-31")
        assert validator.due == "2024-12-31"

    def test_valid_iso_datetime(self):
        """Test that ISO datetimes are accepted."""
        validator = DueDateValidator(due="2024-12-31T23:59:59")
        assert validator.due == "2024-12-31T23:59:59"

    def test_valid_relative_date(self):
        """Test that relative dates are accepted."""
        relative_dates = ["tomorrow", "today", "eom", "eow", "1day", "2weeks"]
        for date in relative_dates:
            validator = DueDateValidator(due=date)
            assert validator.due == date

    def test_none_due_date(self):
        """Test that None due date is accepted."""
        validator = DueDateValidator(due=None)
        assert validator.due is None

    def test_invalid_iso_date(self):
        """Test that invalid ISO dates are rejected."""
        with pytest.raises(PydanticValidationError):
            DueDateValidator(due="2024-13-01")  # Invalid month

    def test_due_date_with_injection(self):
        """Test that due dates with injection patterns are rejected."""
        with pytest.raises(PydanticValidationError):
            DueDateValidator(due="2024-12-31; rm -rf /")


class TestTaskCommandValidator:
    """Tests for task command validation."""

    def test_valid_task_command(self):
        """Test that valid task commands are accepted."""
        validator = TaskCommandValidator(task_command="task")
        assert validator.task_command == "task"

    def test_valid_docker_task_command(self):
        """Test that docker compose task commands are accepted."""
        validator = TaskCommandValidator(
            task_command="docker compose -f docker-compose.yml run taskwarrior"
        )
        assert "task" in validator.task_command.lower()

    def test_empty_task_command(self):
        """Test that empty task commands are rejected."""
        with pytest.raises(PydanticValidationError):
            TaskCommandValidator(task_command="")

    def test_task_command_without_task(self):
        """Test that commands without 'task' are rejected."""
        with pytest.raises(PydanticValidationError):
            TaskCommandValidator(task_command="ls -la")

    def test_task_command_with_injection(self):
        """Test that commands with injection patterns are rejected."""
        dangerous_patterns = [
            "task && rm -rf /",
            "task || echo hacked",
            "task ; ls",
            "task | grep",
            "task > /tmp/output",
            "task < /etc/passwd",
            "task `whoami`",
            "task $(echo hacked)",
        ]
        for dangerous in dangerous_patterns:
            with pytest.raises(PydanticValidationError):
                TaskCommandValidator(task_command=dangerous)


class TestAddTaskValidator:
    """Tests for add_task parameter validation."""

    def test_valid_add_task_minimal(self):
        """Test that minimal valid add_task params are accepted."""
        validator = AddTaskValidator(description="Test task")
        assert validator.description == "Test task"
        assert validator.project is None
        assert validator.priority is None
        assert validator.due is None
        assert validator.tags is None

    def test_valid_add_task_full(self):
        """Test that full valid add_task params are accepted."""
        validator = AddTaskValidator(
            description="Test task",
            project="myproject",
            priority="H",
            due="tomorrow",
            tags=["urgent", "bug"]
        )
        assert validator.description == "Test task"
        assert validator.project == "myproject"
        assert validator.priority == "H"
        assert validator.due == "tomorrow"
        assert validator.tags == ["urgent", "bug"]

    def test_add_task_invalid_priority(self):
        """Test that add_task with invalid priority is rejected."""
        with pytest.raises(PydanticValidationError):
            AddTaskValidator(description="Test", priority="X")


class TestEditTaskValidator:
    """Tests for edit_task parameter validation."""

    def test_valid_edit_task_minimal(self):
        """Test that minimal valid edit_task params are accepted."""
        validator = EditTaskValidator(task_id="123")
        assert validator.task_id == "123"
        assert validator.description is None

    def test_valid_edit_task_full(self):
        """Test that full valid edit_task params are accepted."""
        validator = EditTaskValidator(
            task_id="550e8400-e29b-41d4-a716-446655440000",
            description="Updated task",
            project="newproject",
            priority="M",
            due="2024-12-31",
            tags=["updated"]
        )
        assert validator.task_id == "550e8400-e29b-41d4-a716-446655440000"
        assert validator.description == "Updated task"

    def test_edit_task_invalid_task_id(self):
        """Test that edit_task with invalid task_id is rejected."""
        with pytest.raises(PydanticValidationError):
            EditTaskValidator(task_id="invalid-id")


class TestListProjectTasksValidator:
    """Tests for list_project_tasks parameter validation."""

    def test_valid_list_project_tasks(self):
        """Test that valid list_project_tasks params are accepted."""
        validator = ListProjectTasksValidator(project="myproject")
        assert validator.project == "myproject"

    def test_list_project_tasks_empty_project(self):
        """Test that list_project_tasks with empty project is rejected."""
        with pytest.raises(PydanticValidationError):
            ListProjectTasksValidator(project="")


class TestConvenienceFunctions:
    """Tests for convenience validation functions."""

    def test_validate_add_task_params_success(self):
        """Test that validate_add_task_params works with valid input."""
        result = validate_add_task_params(
            description="Test task",
            project="myproject",
            priority="H",
            due="tomorrow",
            tags=["urgent"]
        )
        assert result['description'] == "Test task"
        assert result['project'] == "myproject"
        assert result['priority'] == "H"
        assert result['due'] == "tomorrow"
        assert result['tags'] == ["urgent"]

    def test_validate_add_task_params_failure(self):
        """Test that validate_add_task_params raises ValidationError on invalid input."""
        with pytest.raises(ValidationError):
            validate_add_task_params(description="")

    def test_validate_edit_task_params_success(self):
        """Test that validate_edit_task_params works with valid input."""
        result = validate_edit_task_params(
            task_id="123",
            description="Updated task"
        )
        assert result['task_id'] == "123"
        assert result['description'] == "Updated task"

    def test_validate_edit_task_params_failure(self):
        """Test that validate_edit_task_params raises ValidationError on invalid input."""
        with pytest.raises(ValidationError):
            validate_edit_task_params(task_id="invalid-id")

    def test_validate_list_project_tasks_params_success(self):
        """Test that validate_list_project_tasks_params works with valid input."""
        result = validate_list_project_tasks_params(project="myproject")
        assert result == "myproject"

    def test_validate_list_project_tasks_params_failure(self):
        """Test that validate_list_project_tasks_params raises ValidationError on invalid input."""
        with pytest.raises(ValidationError):
            validate_list_project_tasks_params(project="")

    def test_validate_task_command_success(self):
        """Test that validate_task_command works with valid input."""
        result = validate_task_command(task_command="task")
        assert result == "task"

    def test_validate_task_command_failure(self):
        """Test that validate_task_command raises ValidationError on invalid input."""
        with pytest.raises(ValidationError):
            validate_task_command(task_command="ls -la")
