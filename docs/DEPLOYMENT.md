# Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Deploy (Docker)](#quick-deploy-docker)
3. [Manual Deployment](#manual-deployment)
4. [Production Configuration](#production-configuration)
5. [High Availability](#high-availability)
6. [Edge Deployment](#edge-deployment)
7. [Monitoring](#monitoring)
8. [Backup & Recovery](#backup--recovery)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware Requirements

| Environment | CPU | RAM | Storage | Network |
|-------------|-----|-----|---------|---------|
| Development | 2 cores | 4 GB | 20 GB SSD | 100 Mbps |
| Production (Small) | 4 cores | 8 GB | 50 GB SSD | 1 Gbps |
| Production (Medium) | 8 cores | 16 GB | 200 GB SSD | 1 Gbps |
| Production (Large) | 16+ cores | 32+ GB | 500+ GB SSD | 10 Gbps |
| Edge Node | 2 cores | 2 GB | 10 GB | 100 Mbps |

### Software Requirements

- **OS**: Ubuntu 20.04+, CentOS 8+, RHEL 8+, Windows Server 2019+
- **Docker**: 20.10+ with compose plugin
- **Python**: 3.8+ (manual deployment only)
- **PostgreSQL**: 12+ (if not using Docker)

## Quick Deploy (Docker)

### Step 1: Clone Repository

```bash
git clone https://github.com/industrial-data-bridge/industrial-data-bridge.git
cd industrial-data-bridge
```

### Step 2: Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
nano .env
```

Essential configurations:
```bash
# Security (MUST change!)
JWT_SECRET_KEY=generate-a-random-key-here
POSTGRES_PASSWORD=strong-password-here
INFLUXDB_TOKEN=another-strong-token

# Network
APP_PORT=8000
MODBUS_DEFAULT_PORT=5020
```

### Step 3: Start Services

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f bridge-core
```

### Step 4: Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Access Grafana dashboard
open http://localhost:3000  # Default: admin/admin

# Access MinIO console
open http://localhost:9001  # Default: minioadmin/minioadmin
```

## Manual Deployment

### Step 1: Install Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv \
    postgresql postgresql-client redis-server \
    build-essential libssl-dev

# Create PostgreSQL database
sudo -u postgres psql
CREATE DATABASE industrial_bridge;
CREATE USER bridge_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE industrial_bridge TO bridge_user;
\q
```

### Step 2: Set Up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev,ai,edge]"
```

### Step 3: Initialize Database

```bash
# Copy and edit env
cp .env.example .env
nano .env

# Initialize
python scripts/init_db.py
```

### Step 4: Configure Systemd Service

```bash
sudo nano /etc/systemd/system/industrial-data-bridge.service
```

```
[Unit]
Description=Industrial Data Bridge
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=bridge
WorkingDirectory=/opt/industrial-data-bridge
Environment=BRIDGE_ENV_FILE=/opt/industrial-data-bridge/.env
ExecStart=/opt/industrial-data-bridge/venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable industrial-data-bridge
sudo systemctl start industrial-data-bridge
```

## Production Configuration

### Security Hardening

```bash
# Generate secure random keys
python -c "import secrets; print(secrets.token_hex(32))"

# Update .env with generated values
JWT_SECRET_KEY=<generated_key>
ENCRYPTION_KEY=<generated_key_32_bytes>
```

### SSL/TLS Configuration

Using Nginx as reverse proxy:

```nginx
server {
    listen 443 ssl http2;
    server_name bridge.example.com;

    ssl_certificate     /etc/ssl/certs/bridge.crt;
    ssl_certificate_key /etc/ssl/private/bridge.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Resource Limits

```yaml
# docker-compose.override.yml
services:
  bridge-core:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '2'
          memory: 2G
```

### Logging Configuration

```bash
# Docker logging
docker-compose logs -f --tail=100 bridge-core

# Configure log rotation in .env
LOG_LEVEL=INFO
LOG_FILE=./logs/bridge.log
LOG_ROTATION=100MB
LOG_RETENTION=30 days
```

## High Availability

### PostgreSQL Replication

```yaml
# docker-compose-ha.yml
services:
  postgres-primary:
    image: postgres:15
    environment:
      POSTGRES_DB: industrial_bridge
      POSTGRES_USER: bridge_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres-primary-data:/var/lib/postgresql/data

  postgres-replica:
    image: postgres:15
    environment:
      POSTGRES_DB: industrial_bridge
      POSTGRES_MASTER_SERVICE_HOST: postgres-primary
    depends_on:
      - postgres-primary
    volumes:
      - postgres-replica-data:/var/lib/postgresql/data
```

### Redis Cluster

```yaml
  redis-node-1:
    image: redis:7
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf

  redis-node-2:
    image: redis:7
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf

  redis-node-3:
    image: redis:7
    command: redis-server --cluster-enabled yes --cluster-config-file nodes.conf
```

### Load Balancing

Using Docker Swarm or Kubernetes:

```yaml
# docker stack deploy
services:
  bridge-core:
    image: industrialdatabridge/core:latest
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
      update_config:
        parallelism: 1
        delay: 10s
```

## Edge Deployment

### Docker-based Edge

```bash
# On edge device
docker run -d \
    --name idb-edge \
    --network host \
    -v /opt/idb/config:/app/config:ro \
    -v /data/idb:/data/edge \
    -e EDGE_ENABLED=true \
    -e BRIDGE_ENV_FILE=/app/config/.env \
    industrialdatabridge/edge:latest
```

### Bare-metal Edge

```bash
# Clone or copy the repo
git clone https://github.com/industrial-data-bridge/industrial-data-bridge.git
cd industrial-data-bridge

# Install minimal dependencies
pip install -e ".[edge]"

# Configure edge mode
export EDGE_ENABLED=true
export EDGE_DATA_PATH=/data/idb

# Start edge agent
python -m src.edge.agent
```

## Monitoring

### Prometheus Metrics

Available at `http://localhost:9090/metrics`:

```prometheus
# Key metrics
idb_devices_connected_total
idb_data_points_collected_total
idb_data_collection_latency_seconds
idb_anomalies_detected_total
idb_model_inference_latency_seconds
idb_db_connection_pool_size
```

### Grafana Dashboards

Import pre-built dashboards:
- `dashboards/device-overview.json` - Device status and metrics
- `dashboards/anomaly-detection.json` - Anomaly trends
- `dashboards/system-health.json` - Infrastructure monitoring

### Alerting Rules

```yaml
# Prometheus alert rules
groups:
  - name: industrial_bridge
    rules:
      - alert: HighAnomalyRate
        expr: rate(idb_anomalies_detected_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High anomaly detection rate"

      - alert: DeviceOffline
        expr: idb_device_status == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Device {{ $labels.device_id }} is offline"
```

## Backup & Recovery

### Database Backup

```bash
# PostgreSQL backup
pg_dump -h localhost -U bridge_user industrial_bridge > backup_$(date +%Y%m%d).sql

# InfluxDB backup
influx backup /backup/influxdb -t ${INFLUXDB_TOKEN}

# Automated backup script
```bash
#!/bin/bash
# scripts/backup.sh
BACKUP_DIR="/backups/industrial-bridge/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
pg_dump -h localhost -U bridge_user industrial_bridge > $BACKUP_DIR/postgres.sql

# Backup InfluxDB
influx backup $BACKUP_DIR/influxdb -t $INFLUXDB_TOKEN

# Backup configs
cp .env $BACKUP_DIR/.env.backup

# Cleanup old backups (keep 30 days)
find /backups/industrial-bridge -type d -mtime +30 -exec rm -rf {} \;
```

### Recovery

```bash
# PostgreSQL restore
psql -h localhost -U bridge_user industrial_bridge < backup.sql

# InfluxDB restore
influx restore /backup/influxdb -t ${INFLUXDB_TOKEN}
```

## Troubleshooting

### Common Issues

**Service won't start**
```bash
# Check logs
docker-compose logs bridge-core

# Check port conflicts
netstat -tulpn | grep -E "8000|5432|6379|8086"

# Reset and rebuild
docker-compose down -v
docker-compose up -d --build
```

**Database connection errors**
```bash
# Verify PostgreSQL is running
docker exec idb-postgres pg_isready

# Check credentials
docker exec idb-postgres psql -U bridge_user -d industrial_bridge -c "SELECT 1"
```

**Device connection issues**
```bash
# Test Modbus connection
python -c "
from pymodbus.client import AsyncModbusTcpClient
client = AsyncModbusTcpClient('192.168.1.100', port=502)
print(client.connect())
"

# Check firewall
sudo ufw status
sudo iptables -L -n | grep 502
```

**Performance issues**
```bash
# Monitor resource usage
docker stats

# Check database query performance
docker exec idb-postgres psql -U bridge_user -d industrial_bridge -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC
LIMIT 10;"
```

### Debug Mode

```bash
# Enable debug mode
export APP_DEBUG=true
export LOG_LEVEL=DEBUG

# Run with verbose output
python -m src.main --debug --log-level DEBUG
```

### Support

If issues persist:
1. Check [GitHub Issues](https://github.com/industrial-data-bridge/industrial-data-bridge/issues)
2. Run diagnostic script: `python scripts/diagnose.py`
3. Open an issue with diagnostic output attached