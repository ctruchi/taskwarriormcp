# TaskWarrior MCP

Simple Python implementation of a Model Context Protocol (MCP) server for TaskWarrior.
This provides access to all tasks and allows tasks to be created and edited through MCP tools.

## Features

- **MCP Tools**: List, add, edit, and filter tasks via Model Context Protocol
- **Automatic Sync**: TaskWarrior syncs before and after each operation
- **GCP Integration**: Uses TaskWarrior's native GCP sync support
- **Configurable**: Works with local TaskWarrior or containerized setup
- **Input Validation**: Comprehensive validation for all inputs to prevent injection attacks and ensure data integrity

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
- `LOG_LEVEL` - Logging level (default: `"INFO"`)
  - Valid levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### OAuth 2.0 Configuration (Optional)

Enable OAuth 2.0 authentication with Dynamic Client Registration (RFC 7591):

- `OAUTH_ENABLED` - Enable OAuth authentication (default: `"false"`)
- `OAUTH_ISSUER_URL` - OAuth issuer URL (default: `"http://localhost:8000"`)
- `OAUTH_AUTH_CODE_LIFETIME` - Authorization code lifetime in seconds (default: `600`)
- `OAUTH_ACCESS_TOKEN_LIFETIME` - Access token lifetime in seconds (default: `3600`)
- `OAUTH_REFRESH_TOKEN_LIFETIME` - Refresh token lifetime in seconds (default: `2592000` = 30 days)
- `OAUTH_DYNAMIC_REGISTRATION` - Enable dynamic client registration (default: `"true"`)
- `OAUTH_REVOCATION_ENABLED` - Enable token revocation (default: `"true"`)

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
│   │   ├── exceptions.py     # Custom exceptions
│   │   ├── validation.py     # Input validation using Pydantic
│   │   ├── logging_config.py # Logging configuration and utilities
│   │   ├── metrics.py        # Metrics collection
│   │   └── oauth/            # OAuth 2.0 implementation
│   │       ├── __init__.py   # OAuth module exports
│   │       ├── config.py     # OAuth configuration
│   │       ├── storage.py    # In-memory token storage
│   │       └── provider.py   # OAuth provider implementation
│   └── tests/
│       ├── test_taskwarrior.py   # Unit tests
│       ├── test_integration.py   # Integration tests
│       ├── test_validation.py    # Validation tests
│       └── test_oauth.py         # OAuth tests
├── docker/                   # Docker setup
├── pyproject.toml           # Project configuration
└── README.md
```

## Docker

A production-ready Dockerfile is provided that packages both the MCP server and TaskWarrior (v3.2.0) in a lightweight, secure container.

### Building the Docker Image

```bash
# Build the image
docker build -t taskwarrior-mcp:latest .

# The image includes:
# - Fedora 41 base
# - TaskWarrior 3.4.1 (from package manager)
# - Python 3.13 with MCP server
# - Final image size: ~294MB
```

### Running with Docker

```bash
# Run the container
docker run -d \
  --name taskwarrior-mcp \
  -e SYNC_GCP_BUCKET=your-bucket-name \
  -e SYNC_GCP_CREDENTIAL_PATH=/credentials/gcp-credentials.json \
  -e LOG_LEVEL=INFO \
  -v taskwarrior-data:/data/taskwarrior \
  -v $(pwd)/config/.taskrc:/config/.taskrc:ro \
  -v $(pwd)/credentials/gcp-credentials.json:/credentials/gcp-credentials.json:ro \
  --read-only \
  --tmpfs /tmp \
  --security-opt no-new-privileges:true \
  taskwarrior-mcp:latest

# View logs
docker logs -f taskwarrior-mcp
```

### Environment Variables (Docker)

- `SYNC_GCP_BUCKET`: GCP bucket name for task synchronization
- `SYNC_GCP_CREDENTIAL_PATH`: Path to GCP credentials file (inside container)
- `LOG_LEVEL`: Logging level (default: INFO)
- `TASKRC`: Path to TaskWarrior config file (default: /config/.taskrc)
- `TASKDATA`: Path to TaskWarrior data directory (default: /data/taskwarrior)

### Security Features

The Docker image implements security best practices:

- **Non-root user**: Runs as user ID 1000
- **Read-only filesystem**: Container root filesystem is read-only
- **No new privileges**: Security option prevents privilege escalation
- **Minimal packages**: Only essential packages installed
- **Resource limits**: Can be configured with docker run --cpus and --memory flags
- **Health checks**: Automatic container health monitoring
- **Signal handling**: Proper shutdown with tini init system
- **Latest TaskWarrior**: v3.4.1 from Fedora repositories

## Input Validation

The server implements comprehensive input validation to ensure data integrity and prevent security issues:

### Validation Rules

- **Task Descriptions**: Max 1000 characters, no control characters, shell injection protection
- **Priority**: Must be "H", "M", "L", or None (case-insensitive, converted to uppercase)
- **Task IDs**: Must be valid UUID or numeric ID format
- **Project Names**: Max 100 characters, alphanumeric + underscore, hyphen, period only
- **Tags**: Max 50 characters each, alphanumeric + underscore, hyphen, period only, no duplicates
- **Due Dates**: ISO date format (YYYY-MM-DD) or TaskWarrior relative dates (tomorrow, eom, etc.)
- **Task Command**: Must contain 'task' executable, protected against shell injection

### Security Features

All inputs are validated for:
- Control characters (except newline and tab)
- Shell injection patterns ($(, `, &&, ||, ;, |, >, <)
- Length limits to prevent DoS attacks
- Format validation using Pydantic

