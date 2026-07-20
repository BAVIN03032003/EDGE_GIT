# Edge Application Deployment Guide

## Overview

This document describes how to deploy and manage the Edge Application on edge devices using Docker containers distributed via GitHub Container Registry (GHCR).

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   GitHub    │     │   GitHub        │     │   RMM Cloud      │
│   Release   │────▶│   Container     │◀───▶│   (Socket.IO)    │
│   (Tags)    │     │   Registry      │     │                  │
└─────────────┘     └─────────────────┘     └──────────────────┘
                           │
                           ▼
                    ┌─────────────────┐
                    │   Edge Device   │
                    │   (Docker)      │
                    │   - Edge App    │
                    │   - Web UI :8080│
                    └─────────────────┘
```

## Prerequisites

### On the Edge Device

1. **Docker Engine** (version 20.10 or higher)
   ```bash
   # Check Docker version
   docker --version
   ```

2. **jq** (for update-watcher script)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install jq

   # RHEL/CentOS
   sudo yum install jq
   ```

3. **curl** (for health checks and API calls)
   ```bash
   # Usually pre-installed on most Linux distributions
   ```

4. **Git** (optional, for manual updates)
   ```bash
   sudo apt-get install git
   ```

## One-Time Setup

### Step 1: Create Directory Structure

```bash
sudo mkdir -p /opt/edge/logs
sudo chmod 755 /opt/edge
sudo chmod 700 /opt/edge/logs
```

### Step 2: Create Configuration File

Create `/opt/edge/.env` with your organization's settings:

```bash
sudo nano /opt/edge/.env
```

Add the following content (replace placeholders):

```env
# RMM Cloud Connection
CLOUD_URL=https://rmm.api.teampresence.in
API_KEY=sk_your_api_key_here
SOCKETIO_PATH=socket.io
SOCKETIO_NAMESPACE=/edge

# Edge Identity
EDGE_NAME=OFFICE-EDGE-001
EDGE_ID=edge_office_001
LOCATION=CHN

# Application Settings
WEB_UI_HOST=0.0.0.0
WEB_UI_PORT=8080
LOG_LEVEL=INFO

# Timing (seconds)
MONITORING_INTERVAL=30
DISCOVERY_INTERVAL=300
COMMAND_CHECK_INTERVAL=5
HEARTBEAT_INTERVAL=60
```

**Security**: Set restrictive permissions:
```bash
sudo chmod 600 /opt/edge/.env
sudo chown root:root /opt/edge/.env
```

### Step 3: Copy Scripts

```bash
sudo cp start.sh /opt/edge/
sudo cp update-watcher.sh /opt/edge/
sudo chmod +x /opt/edge/start.sh
sudo chmod +x /opt/edge/update-watcher.sh
```

### Step 4: Create Log Directory

```bash
sudo mkdir -p /opt/edge/logs
sudo chown 1000:1000 /opt/edge/logs
```

### Step 5: Configure Docker Logging (Optional)

Add to `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker:
```bash
sudo systemctl restart docker
```

## Deployment

### Initial Deployment

```bash
# Pull and start the latest version
sudo VERSION=1.0.0 /opt/edge/start.sh start

# Or use latest tag
sudo /opt/edge/start.sh start
```

### Verify Deployment

```bash
# Check container status
sudo /opt/edge/start.sh status

# View logs
sudo /opt/edge/start.sh logs

# Check health endpoint
curl http://localhost:8080/health
```

### Enable Update Watcher (Background Service)

Create systemd service for auto-updates:

```bash
sudo nano /etc/systemd/system/edge-update-watcher.service
```

Add:
```ini
[Unit]
Description=Edge Application Update Watcher
After=network.target docker.service

[Service]
Type=simple
User=root
EnvironmentFile=/opt/edge/.env
ExecStart=/opt/edge/update-watcher.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable edge-update-watcher.service
sudo systemctl start edge-update-watcher.service

# Check status
sudo systemctl status edge-update-watcher.service
```

## Management Commands

### Start/Stop/Restart

```bash
# Start
sudo /opt/edge/start.sh start

# Stop
sudo /opt/edge/start.sh stop

# Restart
sudo /opt/edge/start.sh restart
```

### Updates

```bash
# Update to specific version
sudo VERSION=1.2.0 /opt/edge/start.sh update

# Or use the default (latest)
sudo /opt/edge/start.sh update
```

### Rollback

```bash
# Rollback to previous version
sudo /opt/edge/start.sh rollback 1.1.0
```

### Logs

```bash
# Follow container logs
sudo /opt/edge/start.sh logs

# View update watcher logs
sudo tail -f /opt/edge/logs/update-watcher.log
```

### Status Check

```bash
# Container status
sudo /opt/edge/start.sh status

