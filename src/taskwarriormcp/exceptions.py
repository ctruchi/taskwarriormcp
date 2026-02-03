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
