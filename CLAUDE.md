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

## Development Status

This repository is in early stages. When implementing the codebase, the key components will be:

1. **MCP Server Implementation** - Python server implementing the Model Context Protocol specification
2. **TaskWarrior Integration** - Python wrapper around TaskWarrior CLI commands
3. **GCP Sync Layer** - Handles uploading/downloading task data to/from GCP bucket
4. **Docker Configuration** - Containerizes the server with TaskWarrior installed

## Rules

- Always update the README.md file with relevant information about the project
- Always update the CLAUDE.md file with relevant information about the project