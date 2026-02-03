"""Input validation for TaskWarrior MCP server.

This module provides comprehensive validation for all inputs to prevent
injection attacks, invalid data, and ensure data integrity.
"""

import re
import unicodedata
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, ValidationError as PydanticValidationError


# Constants for validation
MAX_DESCRIPTION_LENGTH = 1000
MAX_PROJECT_NAME_LENGTH = 100
MAX_TAG_LENGTH = 50
MAX_TASK_ID_LENGTH = 100
MAX_COMMAND_LENGTH = 500

# Valid priority values
VALID_PRIORITIES = {"H", "M", "L"}

# UUID pattern (TaskWarrior uses UUIDs for task IDs)
UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)

# Numeric ID pattern (TaskWarrior also supports short numeric IDs)
NUMERIC_ID_PATTERN = re.compile(r'^\d+$')

# Valid characters for project names and tags (alphanumeric, underscore, hyphen, period)
PROJECT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]+$')
TAG_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]+$')

# TaskWarrior date formats to validate
# TaskWarrior accepts many date formats including:
# - YYYY-MM-DD
# - relative dates like "tomorrow", "today", "eom", "eow", "1day", "2weeks"
# - time specifications like "8am", "noon", "5pm"
RELATIVE_DATE_PATTERN = re.compile(
    r'^(today|tomorrow|yesterday|eom|eow|eoq|eoy|som|sow|soq|soy|'
    r'now|\d+(?:second|minute|hour|day|week|month|quarter|year)s?|'
    r'\d{1,2}(?:am|pm)|noon|midnight)$',
    re.IGNORECASE
)
DATE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?)?$')


class ValidationError(Exception):
    """Custom validation error for clearer error messages."""
    pass


def validate_no_control_characters(value: str, field_name: str) -> None:
    """Validate that string contains no control characters.

    Args:
        value: String to validate
        field_name: Name of field for error messages

    Raises:
        ValidationError: If string contains control characters
    """
    for char in value:
        if unicodedata.category(char).startswith('C') and char not in ('\n', '\t'):
            raise ValidationError(
                f"{field_name} contains invalid control character: {repr(char)}"
            )


def validate_no_shell_injection(value: str, field_name: str) -> None:
    """Validate that string doesn't contain shell injection patterns.

    Args:
        value: String to validate
        field_name: Name of field for error messages

    Raises:
        ValidationError: If string contains suspicious patterns
    """
    # Check for common shell injection patterns
    dangerous_patterns = [
        r'\$\(',  # Command substitution
        r'`',     # Backticks
        r'&&',    # Command chaining
        r'\|\|',  # Command chaining
        r';',     # Command separator
        r'\|',    # Pipe
        r'>',     # Redirect
        r'<',     # Redirect
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, value):
            raise ValidationError(
                f"{field_name} contains potentially dangerous character sequence: {pattern}"
            )


class TaskDescriptionValidator(BaseModel):
    """Validator for task descriptions."""

    description: str = Field(..., min_length=1, max_length=MAX_DESCRIPTION_LENGTH)

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description content."""
        if not v or not v.strip():
            raise ValueError("Description cannot be empty or whitespace only")

        try:
            validate_no_control_characters(v, "Description")
            # Note: We allow some special characters in descriptions as they might be part
            # of natural text, but we still check for shell injection patterns
            validate_no_shell_injection(v, "Description")
        except ValidationError as e:
            raise ValueError(str(e))

        return v.strip()


class PriorityValidator(BaseModel):
    """Validator for task priority."""

    priority: str | None = None

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        """Validate priority value."""
        if v is None:
            return None

        # Convert to uppercase for comparison
        priority_upper = v.upper()

        if priority_upper not in VALID_PRIORITIES:
            raise ValueError(
                f"Priority must be one of {', '.join(sorted(VALID_PRIORITIES))}, got: {v}"
            )

        return priority_upper


class TaskIdValidator(BaseModel):
    """Validator for task IDs."""

    task_id: str = Field(..., min_length=1, max_length=MAX_TASK_ID_LENGTH)

    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Validate task ID format."""
        if not v or not v.strip():
            raise ValueError("Task ID cannot be empty or whitespace only")

        v = v.strip()

        # Check if it's a UUID or numeric ID
        is_uuid = UUID_PATTERN.match(v)
        is_numeric = NUMERIC_ID_PATTERN.match(v)

        if not is_uuid and not is_numeric:
            raise ValueError(
                f"Task ID must be a valid UUID or numeric ID, got: {v}"
            )

        try:
            validate_no_control_characters(v, "Task ID")
            validate_no_shell_injection(v, "Task ID")
        except ValidationError as e:
            raise ValueError(str(e))

        return v


