"""MCP server for TaskWarrior."""

import json
from typing import Any

from mcp.server import FastMCP

from .config import Config
from .taskwarrior import TaskWarriorWrapper
from .exceptions import TaskWarriorError


# Initialize FastMCP server
mcp = FastMCP("taskwarrior")

# Initialize configuration and TaskWarrior wrapper
config = Config.from_env()
config.validate()
tw = TaskWarriorWrapper(config)


def format_result(data: Any) -> str:
    """Format result as pretty-printed JSON string.

    Args:
        data: Data to format

    Returns:
        JSON string
    """
    return json.dumps(data, indent=2, ensure_ascii=False)


@mcp.tool()
async def list_tasks() -> str:
    """Lists all tasks in JSON format.

    Returns all tasks from TaskWarrior with full details including
    description, project, priority, tags, status, and dates.

    Returns:
        JSON string with list of tasks
    """
    try:
        tasks = tw.list_tasks()
        return format_result({
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        })
    except TaskWarriorError as e:
        return format_result({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
async def add_task(
    description: str,
    project: str | None = None,
    priority: str | None = None,
    due: str | None = None,
    tags: list[str] | None = None
) -> str:
    """Adds a new task with optional parameters.

    Args:
        description: Task description (required)
        project: Project name (optional)
        priority: Priority level - H (high), M (medium), L (low) (optional)
        due: Due date in TaskWarrior format (e.g., "tomorrow", "2024-12-31", "eom") (optional)
        tags: List of tags to add to the task (optional)

    Returns:
        JSON string with created task details
    """
    try:
        task = tw.add_task(
            description=description,
            project=project,
            priority=priority,
            due=due,
            tags=tags
        )
        return format_result({
            "success": True,
            "task": task,
            "message": f"Task created successfully with ID {task.get('id')}"
        })
    except TaskWarriorError as e:
        return format_result({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
async def edit_task(
    task_id: str,
    description: str | None = None,
    project: str | None = None,
    priority: str | None = None,
    due: str | None = None,
    tags: list[str] | None = None
) -> str:
    """Edits an existing task.

    Args:
        task_id: Task UUID or short ID (required)
        description: New task description (optional)
        project: New project name (optional)
        priority: New priority level - H (high), M (medium), L (low) (optional)
        due: New due date in TaskWarrior format (optional)
        tags: New list of tags (optional, replaces existing tags)

    Returns:
        JSON string with updated task details
    """
    try:
        task = tw.edit_task(
            task_id=task_id,
            description=description,
            project=project,
            priority=priority,
            due=due,
            tags=tags
        )
        return format_result({
            "success": True,
            "task": task,
            "message": f"Task {task_id} updated successfully"
        })
    except TaskWarriorError as e:
        return format_result({
            "success": False,
            "error": str(e)
        })


@mcp.tool()
async def list_project_tasks(project: str) -> str:
    """Lists all tasks for a specific project.

    Args:
        project: Project name to filter tasks (required)

    Returns:
        JSON string with list of tasks in the specified project
    """
    try:
        tasks = tw.list_project_tasks(project)
        return format_result({
            "success": True,
            "project": project,
            "tasks": tasks,
            "count": len(tasks)
        })
    except TaskWarriorError as e:
        return format_result({
            "success": False,
            "error": str(e)
        })


def main():
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
