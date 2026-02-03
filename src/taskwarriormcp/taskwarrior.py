"""TaskWarrior CLI wrapper with automatic sync."""

import json
import shlex
import subprocess
from typing import Any, Callable

from .config import Config
from .exceptions import (
    TaskWarriorCommandError,
    TaskWarriorNotFoundError,
    TaskWarriorParseError,
    TaskWarriorSyncError,
)


class TaskWarriorWrapper:
    """Wrapper around TaskWarrior CLI with automatic sync."""

    def __init__(self, config: Config):
        """Initialize TaskWarrior wrapper.

        Args:
            config: Configuration instance
        """
        self.config = config

    def _run_command(self, args: list[str]) -> str:
        """Execute task command and return stdout.

        Args:
            args: Command arguments (without the task command itself)

        Returns:
            Command stdout as string

        Raises:
            TaskWarriorNotFoundError: If task command not found
            TaskWarriorCommandError: If command execution failed
        """
        # Split the task_command in case it contains multiple parts (e.g., "docker compose run taskwarrior")
        cmd_parts = shlex.split(self.config.task_command)
        full_command = cmd_parts + args

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except FileNotFoundError as e:
            raise TaskWarriorNotFoundError(
                f"Task command not found: {self.config.task_command}"
            ) from e
        except subprocess.CalledProcessError as e:
            raise TaskWarriorCommandError(
                f"Task command failed: {e.stderr or e.stdout}"
            ) from e

    def _sync(self) -> None:
        """Execute task sync.

        TaskWarrior handles GCP sync configuration through .taskrc file.

        Raises:
            TaskWarriorSyncError: If sync command failed
        """
        try:
            self._run_command(["sync"])
        except TaskWarriorCommandError as e:
            raise TaskWarriorSyncError(f"Sync failed: {e}") from e

    def _with_sync(self, operation_func: Callable[[], Any], modifies_data: bool = False) -> Any:
        """Execute operation with sync wrapper.

        Syncs before operation, and after if operation modifies data.

        Args:
            operation_func: Function to execute
            modifies_data: Whether operation modifies task data

        Returns:
            Result from operation_func

        Raises:
            TaskWarriorSyncError: If sync failed
        """
        # Sync before operation
        self._sync()

        # Execute operation
        result = operation_func()

        # Sync after if data was modified
        if modifies_data:
            self._sync()

        return result

    def _parse_json_output(self, output: str) -> list[dict[str, Any]]:
        """Parse JSON output from task export.

        Handles both JSON array format and line-delimited JSON.

        Args:
            output: JSON output from task command

        Returns:
            List of task dictionaries

        Raises:
            TaskWarriorParseError: If JSON parsing failed
        """
        if not output or not output.strip():
            return []

        try:
            # Try parsing as JSON array first
            data = json.loads(output)
            if isinstance(data, list):
                return data
            return [data]
        except json.JSONDecodeError:
            # Try line-delimited JSON
            try:
                lines = [line.strip() for line in output.strip().split('\n') if line.strip()]
                return [json.loads(line) for line in lines]
            except json.JSONDecodeError as e:
                raise TaskWarriorParseError(f"Failed to parse JSON output: {e}") from e

    def list_tasks(self) -> list[dict[str, Any]]:
        """List all tasks.

        Returns:
            List of task dictionaries
        """
        def _list():
            output = self._run_command(["export"])
            return self._parse_json_output(output)

        return self._with_sync(_list, modifies_data=False)

    def add_task(
        self,
        description: str,
        project: str | None = None,
        priority: str | None = None,
        due: str | None = None,
        tags: list[str] | None = None
    ) -> dict[str, Any]:
        """Add a new task.

        Args:
            description: Task description
            project: Project name
            priority: Priority (H, M, L)
            due: Due date
            tags: List of tags

        Returns:
            Task dictionary
        """
        def _add():
            args = ["add", shlex.quote(description)]

            if project:
                args.append(f"project:{shlex.quote(project)}")
            if priority:
                args.append(f"priority:{shlex.quote(priority)}")
            if due:
                args.append(f"due:{shlex.quote(due)}")
            if tags:
                for tag in tags:
                    args.append(f"+{shlex.quote(tag)}")

            output = self._run_command(args)

            # Parse output to extract UUID
            # Output format: "Created task 1." or similar
            # Get the task by listing all tasks and finding the newest one
            # For simplicity, we'll export all tasks and return the last one
            # This assumes the newest task is the one we just added
            all_tasks = self._parse_json_output(self._run_command(["export"]))
            if not all_tasks:
                raise TaskWarriorCommandError("Failed to retrieve added task")

            # Return the most recently added task (highest id)
            return max(all_tasks, key=lambda t: t.get("id", 0))

        return self._with_sync(_add, modifies_data=True)

    def edit_task(
        self,
        task_id: str,
        description: str | None = None,
        project: str | None = None,
        priority: str | None = None,
        due: str | None = None,
        tags: list[str] | None = None
    ) -> dict[str, Any]:
        """Edit an existing task.

        Args:
            task_id: Task UUID or short ID
            description: New task description
            project: New project name
            priority: New priority (H, M, L)
            due: New due date
            tags: New list of tags

        Returns:
            Updated task dictionary
        """
        def _edit():
            args = [task_id, "modify"]

            if description:
                args.append(f"description:{shlex.quote(description)}")
            if project:
                args.append(f"project:{shlex.quote(project)}")
            if priority:
                args.append(f"priority:{shlex.quote(priority)}")
            if due:
                args.append(f"due:{shlex.quote(due)}")
            if tags:
                for tag in tags:
                    args.append(f"+{shlex.quote(tag)}")

            self._run_command(args)

            # Export the modified task
            output = self._run_command([task_id, "export"])
            tasks = self._parse_json_output(output)
            if not tasks:
                raise TaskWarriorCommandError(f"Failed to retrieve task {task_id}")
            return tasks[0]

        return self._with_sync(_edit, modifies_data=True)

    def list_project_tasks(self, project: str) -> list[dict[str, Any]]:
        """List all tasks for a specific project.

        Args:
            project: Project name

        Returns:
            List of task dictionaries
        """
        def _list():
            output = self._run_command([f"project:{project}", "export"])
            return self._parse_json_output(output)

        return self._with_sync(_list, modifies_data=False)
