"""Custom exceptions for TaskWarrior MCP server."""


class TaskWarriorError(Exception):
    """Base exception for TaskWarrior operations."""
    pass


class TaskWarriorCommandError(TaskWarriorError):
    """Command execution failed."""
    pass


class TaskWarriorNotFoundError(TaskWarriorError):
    """Task command not found."""
    pass


class TaskWarriorParseError(TaskWarriorError):
    """JSON parsing failed."""
    pass


class TaskWarriorSyncError(TaskWarriorError):
    """Task sync command failed."""
    pass


class TaskWarriorValidationError(TaskWarriorError):
    """Input validation failed."""
    pass


class TaskWarriorOAuthError(TaskWarriorError):
    """Base exception for OAuth operations."""
    pass


class TaskWarriorAuthenticationError(TaskWarriorOAuthError):
    """Authentication failed (invalid or missing credentials)."""
    pass


class TaskWarriorAuthorizationError(TaskWarriorOAuthError):
    """Authorization failed (insufficient permissions)."""
    pass
