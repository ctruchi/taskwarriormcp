# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TaskWarrior MCP is a Python implementation of a Model Context Protocol (MCP) server for TaskWarrior. The server provides access to TaskWarrior tasks and enables task creation and editing operations.

## Architecture

```
src/                # Source code for the MCP server and TaskWarrior wrapper
Dockerfile          # Production Docker container (Fedora 41, TaskWarrior 3.4.1, ~294MB)
DOCKER.md           # Comprehensive Docker deployment guide
config/             # Configuration templates (.taskrc.example)
```

### MCP Server
- The MCP server acts as a bridge between AI assistants and TaskWarrior
- All MCP commands trigger automatic syncing:
  - **Before** each command execution
  - **After** each command that modifies tasks

### Docker Container
- Production-ready Dockerfile based on Fedora 41
- Includes TaskWarrior 3.4.1 from official Fedora repositories
- Includes Python 3.13 with MCP server and dependencies
- Security features:
  - Runs as non-root user (UID 1000)
  - Supports read-only filesystem
  - No new privileges flag
  - Health checks included
  - Tini for proper signal handling
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
   - Environment variables:
     - `TASK_COMMAND` (default: "task"): TaskWarrior command to execute
     - `LOG_LEVEL` (default: "INFO"): Logging verbosity level
     - `MCP_TRANSPORT` (default: "stdio"): Transport protocol - `stdio`, `sse`, or `streamable-http`
     - `MCP_HOST` (default: "127.0.0.1"): Host address to bind to (use "0.0.0.0" for Docker)
     - `MCP_PORT` (default: "8000"): Port number for SSE/HTTP transport
   - Transport modes:
     - `stdio`: Standard input/output (default for local development)
     - `sse`: Server-Sent Events over HTTP (default for Docker, listens on port 8000)
     - `streamable-http`: HTTP transport
   - Supports both local TaskWarrior and Docker-based setups

5. **Error Handling** (`src/taskwarriormcp/exceptions.py`)
   - Custom exception hierarchy for TaskWarrior operations
   - Includes: `TaskWarriorError`, `TaskWarriorCommandError`, `TaskWarriorNotFoundError`, `TaskWarriorParseError`, `TaskWarriorSyncError`, `TaskWarriorValidationError`
   - OAuth exceptions: `TaskWarriorOAuthError`, `TaskWarriorAuthenticationError`, `TaskWarriorAuthorizationError`

6. **Input Validation** (`src/taskwarriormcp/validation.py`)
   - Uses Pydantic for structured validation
   - Validates all inputs before execution to prevent injection attacks and ensure data integrity
   - Key validators:
     - `TaskDescriptionValidator`: Max 1000 chars, no control chars, shell injection protection
     - `PriorityValidator`: Must be H/M/L (case-insensitive)
     - `TaskIdValidator`: UUID or numeric ID format
     - `ProjectNameValidator`: Max 100 chars, alphanumeric + underscore/hyphen/period
     - `TagValidator`: Max 50 chars per tag, alphanumeric + underscore/hyphen/period
     - `DueDateValidator`: ISO dates or TaskWarrior relative dates
     - `TaskCommandValidator`: Must contain 'task', injection protection
   - Convenience functions: `validate_add_task_params()`, `validate_edit_task_params()`, `validate_list_project_tasks_params()`, `validate_task_command()`
   - Validation is performed in both `taskwarrior.py` methods and can be used independently
   - All validation errors raise `TaskWarriorValidationError` with descriptive messages

7. **Logging** (`src/taskwarriormcp/logging_config.py`)
   - Comprehensive logging system using Python's standard `logging` module
   - Configurable via `LOG_LEVEL` environment variable (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - Default format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
   - Logs to stderr for compatibility with MCP protocol
   - Key features:
     - `setup_logging()`: Initializes logging configuration on server startup
     - `get_logger(name)`: Returns logger instance for a module
     - `sanitize_for_logging(data, max_length)`: Truncates long strings for safe logging
     - `sanitize_command(command)`: Sanitizes command lists before logging
   - What gets logged:
     - Server initialization and shutdown
     - All tool invocations with sanitized parameters
     - Command executions with sanitized arguments
     - Sync operations (start, success, failure)
     - Subprocess errors with return codes
     - JSON parsing operations
     - Configuration loading and validation
   - Security: Task descriptions truncated to 50 chars, no credentials logged

8. **OAuth 2.0 Authentication** (`src/taskwarriormcp/oauth/`)
   - Implements OAuth 2.0 Dynamic Client Registration (RFC 7591) per MCP specification
   - Uses the MCP SDK's `OAuthAuthorizationServerProvider` protocol
   - Components:
     - `config.py`: OAuth configuration from environment variables
     - `storage.py`: Thread-safe in-memory storage for OAuth data
     - `provider.py`: Full OAuth provider implementation
   - Features:
     - Dynamic client registration with redirect URI validation
     - Authorization code flow with PKCE (enforced by MCP SDK)
     - Token issuance with configurable lifetimes
     - Refresh token rotation for security
     - Token revocation (access and refresh tokens)
   - Environment variables:
     - `OAUTH_ENABLED`: Enable OAuth (default: false)
     - `OAUTH_ISSUER_URL`: OAuth issuer URL (default: http://localhost:8000)
     - `OAUTH_AUTH_CODE_LIFETIME`: Auth code lifetime in seconds (default: 600)
     - `OAUTH_ACCESS_TOKEN_LIFETIME`: Access token lifetime in seconds (default: 3600)
     - `OAUTH_REFRESH_TOKEN_LIFETIME`: Refresh token lifetime in seconds (default: 2592000)
     - `OAUTH_DYNAMIC_REGISTRATION`: Enable dynamic registration (default: true)
     - `OAUTH_REVOCATION_ENABLED`: Enable token revocation (default: true)
   - Security:
     - 256-bit entropy tokens (secrets.token_urlsafe(32))
     - HTTPS required for non-localhost redirect URIs
     - Automatic token expiration handling
     - Thread-safe storage with locks
   - Note: In-memory storage is ephemeral; for production, implement persistent storage

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

# Local TaskWarrior (stdio transport for MCP clients)
export TASK_COMMAND="task"
python -m taskwarriormcp.server

# Docker-based TaskWarrior
export TASK_COMMAND="docker compose -f docker/docker-compose.yml run --rm taskwarrior"
python -m taskwarriormcp.server

# With custom log level
export LOG_LEVEL="DEBUG"
python -m taskwarriormcp.server

# With SSE transport (keeps server running on port 8000)
export MCP_TRANSPORT="sse"
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

# Run only validation tests
pytest src/tests/test_validation.py -v

# Run only OAuth tests
pytest src/tests/test_oauth.py -v
```

### MCP Tools

All MCP tools automatically sync before and after operations:

1. **list_tasks()** - Returns all tasks as JSON
2. **add_task(description, project?, priority?, due?, tags?)** - Creates a new task
3. **edit_task(task_id, description?, project?, priority?, due?, tags?)** - Modifies an existing task
4. **list_project_tasks(project)** - Returns tasks filtered by project

### Running with OAuth Enabled

```bash
# Enable OAuth authentication
export OAUTH_ENABLED=true
export OAUTH_ISSUER_URL=http://localhost:8000
python -m taskwarriormcp.server

# OAuth endpoints are automatically available:
# - GET  /.well-known/oauth-authorization-server
# - POST /register
# - GET  /authorize
# - POST /token
# - POST /revoke
```

## Rules

- Always update the README.md file with relevant information about the project
- Always update the CLAUDE.md file with relevant information about the project
- NEVER add "Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>" or similar co-author attribution to git commit messages