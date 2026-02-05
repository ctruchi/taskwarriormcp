"""MCP server for TaskWarrior."""

import json
from typing import Any

from mcp.server import FastMCP
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions

from .config import Config
from .taskwarrior import TaskWarriorWrapper
from .exceptions import TaskWarriorError
from .logging_config import setup_logging, get_logger, sanitize_for_logging
from .metrics import get_metrics_collector
from .oauth import InMemoryStorage, OAuthConfig, TaskWarriorOAuthProvider

# Setup logging first
setup_logging()
logger = get_logger(__name__)


def create_mcp_server(config: Config) -> FastMCP:
    """Create and configure a FastMCP server instance.

    Args:
        config: Server configuration

    Returns:
        Configured FastMCP server instance
    """
    if config.oauth.enabled:
        logger.info("OAuth is enabled, configuring authentication")

        # Warn about non-HTTPS for non-localhost
        if not config.oauth.is_https and not config.oauth.is_localhost:
            logger.warning(
                "OAuth issuer URL is not HTTPS. This is insecure for production use. "
                f"Current value: {config.oauth.issuer_url}"
            )

        # Create OAuth components
        storage = InMemoryStorage()
        oauth_provider = TaskWarriorOAuthProvider(storage, config.oauth)

        # Create auth settings
        auth_settings = AuthSettings(
            issuer_url=config.oauth.issuer_url,
            resource_server_url=config.oauth.issuer_url,
            client_registration_options=ClientRegistrationOptions(
                enabled=config.oauth.dynamic_registration,
            ),
            revocation_options=RevocationOptions(
                enabled=config.oauth.revocation_enabled,
            ),
        )

        logger.info(
            f"OAuth configured: issuer_url={config.oauth.issuer_url}, "
            f"dynamic_registration={config.oauth.dynamic_registration}, "
            f"revocation={config.oauth.revocation_enabled}"
        )

        return FastMCP(
            "taskwarrior",
            host=config.host,
            port=config.port,
            auth=auth_settings,
            auth_server_provider=oauth_provider,
        )
    else:
        logger.info("OAuth is disabled, creating server without authentication")
        return FastMCP("taskwarrior", host=config.host, port=config.port)


# Initialize configuration
logger.debug("Loading configuration from environment")
config = Config.from_env()
config.validate()

# Initialize FastMCP server
logger.info("Initializing TaskWarrior MCP server")
mcp = create_mcp_server(config)

# Initialize TaskWarrior wrapper and metrics
tw = TaskWarriorWrapper(config)
metrics = get_metrics_collector()
logger.info("TaskWarrior MCP server initialized successfully")


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
    logger.info("Tool invoked: list_tasks")
    with metrics.track_operation("list_tasks"):
        try:
            tasks = tw.list_tasks()
            count = len(tasks)
            logger.info(f"list_tasks completed successfully: returned {count} tasks")
            return format_result({
                "success": True,
                "tasks": tasks,
                "count": count
            })
        except TaskWarriorError as e:
            logger.error(f"list_tasks failed: {str(e)}", exc_info=True)
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
    # Sanitize description for logging (truncate if too long)
    desc_log = sanitize_for_logging(description, max_length=50)
    logger.info(f"Tool invoked: add_task(description={desc_log!r}, project={project!r}, priority={priority!r}, due={due!r}, tags={tags!r})")

    with metrics.track_operation("add_task"):
        try:
            task = tw.add_task(
                description=description,
                project=project,
                priority=priority,
                due=due,
                tags=tags
            )
            task_id = task.get('id')
            logger.info(f"add_task completed successfully: created task ID {task_id}")
            return format_result({
                "success": True,
                "task": task,
                "message": f"Task created successfully with ID {task_id}"
            })
        except TaskWarriorError as e:
            logger.error(f"add_task failed: {str(e)}", exc_info=True)
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
    # Sanitize description for logging
    desc_log = sanitize_for_logging(description, max_length=50) if description else None
    logger.info(f"Tool invoked: edit_task(task_id={task_id!r}, description={desc_log!r}, project={project!r}, priority={priority!r}, due={due!r}, tags={tags!r})")

    with metrics.track_operation("edit_task"):
        try:
            task = tw.edit_task(
                task_id=task_id,
                description=description,
                project=project,
                priority=priority,
                due=due,
                tags=tags
            )
            logger.info(f"edit_task completed successfully: updated task {task_id}")
            return format_result({
                "success": True,
                "task": task,
                "message": f"Task {task_id} updated successfully"
            })
        except TaskWarriorError as e:
            logger.error(f"edit_task failed for task {task_id}: {str(e)}", exc_info=True)
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
    logger.info(f"Tool invoked: list_project_tasks(project={project!r})")
    with metrics.track_operation("list_project_tasks"):
        try:
            tasks = tw.list_project_tasks(project)
            count = len(tasks)
            logger.info(f"list_project_tasks completed successfully: returned {count} tasks for project {project!r}")
            return format_result({
                "success": True,
                "project": project,
                "tasks": tasks,
                "count": count
            })
        except TaskWarriorError as e:
            logger.error(f"list_project_tasks failed for project {project!r}: {str(e)}", exc_info=True)
            return format_result({
                "success": False,
                "error": str(e)
            })


@mcp.tool()
async def get_metrics() -> str:
    """Gets current metrics for the TaskWarrior MCP server.

    Returns comprehensive metrics including:
    - Operation durations and counts (list_tasks, add_task, edit_task, list_project_tasks)
    - Success/failure rates for each operation
    - Sync operation statistics and durations
    - Error counts by exception type
    - Server uptime

    Returns:
        JSON string with all collected metrics
    """
    logger.info("Tool invoked: get_metrics")
    try:
        metrics_data = metrics.get_metrics()
        logger.info("get_metrics completed successfully")
        return format_result({
            "success": True,
            "metrics": metrics_data
        })
    except Exception as e:
        logger.error(f"get_metrics failed: {str(e)}", exc_info=True)
        return format_result({
            "success": False,
            "error": str(e)
        })


def main():
    """Main entry point for the MCP server."""
    logger.info(f"Starting TaskWarrior MCP server with transport: {config.transport}")
    try:
        mcp.run(transport=config.transport)
    except Exception as e:
        logger.critical(f"MCP server crashed: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
