# Input Validation Examples

This document provides examples of the input validation system implemented in TaskWarrior MCP.

## Overview

The validation system uses Pydantic to ensure all inputs are validated before execution. This prevents:
- Shell injection attacks
- Invalid data formats
- Control character injection
- DoS attacks through excessive input lengths

## Validation Rules Summary

| Field | Max Length | Valid Characters | Special Rules |
|-------|------------|------------------|---------------|
| Description | 1000 chars | Any except control chars | Shell injection protection |
| Priority | N/A | H, M, L only | Case-insensitive, converted to uppercase |
| Task ID | 100 chars | UUID or numeric | Format validation |
| Project Name | 100 chars | Alphanumeric + `-_.` | No spaces |
| Tags | 50 chars each | Alphanumeric + `-_.` | No duplicates, no spaces |
| Due Date | 50 chars | ISO dates or TaskWarrior relative | Shell injection protection |
| Task Command | 500 chars | Must contain 'task' | Shell injection protection |

## Valid Examples

### Task Description
```python
# Valid descriptions
"Fix bug in authentication system"
"Review PR #123 for feature/login"
"Update documentation (urgent!)"
"Task: implement API endpoint"

# Invalid - empty
""  # ValidationError: Description cannot be empty

# Invalid - too long
"x" * 1001  # ValidationError: String should have at most 1000 characters

# Invalid - shell injection
"Task $(rm -rf /)"  # ValidationError: Description contains potentially dangerous character sequence
"Task && malicious"  # ValidationError: Description contains potentially dangerous character sequence
```

### Priority
```python
# Valid priorities
"H"  # High
"M"  # Medium
"L"  # Low
"h"  # Converted to "H"
None  # No priority set

# Invalid
"X"  # ValidationError: Priority must be one of H, M, L
"1"  # ValidationError: Priority must be one of H, M, L
"high"  # ValidationError: Priority must be one of H, M, L
```

### Task ID
```python
# Valid task IDs
"123"  # Numeric ID
"550e8400-e29b-41d4-a716-446655440000"  # UUID

# Invalid
"not-a-valid-id"  # ValidationError: Task ID must be a valid UUID or numeric ID
""  # ValidationError: Task ID cannot be empty
"123; rm -rf /"  # ValidationError: Task ID contains potentially dangerous character sequence
```

### Project Name
```python
# Valid project names
"work"
"my-project"
"project_name"
"project.v2"
"api-server-v1.2"

# Invalid
"my project"  # ValidationError: Project name can only contain letters, numbers, underscore, hyphen, and period
"project@work"  # ValidationError: Project name can only contain letters, numbers, underscore, hyphen, and period
""  # ValidationError: Project name cannot be empty
"x" * 101  # ValidationError: String should have at most 100 characters
```

### Tags
```python
# Valid tags
["urgent", "bug", "frontend"]
["v1.2", "api-endpoint"]
["work"]
[]  # Empty list is valid
None  # None is valid

# Invalid
["urgent", "urgent"]  # ValidationError: Tags list contains duplicates
["valid", "invalid tag"]  # ValidationError: Invalid tag 'invalid tag': Tag can only contain letters, numbers, underscore, hyphen, and period
["x" * 51]  # ValidationError: Invalid tag: String should have at most 50 characters
```

### Due Date
```python
# Valid due dates - ISO format
"2024-12-31"
"2024-12-31T23:59:59"
"2025-01-15"

# Valid due dates - TaskWarrior relative
"tomorrow"
"today"
"eom"  # End of month
"eow"  # End of week
"1day"
"2weeks"
"8am"
"noon"

# Invalid
"2024-13-01"  # ValidationError: Invalid ISO date format (month > 12)
"2024-12-31; rm -rf /"  # ValidationError: Due date contains potentially dangerous character sequence
""  # ValidationError: Due date cannot be empty
```

### Task Command
```python
# Valid task commands
"task"
"docker compose -f docker-compose.yml run taskwarrior"
"/usr/bin/task"

# Invalid
""  # ValidationError: Task command cannot be empty
"ls -la"  # ValidationError: Task command must contain 'task' executable
"task && malicious"  # ValidationError: Task command contains potentially dangerous sequence: &&
"task | grep secret"  # ValidationError: Task command contains potentially dangerous sequence: |
```