class ProjectNameValidator(BaseModel):
    """Validator for project names."""

    project: str | None = Field(None, max_length=MAX_PROJECT_NAME_LENGTH)

    @field_validator('project')
    @classmethod
    def validate_project(cls, v: str | None) -> str | None:
        """Validate project name."""
        if v is None:
            return None

        if not v.strip():
            raise ValueError("Project name cannot be empty or whitespace only")

        v = v.strip()

        if not PROJECT_NAME_PATTERN.match(v):
            raise ValueError(
                f"Project name can only contain letters, numbers, underscore, "
                f"hyphen, and period, got: {v}"
            )

        try:
            validate_no_control_characters(v, "Project name")
        except ValidationError as e:
            raise ValueError(str(e))

        return v


class TagValidator(BaseModel):
    """Validator for tags."""

    tag: str = Field(..., min_length=1, max_length=MAX_TAG_LENGTH)

    @field_validator('tag')
    @classmethod
    def validate_tag(cls, v: str) -> str:
        """Validate tag format."""
        if not v or not v.strip():
            raise ValueError("Tag cannot be empty or whitespace only")

        v = v.strip()

        if not TAG_PATTERN.match(v):
            raise ValueError(
                f"Tag can only contain letters, numbers, underscore, "
                f"hyphen, and period, got: {v}"
            )

        try:
            validate_no_control_characters(v, "Tag")
        except ValidationError as e:
            raise ValueError(str(e))

        return v


