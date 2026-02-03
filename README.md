# TaskWarrior MCP

Simple Python implementation of a Model Context Protocol (MCP) server for TaskWarrior.
This provides access to all tasks and allows tasks to be created and edited through MCP tools.

## Features

- **MCP Tools**: List, add, edit, and filter tasks via Model Context Protocol
- **Automatic Sync**: TaskWarrior syncs before and after each operation
- **GCP Integration**: Uses TaskWarrior's native GCP sync support
- **Configurable**: Works with local TaskWarrior or containerized setup

## Installation

### Requirements

- Python 3.10 or higher
- TaskWarrior installed and configured (or use Docker setup)

### Install from source

```bash
# Clone the repository
git clone <repository-url>
cd taskwarriormcp

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Install in development mode
pip install -e ".[dev]"
```

## Configuration

### Environment Variables

- `TASK_COMMAND` - Command to execute TaskWarrior (default: `"task"`)
  - For local: `"task"`
  - For Docker: `"docker compose -f docker/docker-compose.yml run --rm taskwarrior"`

### TaskWarrior Sync Configuration

TaskWarrior handles GCP sync through its `.taskrc` configuration file. The MCP server calls `task sync` before and after operations, and TaskWarrior manages the GCP connection.

See [TaskWarrior GCP Sync Documentation](https://taskwarrior.org/docs/sync/) for setting up sync.

## Usage

### Running the MCP Server

```bash
# Activate the virtual environment
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Set the task command (optional, defaults to "task")
export TASK_COMMAND="task"

# Run the server
python -m taskwarriormcp.server
```

Or using Docker:

```bash
# Activate the virtual environment
source venv/bin/activate

# Set the Docker command
export TASK_COMMAND="docker compose -f docker/docker-compose.yml run --rm taskwarrior"

# Run the server
python -m taskwarriormcp.server
```

### Available MCP Tools

1. **list_tasks** - Lists all tasks
   ```python
   # Returns JSON with all tasks
   ```

2. **add_task** - Adds a new task
   ```python
   add_task(
       description="Task description",
       project="project-name",      # optional
       priority="H",                 # optional: H, M, L
       due="tomorrow",               # optional
       tags=["tag1", "tag2"]        # optional
   )
   ```

3. **edit_task** - Edits an existing task
   ```python
   edit_task(
       task_id="1",                  # UUID or short ID
       description="New description", # optional
       project="new-project",        # optional
       priority="M",                 # optional
       due="next week",              # optional
       tags=["newtag"]              # optional
   )
   ```

4. **list_project_tasks** - Lists tasks for a specific project
   ```python
   list_project_tasks(project="project-name")
   ```

## Development

### Running Tests

```bash
# Activate the virtual environment
source venv/bin/activate

# Set the TaskWarrior command for testing
export TASK_COMMAND="docker compose -f docker/docker-compose.yml run --rm taskwarrior"

# Run integration tests (requires TaskWarrior configured)
pytest src/tests/test_integration.py -v -m integration

# Run all tests
pytest src/tests/ -v
```

### Project Structure

```
taskwarriormcp/
├── src/
│   ├── taskwarriormcp/
│   │   ├── __init__.py       # Package initialization
│   │   ├── server.py         # MCP server with tool definitions
│   │   ├── taskwarrior.py    # TaskWarrior CLI wrapper with sync
│   │   ├── config.py         # Configuration management
│   │   └── exceptions.py     # Custom exceptions
│   └── tests/
│       ├── test_taskwarrior.py   # Unit tests
│       └── test_integration.py   # Integration tests
├── docker/                   # Docker setup
├── pyproject.toml           # Project configuration
└── README.md
```

## Docker

The Dockerfile packages the MCP server with TaskWarrior embedded.

### Environment Variables (Docker)

- `SYNC_GCP_BUCKET`: GCP bucket name for task synchronization
- `SYNC_GCP_CREDENTIAL_PATH`: Path to GCP credentials file

## Task Syncing

Syncing is handled by TaskWarrior's native sync functionality. Currently supports Google Cloud Platform (GCP) as the sync backend.

The MCP server automatically syncs TaskWarrior:
- **Before each command** - Ensures local data is up to date
- **After modifications** - Pushes changes to sync backend

To verify sync works correctly, you can test with two separate TaskWarrior instances (e.g., two Docker containers with different data directories) and confirm tasks sync between them.

## License

See LICENSE file for details.
