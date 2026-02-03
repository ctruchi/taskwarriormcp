# Docker Deployment Guide

This guide covers how to deploy the TaskWarrior MCP Server using Docker.

## Quick Start

```bash
# 1. Build the image
docker build -t taskwarrior-mcp:latest .

# 2. Create configuration
mkdir -p config credentials
cp config/.taskrc.example config/.taskrc

# 3. Edit config/.taskrc with your GCP settings
# Uncomment and set:
#   sync.gcp.bucket=your-bucket-name
#   sync.gcp.credential_path=/credentials/gcp-credentials.json

# 4. Add your GCP credentials
cp /path/to/your/gcp-key.json credentials/gcp-credentials.json

# 5. Run the container
docker run -d \
  --name taskwarrior-mcp \
  -e SYNC_GCP_BUCKET=your-bucket-name \
  -e SYNC_GCP_CREDENTIAL_PATH=/credentials/gcp-credentials.json \
  -v taskwarrior-data:/data/taskwarrior \
  -v $(pwd)/config/.taskrc:/config/.taskrc:ro \
  -v $(pwd)/credentials/gcp-credentials.json:/credentials/gcp-credentials.json:ro \
  --read-only \
  --tmpfs /tmp \
  --security-opt no-new-privileges:true \
  taskwarrior-mcp:latest
```

## Dockerfile Architecture

The Dockerfile is optimized for simplicity and security:

### Single-Stage Build
- Base: `fedora:41`
- Size: ~294MB
- Components:
  - TaskWarrior 3.4.1 (from Fedora repositories)
  - Python 3.13 with pip
  - MCP server and dependencies
  - Tini init system for proper signal handling
- Benefits:
  - Latest TaskWarrior from official packages
  - Fast build times (no compilation)
  - Automatic security updates via package manager
  - Native GCP sync support included

## Security Features

### Container Security

1. **Non-root User**: Runs as UID 1000 (taskuser)
2. **Read-only Root Filesystem**: Prevents tampering
3. **No New Privileges**: Blocks privilege escalation
4. **Minimal Base**: Alpine Linux reduces attack surface
5. **No Build Tools**: Runtime image contains no compilers or dev tools
6. **Signal Handling**: Proper shutdown via tini init system

### Best Practices Implemented

```yaml
# In docker-compose.yml
security_opt:
  - no-new-privileges:true
read_only: true
tmpfs:
  - /tmp  # Only /tmp is writable
```

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
    reservations:
      cpus: '0.25'
      memory: 128M
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNC_GCP_BUCKET` | (required) | GCP bucket name for sync |
| `SYNC_GCP_CREDENTIAL_PATH` | `/credentials/gcp-credentials.json` | Path to GCP credentials |
| `LOG_LEVEL` | `INFO` | Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `TASKRC` | `/config/.taskrc` | TaskWarrior config file path |
| `TASKDATA` | `/data/taskwarrior` | TaskWarrior data directory |
| `TASK_COMMAND` | `task` | TaskWarrior command to execute |

### Volume Mounts

1. **TaskWarrior Data** (required):
   ```bash
   -v taskwarrior-data:/data/taskwarrior
   ```
   Persistent storage for task data.

2. **Configuration** (required):
   ```bash
   -v ./config/.taskrc:/config/.taskrc:ro
   ```
   TaskWarrior configuration file (read-only).

3. **GCP Credentials** (required for sync):
   ```bash
   -v ./credentials/gcp-credentials.json:/credentials/gcp-credentials.json:ro
   ```
   GCP service account credentials (read-only).

## Building Custom Images

### Build Arguments

```bash
# Build with custom TaskWarrior version
docker build \
  --build-arg TASKWARRIOR_VERSION=v3.1.0 \
  -t taskwarrior-mcp:custom \
  .
```

### Build Options

```bash
# Build with BuildKit (faster, better caching)
DOCKER_BUILDKIT=1 docker build -t taskwarrior-mcp:latest .

# Build with no cache
docker build --no-cache -t taskwarrior-mcp:latest .

# Build for specific platform
docker build --platform linux/amd64 -t taskwarrior-mcp:latest .
```

## Running the Container

```bash
docker run -d \
  --name taskwarrior-mcp \
  -e SYNC_GCP_BUCKET=my-bucket \
  -e SYNC_GCP_CREDENTIAL_PATH=/credentials/gcp-credentials.json \
  -e LOG_LEVEL=INFO \
  -v taskwarrior-data:/data/taskwarrior \
  -v $(pwd)/config/.taskrc:/config/.taskrc:ro \
  -v $(pwd)/credentials/gcp-credentials.json:/credentials/gcp-credentials.json:ro \
  --read-only \
  --tmpfs /tmp \
  --security-opt no-new-privileges:true \
  --memory=512m \
  --cpus=1.0 \
  taskwarrior-mcp:latest
