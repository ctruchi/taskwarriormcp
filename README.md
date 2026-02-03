# TaskWarrior MCP

Simple python implementation of a Model Context Protocol (MCP) for TaskWarrior.
This gives access to all the tasks and allow tasks to be created/edited.

## Docker

The Dockerfile run this MCP server and embed taskwarrior to be able to interact with it.
You need to provide two env vars :
- SYNC_GCP_BUCKET: Bucket name in GCP
- SYNC_GCP_CREDENTIAL_PATH: Path where the credentials for the bucket is stored

## Task syncing
For now, syncing is only available via Google Cloud Platform.

Each command of the MCP server sync taskwarrior:
- before the call
- after the call in case of an update
