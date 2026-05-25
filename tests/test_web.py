import pytest
from src.web.app import create_app
from fastapi.testclient import TestClient
import json

def test_app_creation():
    """Test FastAPI application creation."""
    app = create_app()
    assert app.title == "Industrial Data Bridge API"
    assert app.version == "1.0.0"
    assert "openapi" in app.openapi()

def test_health_endpoint():
    """Test health check endpoint."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data

def test_device_endpoints():
    """Test device management endpoints."""
    app = create_app()
    client = TestClient(app)
    
    # Test device listing (empty initially)
    response = client.get("/api/v1/devices")
    assert response.status_code == 200
    devices = response.json()
    assert isinstance(devices, list)
    
    # Test device registration
    device_data = {
        "device_id": "test_device_001",
        "name": "Test Device",
        "protocol": "modbus",
        "connection_params": {
            "mode": "tcp",
            "host": "192.168.1.100",
            "port": 502,
            "unit_id": 1
        },
        "points": [
            {
                "name": "temperature",
                "register_type": "holding_register",
                "address": 100,
                "data_type": "float32",
                "unit": "celsius"
            }
        ]
    }
    
    response = client.post("/api/v1/devices", json=device_data)
    assert response.status_code in [200, 201]
    
    # Verify device was added
    response = client.get("/api/v1/devices")
    devices = response.json()
    assert len(devices) > 0
    assert any(d["device_id"] == "test_device_001" for d in devices)
    
    # Test device retrieval
    response = client.get("/api/v1/devices/test_device_001")
    assert response.status_code == 200
    device = response.json()
    assert device["device_id"] == "test_device_001"
    assert device["name"] == "Test Device"
    
    # Test device data collection
    response = client.post("/api/v1/devices/test_device_001/collect")
    assert response.status_code == 200
    data = response.json()
    assert "device_id" in data
    assert "data_points" in data
    
    # Test device deletion
    response = client.delete("/api/v1/devices/test_device_001")
    assert response.status_code == 200
    
    # Verify device was removed
    response = client.get("/api/v1/devices/test_device_001")
    assert response.status_code == 404

def test_data_endpoints():
    """Test data query endpoints."""
    app = create_app()
    client = TestClient(app)
    
    # Test data query with parameters
    params = {
        "device_id": "test_device",
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-02T00:00:00Z",
        "limit": 100
    }
    
    response = client.get("/api/v1/data", params=params)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Test data aggregation
    agg_params = {
        "device_id": "test_device",
        "metric": "temperature",
        "aggregation": "avg",
        "interval": "1h",
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-02T00:00:00Z"
    }
    
    response = client.get("/api/v1/data/aggregate", params=agg_params)
    assert response.status_code == 200
    aggregated = response.json()
    assert isinstance(aggregated, list)
    if len(aggregated) > 0:
        assert "timestamp" in aggregated[0]
        assert "value" in aggregated[0]

def test_ai_endpoints():
    """Test AI/ML endpoints."""
    app = create_app()
    client = TestClient(app)
    
    # Test anomaly detection
    anomaly_data = {
        "device_id": "test_device",
        "data": [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 25.5},
            {"timestamp": "2024-01-01T01:00:00Z", "value": 26.0},
            {"timestamp": "2024-01-01T02:00:00Z", "value": 100.0}  # Anomaly
        ],
        "metric": "temperature"
    }
    
    response = client.post("/api/v1/ai/anomaly", json=anomaly_data)
    assert response.status_code == 200
    result = response.json()
    assert "anomalies" in result
    assert "scores" in result
    
    # Test predictive maintenance
    pm_data = {
        "device_id": "test_device",
        "features": {
            "temperature": 75.5,
            "pressure": 120.0,
            "vibration": 0.8,
            "current": 15.2,
            "rpm": 1450
        }
    }
    
    response = client.post("/api/v1/ai/predict", json=pm_data)
    assert response.status_code == 200
    prediction = response.json()
    assert "probability" in prediction
    assert "ttf_hours" in prediction
    assert "alert" in prediction

def test_websocket_endpoint():
    """Test WebSocket endpoint for real-time data."""
    app = create_app()
    client = TestClient(app)
    
    # Note: TestClient doesn't fully support WebSocket testing
    # This is a placeholder for actual WebSocket tests
    with client.websocket_connect("/api/v1/ws") as websocket:
        # Send subscription message
        websocket.send_json({"action": "subscribe", "device_id": "test_device"})
        # Receive initial data
        data = websocket.receive_json()
        assert "type" in data
        assert data["type"] == "connected"

def test_error_handling():
    """Test error responses and validation."""
    app = create_app()
    client = TestClient(app)
    
    # Test non-existent endpoint
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    
    # Test invalid device ID
    response = client.get("/api/v1/devices/invalid_device_id")
    assert response.status_code == 404
    
    # Test invalid data query
    invalid_params = {
        "start_time": "invalid-date",
        "end_time": "also-invalid"
    }
    response = client.get("/api/v1/data", params=invalid_params)
    assert response.status_code == 422  # Validation error
    
    # Test malformed JSON
    response = client.post("/api/v1/devices", data="invalid json")
    assert response.status_code == 422

if __name__ == "__main__":
    pytest.main([__file__, "-v"])