```

## Health Checks

The container includes automatic health monitoring:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD task --version || exit 1
```

Check container health:

```bash
# Via docker ps
docker ps

# Via docker inspect
docker inspect --format='{{.State.Health.Status}}' taskwarrior-mcp

# View container status
docker ps
```

## Troubleshooting

### View Logs

```bash
# Last 100 lines
docker logs --tail 100 taskwarrior-mcp

# Follow logs
docker logs -f taskwarrior-mcp

# With timestamps
docker logs -t taskwarrior-mcp
```

### Access Container Shell

```bash
# For debugging (container must be running)
docker exec -it taskwarrior-mcp /bin/sh

# Check TaskWarrior version
docker exec taskwarrior-mcp task --version

# Check Python version
docker exec taskwarrior-mcp python --version
```

### Common Issues

**Issue**: Container exits immediately

```bash
# Check logs for errors
docker logs taskwarrior-mcp

# Verify configuration
docker exec taskwarrior-mcp cat /config/.taskrc
```

**Issue**: Permission denied

```bash
# Ensure volumes are owned by UID 1000
sudo chown -R 1000:1000 ./config ./credentials
```

**Issue**: GCP sync fails

```bash
# Verify credentials file is mounted correctly
docker exec taskwarrior-mcp ls -l /credentials/

# Check TaskWarrior config
docker exec taskwarrior-mcp task diagnostics
```

## Advanced Usage

### Custom Entrypoint

Run TaskWarrior commands directly:

```bash
# List tasks
docker run --rm \
  -v taskwarrior-data:/data/taskwarrior \
  -v $(pwd)/config/.taskrc:/config/.taskrc:ro \
  taskwarrior-mcp:latest \
  task list

# Export tasks
docker run --rm \
  -v taskwarrior-data:/data/taskwarrior \
  -v $(pwd)/config/.taskrc:/config/.taskrc:ro \
  taskwarrior-mcp:latest \
  task export
```

### Interactive Mode

```bash
docker run -it --rm \
  -v taskwarrior-data:/data/taskwarrior \
  -v $(pwd)/config/.taskrc:/config/.taskrc \
  taskwarrior-mcp:latest \
  /bin/sh
```

## Optimization

### Layer Caching

The Dockerfile is optimized for layer caching:

1. System packages installed first (changes infrequently)
2. Application dependencies installed next
3. Source code copied last (changes frequently)

### Image Size

```bash
# View image size
docker images taskwarrior-mcp

# Expected: ~294MB
# Includes Fedora 41, TaskWarrior 3.4.1, Python 3.13, and all dependencies
```

## Production Deployment

### Kubernetes

Example deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: taskwarrior-mcp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: taskwarrior-mcp
  template:
    metadata:
      labels:
        app: taskwarrior-mcp
    spec:
      containers:
      - name: mcp-server
        image: taskwarrior-mcp:latest
        env:
        - name: SYNC_GCP_BUCKET
          valueFrom:
            secretKeyRef:
              name: taskwarrior-config
              key: gcp-bucket
        - name: LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: taskwarrior-data
          mountPath: /data/taskwarrior
        - name: config
          mountPath: /config
          readOnly: true
        - name: credentials
          mountPath: /credentials
          readOnly: true
        securityContext:
          runAsUser: 1000
          runAsNonRoot: true
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
        resources:
          limits:
            cpu: "1"
            memory: "512Mi"
          requests:
            cpu: "250m"
            memory: "128Mi"
      volumes:
      - name: taskwarrior-data
        persistentVolumeClaim:
          claimName: taskwarrior-pvc
      - name: config
        configMap:
          name: taskwarrior-config
      - name: credentials
        secret:
          secretName: gcp-credentials
```

### Docker Swarm

```bash
# Create a stack file first, then deploy
docker stack deploy -c stack.yml taskwarrior
```

## Maintenance

### Updating

```bash
# Pull latest code
git pull

# Rebuild image
docker build -t taskwarrior-mcp:latest .

# Restart containers
docker compose down
docker compose up -d
```

### Backup

```bash
# Backup TaskWarrior data
docker run --rm \
  -v taskwarrior-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/taskwarrior-$(date +%Y%m%d).tar.gz /data

# Restore from backup
docker run --rm \
  -v taskwarrior-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/taskwarrior-20260203.tar.gz -C /
```

## License

See LICENSE file for details.
