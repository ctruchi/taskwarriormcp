FROM fedora:41

# Install TaskWarrior and create non-root user in a single layer
RUN dnf install -y --setopt=install_weak_deps=False task && \
    dnf clean all && \
    rm -rf /var/cache/dnf && \
    useradd -u 1000 -m -s /bin/bash taskuser && \
    mkdir -p /data/taskwarrior && \
    chown -R taskuser:taskuser /data/taskwarrior

#COPY .taskrc /config/.taskrc

# Set up TaskWarrior environment
ENV TASKRC=/config/.taskrc
ENV TASKDATA=/data/taskwarrior

# Switch to non-root user
USER taskuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=1 \
    CMD task --version || exit 1

# Default command
ENTRYPOINT ["task"]
