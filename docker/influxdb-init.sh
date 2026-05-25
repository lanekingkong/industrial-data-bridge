#!/bin/bash
# InfluxDB 2.x initialization script for Industrial Data Bridge
# Creates buckets and tokens for time-series data

set -e

echo "Initializing InfluxDB for Industrial Data Bridge..."

# Wait for InfluxDB to be ready
until influx ping --host "http://localhost:8086" 2>/dev/null; do
  echo "Waiting for InfluxDB to be ready..."
  sleep 2
done

echo "InfluxDB is ready, setting up buckets..."

# Create additional buckets using the API
INFLUX_HOST="http://localhost:8086"
ORG="${DOCKER_INFLUXDB_INIT_ORG:-idb}"
TOKEN="${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN:-dev-token-123}"

# Buckets to create
BUCKETS=(
  "device_metrics:Device metrics and sensor data"
  "device_events:Device events and alarms"
  "anomaly_scores:Anomaly detection scores and classifications"
  "maintenance_predictions:Predictive maintenance RUL estimates"
  "system_metrics:System and edge agent metrics"
  "raw_data:Raw data archive for auditing"
)

for bucket_def in "${BUCKETS[@]}"; do
  IFS=':' read -r name description <<< "$bucket_def"
  
  # Create bucket with infinite retention (managed by downsampling tasks)
  influx bucket create \
    --host "$INFLUX_HOST" \
    --org "$ORG" \
    --token "$TOKEN" \
    --name "$name" \
    --description "$description" \
    --retention 0 || echo "Bucket '$name' may already exist"
done

# Create a read-only token for Grafana
influx auth create \
  --host "$INFLUX_HOST" \
  --org "$ORG" \
  --token "$TOKEN" \
  --description "Grafana read token" \
  --read-buckets \
  --write-buckets=false || echo "Grafana token may already exist"

echo "InfluxDB initialization complete!"
echo "Available buckets:"
influx bucket list --host "$INFLUX_HOST" --org "$ORG" --token "$TOKEN" --name