## Using Validation Functions

### Validate Add Task Parameters
```python
from taskwarriormcp.validation import validate_add_task_params, ValidationError

try:
    validated = validate_add_task_params(
        description="Fix authentication bug",
        project="backend",
        priority="H",
        due="tomorrow",
        tags=["urgent", "bug"]
    )
    print(f"Validated: {validated}")
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Validate Edit Task Parameters
```python
from taskwarriormcp.validation import validate_edit_task_params, ValidationError

try:
    validated = validate_edit_task_params(
        task_id="123",
        description="Updated description",
        priority="M"
    )
    print(f"Validated: {validated}")
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Validate Project Name
```python
from taskwarriormcp.validation import validate_list_project_tasks_params, ValidationError

try:
    validated = validate_list_project_tasks_params(project="my-project")
    print(f"Valid project: {validated}")
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## Security Features

### Shell Injection Protection

The validation system protects against common shell injection patterns:

```python
# These are all rejected
"Task $(malicious_command)"  # Command substitution
"Task `whoami`"              # Backtick command execution
"Task && echo hacked"        # Command chaining
"Task || cat /etc/passwd"    # Command chaining
"Task ; ls -la"              # Command separator
"Task | grep secret"         # Pipe
"Task > /tmp/output"         # Redirect
"Task < /etc/passwd"         # Redirect
```

### Control Character Protection

Control characters (except newline and tab) are rejected:

```python
"Task with \x00 null"  # Rejected
"Task with \x1b escape"  # Rejected
"Task with \n newline"  # Allowed
"Task with \t tab"  # Allowed
```

### Length Limits

All fields have maximum length limits to prevent DoS attacks:

```python
# Description max 1000 chars
"x" * 1001  # Rejected

# Project name max 100 chars
"x" * 101  # Rejected

# Tag max 50 chars
"x" * 51  # Rejected

# Task ID max 100 chars
"x" * 101  # Rejected
```

## Error Messages

The validation system provides clear, actionable error messages:

```python
# Empty description
"Description cannot be empty or whitespace only"

# Invalid priority
"Priority must be one of H, M, L, got: X"

# Invalid task ID format
"Task ID must be a valid UUID or numeric ID, got: invalid-id"

# Shell injection detected
"Description contains potentially dangerous character sequence: $()"

# Invalid project name characters
"Project name can only contain letters, numbers, underscore, hyphen, and period, got: my@project"

# Duplicate tags
"Tags list contains duplicates"
```

## Integration with TaskWarrior Wrapper

All validation happens automatically in the TaskWarrior wrapper methods:

```python
from taskwarriormcp.taskwarrior import TaskWarriorWrapper
from taskwarriormcp.exceptions import TaskWarriorValidationError

tw = TaskWarriorWrapper(config)

try:
    # Validation happens automatically
    task = tw.add_task(
        description="My task",
        priority="H",
        tags=["urgent"]
    )
except TaskWarriorValidationError as e:
    print(f"Validation error: {e}")
```

## Testing Validation

Run the validation test suite:

```bash
# Activate virtual environment
source venv/bin/activate

# Run only validation tests
pytest src/tests/test_validation.py -v

# Run all tests including validation
pytest src/tests/ -v
```

## Customizing Validation

To modify validation rules, edit `/home/ctruchi/dev/wkspace/taskwarriormcp/src/taskwarriormcp/validation.py`:

```python
# Change max description length
MAX_DESCRIPTION_LENGTH = 1000  # Modify this constant

# Add new validation patterns
NEW_PATTERN = re.compile(r'^custom-pattern$')

# Modify validators
@field_validator('description')
@classmethod
def validate_description(cls, v: str) -> str:
    # Add custom validation logic here
    return v
```

## Performance

Validation is designed to be fast and efficient:
- Regex patterns are compiled once at module load time
- Pydantic uses Rust-based validation for speed
- All validation happens in memory before any subprocess calls
- Average validation time: < 1ms per operation

## Summary

The validation system provides comprehensive protection against:
- **Security threats**: Shell injection, control characters
- **Data integrity**: Format validation, length limits
- **Invalid inputs**: Type checking, value constraints
- **User errors**: Clear error messages, trimmed whitespace

All validation is transparent to users and happens automatically before any TaskWarrior commands are executed.