class TagListValidator(BaseModel):
    """Validator for lists of tags."""

    tags: list[str] | None = None

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate list of tags."""
        if v is None:
            return None

        if not isinstance(v, list):
            raise ValueError("Tags must be a list")

        validated_tags = []
        for tag in v:
            try:
                validated = TagValidator(tag=tag)
                validated_tags.append(validated.tag)
            except PydanticValidationError as e:
                raise ValueError(f"Invalid tag '{tag}': {e.errors()[0]['msg']}")

        # Check for duplicates
        if len(validated_tags) != len(set(validated_tags)):
            raise ValueError("Tags list contains duplicates")

        return validated_tags


class DueDateValidator(BaseModel):
    """Validator for due dates."""

    due: str | None = None

    @field_validator('due')
    @classmethod
    def validate_due(cls, v: str | None) -> str | None:
        """Validate due date format."""
        if v is None:
            return None

        if not v.strip():
            raise ValueError("Due date cannot be empty or whitespace only")

        v = v.strip()

        # Check if it's a valid relative date or ISO date
        is_relative = RELATIVE_DATE_PATTERN.match(v)
        is_iso_date = DATE_PATTERN.match(v)

        if is_iso_date:
            # Validate it's actually a valid date
            try:
                if 'T' in v:
                    datetime.strptime(v.split('T')[0], '%Y-%m-%d')
                else:
                    datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f"Invalid ISO date format: {v}")
        elif not is_relative:
            # If it's neither relative nor ISO date, it might still be valid
            # TaskWarrior syntax, so we'll allow it but warn
            # For now, we'll be permissive and allow any reasonable string
            if len(v) > 50:
                raise ValueError(f"Due date string too long: {v}")

        try:
            validate_no_control_characters(v, "Due date")
            validate_no_shell_injection(v, "Due date")
        except ValidationError as e:
            raise ValueError(str(e))

        return v


class TaskCommandValidator(BaseModel):
    """Validator for task command configuration."""

    task_command: str = Field(..., min_length=1, max_length=MAX_COMMAND_LENGTH)

    @field_validator('task_command')
    @classmethod
    def validate_task_command(cls, v: str) -> str:
        """Validate task command."""
        if not v or not v.strip():
            raise ValueError("Task command cannot be empty or whitespace only")

        v = v.strip()

        # The command should start with either "task" or contain "task" as an argument
        # (for docker compose scenarios)
        if 'task' not in v.lower():
            raise ValueError(
                f"Task command must contain 'task' executable, got: {v}"
            )

        # Check for obviously dangerous patterns
        dangerous_chars = ['&&', '||', ';', '|', '>', '<', '`', '$(']
        for char in dangerous_chars:
            if char in v:
                raise ValueError(
                    f"Task command contains potentially dangerous sequence: {char}"
                )

        try:
            validate_no_control_characters(v, "Task command")
        except ValidationError as e:
            raise ValueError(str(e))

        return v


class AddTaskValidator(BaseModel):
    """Validator for add_task parameters."""

    description: str
    project: str | None = None
    priority: str | None = None
    due: str | None = None
    tags: list[str] | None = None

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description."""
        validator = TaskDescriptionValidator(description=v)
        return validator.description

    @field_validator('project')
    @classmethod
    def validate_project(cls, v: str | None) -> str | None:
        """Validate project."""
        validator = ProjectNameValidator(project=v)
        return validator.project

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        """Validate priority."""
        validator = PriorityValidator(priority=v)
        return validator.priority

    @field_validator('due')
    @classmethod
    def validate_due(cls, v: str | None) -> str | None:
        """Validate due date."""
        validator = DueDateValidator(due=v)
        return validator.due

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate tags."""
        validator = TagListValidator(tags=v)
        return validator.tags


class EditTaskValidator(BaseModel):
    """Validator for edit_task parameters."""

    task_id: str
    description: str | None = None
    project: str | None = None
    priority: str | None = None
    due: str | None = None
    tags: list[str] | None = None

    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """Validate task ID."""
        validator = TaskIdValidator(task_id=v)
        return validator.task_id

    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate description."""
        if v is None:
            return None
        validator = TaskDescriptionValidator(description=v)
        return validator.description

    @field_validator('project')
    @classmethod
    def validate_project(cls, v: str | None) -> str | None:
        """Validate project."""
        validator = ProjectNameValidator(project=v)
        return validator.project

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        """Validate priority."""
        validator = PriorityValidator(priority=v)
        return validator.priority

    @field_validator('due')
    @classmethod
    def validate_due(cls, v: str | None) -> str | None:
        """Validate due date."""
        validator = DueDateValidator(due=v)
        return validator.due

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate tags."""
        validator = TagListValidator(tags=v)
        return validator.tags


class ListProjectTasksValidator(BaseModel):
    """Validator for list_project_tasks parameters."""

    project: str

    @field_validator('project')
    @classmethod
    def validate_project(cls, v: str) -> str:
        """Validate project."""
        validator = ProjectNameValidator(project=v)
        if validator.project is None:
            raise ValueError("Project name is required")
        return validator.project


# Convenience functions for validation
def validate_add_task_params(
    description: str,
    project: str | None = None,
    priority: str | None = None,
    due: str | None = None,
    tags: list[str] | None = None
) -> dict[str, Any]:
    """Validate parameters for add_task operation.

    Args:
        description: Task description
        project: Project name
        priority: Priority level
        due: Due date
        tags: List of tags

    Returns:
        Dictionary of validated parameters

    Raises:
        ValidationError: If any parameter is invalid
    """
    try:
        validator = AddTaskValidator(
            description=description,
            project=project,
            priority=priority,
            due=due,
            tags=tags
        )
        return validator.model_dump(exclude_none=True)
    except PydanticValidationError as e:
        # Extract the first error message for clarity
        error_msg = e.errors()[0]['msg']
        field = e.errors()[0].get('loc', ['unknown'])[0]
        raise ValidationError(f"Invalid {field}: {error_msg}")


def validate_edit_task_params(
    task_id: str,
    description: str | None = None,
    project: str | None = None,
    priority: str | None = None,
    due: str | None = None,
    tags: list[str] | None = None
) -> dict[str, Any]:
    """Validate parameters for edit_task operation.

    Args:
        task_id: Task ID
        description: Task description
        project: Project name
        priority: Priority level
        due: Due date
        tags: List of tags

    Returns:
        Dictionary of validated parameters

    Raises:
        ValidationError: If any parameter is invalid
    """
    try:
        validator = EditTaskValidator(
            task_id=task_id,
            description=description,
            project=project,
            priority=priority,
            due=due,
            tags=tags
        )
        return validator.model_dump(exclude_none=True)
    except PydanticValidationError as e:
        error_msg = e.errors()[0]['msg']
        field = e.errors()[0].get('loc', ['unknown'])[0]
        raise ValidationError(f"Invalid {field}: {error_msg}")


def validate_list_project_tasks_params(project: str) -> str:
    """Validate parameters for list_project_tasks operation.

    Args:
        project: Project name

    Returns:
        Validated project name

    Raises:
        ValidationError: If project name is invalid
    """
    try:
        validator = ListProjectTasksValidator(project=project)
        return validator.project
    except PydanticValidationError as e:
        error_msg = e.errors()[0]['msg']
        raise ValidationError(f"Invalid project name: {error_msg}")


def validate_task_command(task_command: str) -> str:
    """Validate task command configuration.

    Args:
        task_command: Task command string

    Returns:
        Validated task command

    Raises:
        ValidationError: If task command is invalid
    """
    try:
        validator = TaskCommandValidator(task_command=task_command)
        return validator.task_command
    except PydanticValidationError as e:
        error_msg = e.errors()[0]['msg']
        raise ValidationError(f"Invalid task command: {error_msg}")