### Error Messages

Validation errors return descriptive messages indicating:
- Which field failed validation
- Why it failed (e.g., "Priority must be one of H, M, L")
- Clear guidance for fixing the issue

## Logging

The TaskWarrior MCP server includes comprehensive logging to help with debugging and monitoring.

### Configuration

Set the `LOG_LEVEL` environment variable to control logging verbosity:

```bash
# Set log level to DEBUG for detailed information
export LOG_LEVEL=DEBUG

# Set log level to INFO for normal operations (default)
export LOG_LEVEL=INFO

# Set log level to WARNING to only see warnings and errors
export LOG_LEVEL=WARNING
```

### Log Levels

- **DEBUG**: Detailed information including command execution, JSON parsing, and sync operations
- **INFO**: General information about tool invocations, operations, and success/failure
- **WARNING**: Warning messages about potential issues
- **ERROR**: Error messages with stack traces
- **CRITICAL**: Critical failures that prevent server operation

### What is Logged

The logging system captures:

#### Server Operations (server.py)
- Tool invocations with sanitized parameters
- Success/failure of each operation
- Task counts and IDs for completed operations
- Error details with stack traces

#### TaskWarrior Integration (taskwarrior.py)
- Command executions (with sensitive data sanitized)
- Sync operations (start, success, failure)
- Subprocess errors with return codes
- JSON parsing operations

#### Configuration (config.py)
- Environment variable loading
- Configuration validation results

### Security

Logging is designed to avoid exposing sensitive information:
- Task descriptions are truncated to 50 characters in logs
- Command arguments longer than 50 characters are truncated
- Full task content is not logged unless at DEBUG level
- No credentials or tokens are logged

### Example Output

```
2026-02-03 17:34:53 - taskwarriormcp.server - INFO - Initializing TaskWarrior MCP server
2026-02-03 17:34:53 - taskwarriormcp.config - INFO - Configuration validated successfully: task_command=task
2026-02-03 17:34:53 - taskwarriormcp.server - INFO - TaskWarrior MCP server initialized successfully
2026-02-03 17:35:10 - taskwarriormcp.server - INFO - Tool invoked: add_task(description='Complete project documentation...', project='work', priority='H', due='tomorrow', tags=['urgent'])
2026-02-03 17:35:10 - taskwarriormcp.taskwarrior - INFO - Starting task sync operation
2026-02-03 17:35:12 - taskwarriormcp.taskwarrior - INFO - Task sync completed successfully
2026-02-03 17:35:12 - taskwarriormcp.taskwarrior - INFO - Executing add_task command with 6 arguments
2026-02-03 17:35:13 - taskwarriormcp.server - INFO - add_task completed successfully: created task ID 42
```

## OAuth 2.0 Authentication

The TaskWarrior MCP server supports optional OAuth 2.0 authentication with Dynamic Client Registration (RFC 7591) per the MCP specification.

### Enabling OAuth

```bash
# Enable OAuth
export OAUTH_ENABLED=true
export OAUTH_ISSUER_URL=http://localhost:8000

# Start the server
python -m taskwarriormcp.server
```

### OAuth Endpoints

When OAuth is enabled, the following endpoints are available:

- `GET /.well-known/oauth-authorization-server` - OAuth metadata
- `POST /register` - Dynamic client registration
- `GET /authorize` - Authorization endpoint
- `POST /token` - Token endpoint
- `POST /revoke` - Token revocation endpoint

### Manual Testing

```bash
# Check OAuth metadata
curl http://localhost:8000/.well-known/oauth-authorization-server

# Register a client
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"redirect_uris": ["http://localhost:3000/callback"], "client_name": "Test Client"}'
```

### Security Considerations

- **HTTPS Required**: For production, redirect URIs must use HTTPS (except localhost)
- **Token Security**: Uses 256-bit entropy for tokens (secrets.token_urlsafe(32))
- **PKCE Required**: MCP SDK enforces PKCE with S256 method
- **Token Rotation**: Refresh tokens are rotated on each use
- **In-Memory Storage**: Tokens are stored in memory and lost on restart (for production, implement persistent storage)

## Task Syncing

Syncing is handled by TaskWarrior's native sync functionality. Currently supports Google Cloud Platform (GCP) as the sync backend.

The MCP server automatically syncs TaskWarrior:
- **Before each command** - Ensures local data is up to date
- **After modifications** - Pushes changes to sync backend

To verify sync works correctly, you can test with two separate TaskWarrior instances (e.g., two Docker containers with different data directories) and confirm tasks sync between them.

## License

See LICENSE file for details.
