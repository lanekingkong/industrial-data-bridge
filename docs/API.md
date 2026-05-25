# API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All API requests require authentication via JWT Bearer Token.

```http
Authorization: Bearer <your_jwt_token>
```

### Obtain Token
```http
POST /auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "your_password"
}
```

Response:
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

## API Endpoints

### Devices

#### List all devices
```http
GET /devices
```

Query Parameters:
| Parameter | Type | Description |
|-----------|------|-------------|
| page | int | Page number (default: 1) |
| page_size | int | Items per page (default: 20) |
| protocol | string | Filter by protocol |
| status | string | Filter by status |

Response:
```json
{
    "total": 42,
    "page": 1,
    "page_size": 20,
    "devices": [
        {
            "device_id": "pump_001",
            "name": "Main Water Pump",
            "protocol": "modbus",
            "status": "online",
            "last_seen": "2024-01-15T08:30:00Z",
            "points_count": 12
        }
    ]
}
```

#### Register a new device
```http
POST /devices
Content-Type: application/json

{
    "device_id": "pump_002",
    "name": "Coolant Pump",
    "protocol": "modbus",
    "connection_params": {
        "mode": "tcp",
        "host": "192.168.1.101",
        "port": 502,
        "unit_id": 2
    },
    "points": [
        {
            "name": "temperature",
            "register_type": "holding_register",
            "address": 100,
            "data_type": "float32",
            "unit": "celsius",
            "min": 0,
            "max": 100
        }
    ]
}
```

Response:
```json
{
    "success": true,
    "device": {
        "device_id": "pump_002",
        "name": "Coolant Pump",
        "protocol": "modbus",
        "status": "registered",
        "created_at": "2024-01-15T08:35:00Z"
    }
}
```

#### Get device details
```http
GET /devices/{device_id}
```

Response:
```json
{
    "device_id": "pump_001",
    "name": "Main Water Pump",
    "protocol": "modbus",
    "connection_params": {
        "mode": "tcp",
        "host": "192.168.1.100",
        "port": 502,
        "unit_id": 1
    },
    "points": [...],
    "status": "online",
    "last_seen": "2024-01-15T08:30:00Z",
    "created_at": "2024-01-10T12:00:00Z",
    "updated_at": "2024-01-15T08:30:00Z"
}
```

#### Update device configuration
```http
PUT /devices/{device_id}
Content-Type: application/json

{
    "name": "Main Water Pump v2",
    "connection_params": {
        "host": "192.168.1.200"
    }
}
```

#### Delete device
```http
DELETE /devices/{device_id}
```

Response:
```json
{
    "success": true,
    "message": "Device pump_001 deleted"
}
```

### Data Collection

#### Collect data from all devices
```http
POST /data/collect
```

Response:
```json
{
    "success": true,
    "collected_at": "2024-01-15T08:40:00Z",
    "results": {
        "pump_001": [
            {
                "point_name": "temperature",
                "value": 45.2,
                "unit": "celsius",
                "quality": "good",
                "timestamp": "2024-01-15T08:40:00Z"
            }
        ]
    }
}
```

#### Collect data from specific device
```http
POST /data/collect/{device_id}
```

#### Get historical data
```http
GET /data/history/{device_id}
```

Query Parameters:
| Parameter | Type | Description |
|-----------|------|-------------|
| start_time | ISO 8601 | Start of time range |
| end_time | ISO 8601 | End of time range |
| points | string | Comma-separated point names |
| interval | string | Aggregation interval (1m, 5m, 1h, 1d) |
| aggregation | string | mean, sum, min, max, last |

Response:
```json
{
    "device_id": "pump_001",
    "start_time": "2024-01-15T00:00:00Z",
    "end_time": "2024-01-15T08:40:00Z",
    "interval": "5m",
    "data": [
        {
            "timestamp": "2024-01-15T00:00:00Z",
            "temperature": 42.1,
            "pressure": 5.2,
            "flow_rate": 10.3
        }
    ]
}
```

#### Get latest values
```http
GET /data/latest
```

### AI & Analytics

#### Detect anomalies
```http
POST /ai/anomaly/detect
Content-Type: application/json

{
    "device_id": "pump_001",
    "time_range": {
        "start": "2024-01-15T00:00:00Z",
        "end": "2024-01-15T08:00:00Z"
    }
}
```