# Docker status
sudo docker ps

# Container details
sudo docker inspect edge-app
```

## Automatic Updates

The Edge Application checks for updates on every heartbeat to RMM:

1. Heartbeat runs every `HEARTBEAT_INTERVAL` seconds (default: 60s)
2. Edge calls `GET /api/edge/manifest` to check for new versions
3. If update available:
   - Update pending file is created
   - Update watcher detects the file
   - Graceful restart is performed
   - RMM is notified of success/failure

### Manual Update Check

```bash
# Check current version
sudo docker exec edge-app cat /app/VERSION

# Check latest available (via RMM API)
curl https://rmm.api.teampresence.in/api/edge/manifest
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
sudo /opt/edge/start.sh logs

# Check env file
sudo cat /opt/edge/.env

# Verify env file permissions
ls -la /opt/edge/.env

# Check Docker daemon
sudo systemctl status docker
```

### Network Issues

```bash
# Test RMM connectivity
curl -v https://rmm.api.teampresence.in/api/edge/health

# Check DNS resolution
nslookup rmm.api.teampresence.in

# Test from within container
sudo docker exec edge-app curl -v https://rmm.api.teampresence.in/api/edge/health
```

### Update Failed

```bash
# Check update watcher logs
sudo tail -50 /opt/edge/logs/update-watcher.log

# Check for pending update files
ls -la /opt/edge/*pending* 2>/dev/null || echo "No pending files"

# Manual rollback
sudo /opt/edge/start.sh rollback <previous-version>
```

### Web UI Not Accessible

```bash
# Check if container is running
sudo docker ps | grep edge-app

# Check port binding
sudo netstat -tlnp | grep 8080

# Test locally in container
sudo docker exec edge-app curl http://localhost:8080/health
```

### Reset Edge Device

```bash
# Stop and remove container
sudo docker stop edge-app
sudo docker rm edge-app

# Clear logs (optional)
sudo rm -rf /opt/edge/logs/*
sudo mkdir -p /opt/edge/logs
sudo chown 1000:1000 /opt/edge/logs

# Fresh start
sudo /opt/edge/start.sh start
```

## Security Checklist

- [ ] `.env` file has 600 permissions
- [ ] API key is not committed to any repository
- [ ] Edge device has firewall rules configured
- [ ] Only necessary ports are exposed (8080)
- [ ] Docker socket is not exposed to containers unless necessary
- [ ] Regular security updates are applied to the host OS

## Image Registry

### GHCR Image References

```
ghcr.io/your-org/edge-application:latest          # Latest stable
ghcr.io/your-org/edge-application:1.2.0           # Specific version
ghcr.io/your-org/edge-application:1.2             # Minor version alias
ghcr.io/your-org/edge-application:1               # Major version alias
ghcr.io/your-org/edge-application:sha-abc1234    # Immutable SHA tag
```

### Pull Image Manually

```bash
# Login to GHCR (if needed)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Pull specific version
docker pull ghcr.io/your-org/edge-application:1.2.0

# List available tags
docker search ghcr.io/your-org/edge-application
```

## Backup and Recovery

### Backup

```bash
# Backup configuration
sudo cp /opt/edge/.env /opt/edge/.env.backup

# Backup scripts
sudo tar -czf /opt/edge-backup.tar.gz /opt/edge/start.sh /opt/edge/update-watcher.sh

# Export container state
sudo docker commit edge-app edge-backup:$(date +%Y%m%d)
```

### Recovery

```bash
# Restore configuration
sudo cp /opt/edge/.env.backup /opt/edge/.env
sudo chmod 600 /opt/edge/.env

# Restore container from backup image
sudo docker run -d \
  --name edge-app \
  --restart unless-stopped \
  --env-file /opt/edge/.env \
  -p 8080:8080 \
  edge-backup:20240417
```

## Monitoring

### Health Checks

```bash
# Local health check
curl http://localhost:8080/health

# Remote health check (from RMM)
curl https://rmm.api.teampresence.in/api/edge/health
```

### Log Rotation

Configure logrotate for container logs:

```bash
sudo nano /etc/logrotate.d/edge-logs
```

Add:
```
/opt/edge/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        docker kill -s USR1 edge-app > /dev/null 2>&1 || true
    endscript
}
```

## Support

For issues:
1. Check logs: `sudo /opt/edge/start.sh logs`
2. Check update watcher: `sudo tail -f /opt/edge/logs/update-watcher.log`
3. Report to RMM admin with:
   - Edge ID
   - Current version
   - Error messages from logs
   - Steps to reproduce

## Version Information

- **Document Version**: 1.0.0
- **Last Updated**: 2026-04-17
- **Edge Application**: Version 1.0.0+
- **RMM API Version**: v1
