# Dockerfile for TaskWarrior MCP Server
# Uses Fedora with TaskWarrior from package manager

FROM fedora:41

LABEL maintainer="TaskWarrior MCP Server"
LABEL description="MCP Server for TaskWarrior"
LABEL version="0.1.0"

# Install Python, TaskWarrior, tini, pip, and create non-root user in a single layer
RUN dnf install -y --setopt=install_weak_deps=False \
        python3 \
        python3-pip \
        task \
        tini && \
    dnf clean all && \
    rm -rf /var/cache/dnf && \
    useradd -u 1000 -m -s /bin/bash taskuser && \
    mkdir -p /data/taskwarrior /config /app && \
    chown -R taskuser:taskuser /data/taskwarrior /config /app

# Copy application source code
WORKDIR /app
COPY --chown=taskuser:taskuser src/ ./src/
COPY --chown=taskuser:taskuser pyproject.toml README.md ./

# Install Python dependencies and the application
RUN python3 -m pip install --no-cache-dir --break-system-packages -e .

# Set up environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TASKRC=/config/.taskrc \
    TASKDATA=/data/taskwarrior \
    TASK_COMMAND=task \
    LOG_LEVEL=INFO

# Switch to non-root user
USER taskuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD task --version || exit 1

# Use tini for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command: run the MCP server
CMD ["python3", "-m", "taskwarriormcp.server"]