Response:
```json
{
    "device_id": "pump_001",
    "anomalies_detected": 3,
    "anomalies": [
        {
            "timestamp": "2024-01-15T03:15:00Z",
            "score": 0.92,
            "deviating_features": [
                {
                    "feature": "temperature",
                    "value": 85.3,
                    "deviation_sigma": 4.2
                }
            ]
        }
    ]
}
```

#### Predict maintenance needs
```http
POST /ai/predict/maintenance
Content-Type: application/json

{
    "device_id": "pump_001"
}
```

Response:
```json
{
    "device_id": "pump_001",
    "failure_probability": 0.15,
    "risk_level": "medium",
    "estimated_rul_hours": 850,
    "recommendation": "Schedule preventive maintenance within 30 days.",
    "prediction_time": "2024-01-15T08:45:00Z"
}
```

#### Train anomaly model
```http
POST /ai/anomaly/train
Content-Type: application/json

{
    "method": "isolation_forest",
    "time_range": {
        "start": "2024-01-01T00:00:00Z",
        "end": "2024-01-14T23:59:59Z"
    },
    "features": ["temperature", "pressure", "flow_rate", "vibration"]
}
```

### Protocol Management

#### Test device connection
```http
POST /protocols/test
Content-Type: application/json

{
    "protocol": "modbus",
    "connection_params": {
        "mode": "tcp",
        "host": "192.168.1.100",
        "port": 502,
        "unit_id": 1
    }
}
```

Response:
```json
{
    "success": true,
    "protocol": "modbus",
    "latency_ms": 12.5,
    "message": "Connection successful"
}
```

#### Browse OPC-UA nodes
```http
GET /protocols/opcua/browse/{device_id}?path=ns=2;s=Devices
```

Response:
```json
{
    "device_id": "opc_server_001",
    "path": "ns=2;s=Devices",
    "nodes": [
        {
            "node_id": "ns=2;s=Devices.Pump1",
            "display_name": "Pump 1",
            "browse_name": "Pump1"
        }
    ]
}
```

### System & Health

#### Health check
```http
GET /health
```

Response:
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 3600,
    "components": {
        "database": "connected",
        "redis": "connected",
        "influxdb": "connected",
        "modbus": "running",
        "opcua": "running"
    }
}
```

#### Metrics
```http
GET /metrics
```

Returns Prometheus-formatted metrics.

## WebSocket API

### Real-time Data Stream
```
ws://localhost:8000/ws/data?token=<jwt_token>
```

Message format:
```json
{
    "type": "data_point",
    "device_id": "pump_001",
    "point_name": "temperature",
    "value": 45.2,
    "unit": "celsius",
    "quality": "good",
    "timestamp": "2024-01-15T08:40:01.500Z"
}
```

### Alert Stream
```
ws://localhost:8000/ws/alerts?token=<jwt_token>
```

Message format:
```json
{
    "type": "alert",
    "severity": "warning",
    "device_id": "pump_001",
    "message": "Temperature exceeding normal range",
    "value": 85.3,
    "threshold": 80.0,
    "timestamp": "2024-01-15T08:40:02Z"
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or expired token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Duplicate resource |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable - Dependency down |

Error response format:
```json
{
    "error": {
        "code": 404,
        "type": "not_found",
        "message": "Device pump_099 not found",
        "request_id": "req_abc123"
    }
}
```

## SDK Example

### Python SDK
```python
from industrial_data_bridge import Client

client = Client(
    base_url="http://localhost:8000",
    token="your_jwt_token"
)

# List devices
devices = client.devices.list()

# Register device
device = client.devices.register(
    device_id="pump_003",
    name="New Pump",
    protocol="modbus",
    connection_params={"host": "192.168.1.102", "port": 502, "mode": "tcp"},
    points=[{"name": "temp", "register_type": "holding_register", "address": 100}]
)

# Collect data
data = client.data.collect("pump_003")

# Detect anomalies
anomalies = client.ai.detect_anomalies("pump_001")

# Predict maintenance
prediction = client.ai.predict_maintenance("pump_001")
```

## Rate Limiting

| Tier | Requests/Minute | Burst |
|------|-----------------|-------|
| Basic | 100 | 200 |
| Standard | 500 | 1000 |
| Enterprise | 5000 | 10000 |

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705305000
```