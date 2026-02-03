# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TaskWarrior MCP is a Python implementation of a Model Context Protocol (MCP) server for TaskWarrior. The server provides access to TaskWarrior tasks and enables task creation and editing operations.

## Architecture

```
src/        # Source code for the MCP server and TaskWarrior wrapper
Dockerfile  # Docker container for the MCP server and taskwarrior
```

### MCP Server
- The MCP server acts as a bridge between AI assistants and TaskWarrior
- All MCP commands trigger automatic syncing:
  - **Before** each command execution
  - **After** each command that modifies tasks

### Docker Container
- The Dockerfile packages both the MCP server and TaskWarrior binary
- Required environment variables:
  - `SYNC_GCP_BUCKET`: GCP bucket name for task synchronization
  - `SYNC_GCP_CREDENTIAL_PATH`: Path to GCP credentials file

### Task Synchronization
- Currently only supports Google Cloud Platform (GCP) as the sync backend
- Sync operations are automatic and bidirectional around each MCP command

## Implementation Details

The codebase consists of the following key components:

1. **MCP Server Implementation** (`src/taskwarriormcp/server.py`)
   - Python server using FastMCP from the MCP SDK
   - Exposes four MCP tools: `list_tasks`, `add_task`, `edit_task`, `list_project_tasks`
   - All tools return JSON-formatted results with success/error information

2. **TaskWarrior Integration** (`src/taskwarriormcp/taskwarrior.py`)
   - Python wrapper around TaskWarrior CLI commands
   - Uses subprocess to execute TaskWarrior commands
   - Automatically calls `task sync` before and after operations
   - Parses JSON output from `task export` commands

3. **Sync Integration**
   - TaskWarrior's native `task sync` command is called via subprocess
   - TaskWarrior handles all GCP sync details through its `.taskrc` configuration
   - The MCP server doesn't directly interact with GCP - it delegates to TaskWarrior

4. **Configuration** (`src/taskwarriormcp/config.py`)
   - Environment variable: `TASK_COMMAND` (default: "task")
   - Supports both local TaskWarrior and Docker-based setups

5. **Error Handling** (`src/taskwarriormcp/exceptions.py`)
   - Custom exception hierarchy for TaskWarrior operations
   - Includes: `TaskWarriorError`, `TaskWarriorCommandError`, `TaskWarriorNotFoundError`, `TaskWarriorParseError`, `TaskWarriorSyncError`

## Development Workflow

### Setup

The project uses a Python virtual environment for dependency isolation:

```bash
# Create virtual environment (first time only)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Install package with dependencies
pip install -e ".[dev]"
```

### Running the MCP Server

```bash
# Activate virtual environment
source venv/bin/activate

# Local TaskWarrior
export TASK_COMMAND="task"
python -m taskwarriormcp.server

# Docker-based TaskWarrior
export TASK_COMMAND="docker compose -f docker/docker-compose.yml run --rm taskwarrior"
python -m taskwarriormcp.server
```

### Testing

Integration tests are located in `src/tests/test_integration.py`:

```bash
# Activate virtual environment
source venv/bin/activate

# Set TaskWarrior command for testing
export TASK_COMMAND="docker compose -f docker/docker-compose.yml run --rm taskwarrior"

# Run integration tests (requires TaskWarrior configured)
pytest src/tests/test_integration.py -v -m integration

# Run all tests
pytest src/tests/ -v
```

### MCP Tools

All MCP tools automatically sync before and after operations:

1. **list_tasks()** - Returns all tasks as JSON
2. **add_task(description, project?, priority?, due?, tags?)** - Creates a new task
3. **edit_task(task_id, description?, project?, priority?, due?, tags?)** - Modifies an existing task
4. **list_project_tasks(project)** - Returns tasks filtered by project

## Rules

- Always update the README.md file with relevant information about the project
- Always update the CLAUDE.md file with relevant information about the project