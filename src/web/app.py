"""
Industrial Data Bridge - Web API Service

FastAPI-based REST and WebSocket API for device management,
data collection, and AI analytics.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import jwt
from jwt.exceptions import InvalidTokenError

from src.core import BridgeEngine, BridgeConfig
from src.core.config import DatabaseSettings, InfluxDBSettings, RedisSettings, SecuritySettings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()
JWT_SECRET = None
JWT_ALGORITHM = "HS256"

# Global engine instance
engine: Optional[BridgeEngine] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    global engine
    
    # Startup
    logger.info("Starting Industrial Data Bridge API...")
    
    # Load configuration
    config = BridgeConfig()
    
    # Initialize engine
    engine = BridgeEngine(config)
    await engine.initialize()
    await engine.start_background_tasks()
    
    # Set JWT secret
    global JWT_SECRET
    JWT_SECRET = config.security.jwt_secret_key
    
    logger.info(f"API started on port {config.server.port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Industrial Data Bridge API...")
    if engine:
        await engine.stop()
    logger.info("API shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Industrial Data Bridge API",
    description="AI-powered industrial device data collection and protocol conversion",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class DeviceRegistration(BaseModel):
    """Device registration request."""
    device_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    protocol: str = Field(..., pattern="^(modbus|opcua|mqtt|http)$")
    connection_params: Dict[str, Any] = Field(...)
    points: List[Dict[str, Any]] = Field(default_factory=list)
    
    @validator("connection_params")
    def validate_connection_params(cls, v, values):
        protocol = values.get("protocol")
        if protocol == "modbus":
            required = ["mode", "host", "port"]
            if "mode" in v and v["mode"] == "rtu":
                required.append("port")
        elif protocol == "opcua":
            required = ["endpoint_url"]
        elif protocol == "mqtt":
            required = ["host", "port"]
        elif protocol == "http":
            required = ["base_url"]
        
        for field in required:
            if field not in v:
                raise ValueError(f"Missing required field for {protocol}: {field}")
        return v

class DataCollectionRequest(BaseModel):
    """Data collection request."""
    device_ids: Optional[List[str]] = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)

class AnomalyDetectionRequest(BaseModel):
    """Anomaly detection request."""
    device_id: str
    time_range: Dict[str, datetime]
    features: Optional[List[str]] = None

class PredictiveMaintenanceRequest(BaseModel):
    """Predictive maintenance request."""
    device_id: str
    lookahead_hours: int = Field(default=24, ge=1, le=720)

class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str

class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# Authentication
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Health endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "components": {
            "engine": "running" if engine.is_running else "stopped",
            "devices": len(engine.devices) if engine.devices else 0,
            "protocols": list(engine.protocol_adapters.keys()),
        }
    }
    return health_status

# Authentication endpoints
@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login and get JWT token."""
    import os
    admin_user = os.getenv("IDB_ADMIN_USER", "admin")
    admin_pass = os.getenv("IDB_ADMIN_PASSWORD", "admin")
    if request.username != admin_user or request.password != admin_pass:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate token
    payload = {
        "sub": request.username,
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return TokenResponse(
        access_token=token,
        expires_in=24 * 3600
    )

# Device management endpoints
@app.get("/devices")
async def list_devices(
    page: int = 1,
    page_size: int = 20,
    protocol: Optional[str] = None,
    status: Optional[str] = None,
    user: Dict[str, Any] = Depends(verify_token)
):
    """List all registered devices."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    devices = engine.devices.values()
    
    # Apply filters
    if protocol:
        devices = [d for d in devices if d.get("protocol") == protocol]
    if status:
        devices = [d for d in devices if d.get("status") == status]
    
    # Pagination
    total = len(devices)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = devices[start:end]
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "devices": paginated
    }

@app.post("/devices", status_code=status.HTTP_201_CREATED)
async def register_device(
    device: DeviceRegistration,
    user: Dict[str, Any] = Depends(verify_token)
):
    """Register a new device."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        await engine.register_device(**device.dict())
        return {
            "success": True,
            "device": {
                "device_id": device.device_id,
                "name": device.name,
                "protocol": device.protocol,
                "status": "registered",
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Device registration failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/devices/{device_id}")
async def get_device(
    device_id: str,
    user: Dict[str, Any] = Depends(verify_token)
):
    """Get device details."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    device = engine.devices.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    return device

@app.put("/devices/{device_id}")
async def update_device(
    device_id: str,
    update_data: Dict[str, Any],
    user: Dict[str, Any] = Depends(verify_token)
):
    """Update device configuration."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    device = engine.devices.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    # Update logic (simplified)
    device.update(update_data)
    return {"success": True, "message": f"Device {device_id} updated"}

@app.delete("/devices/{device_id}")
async def delete_device(
    device_id: str,
    user: Dict[str, Any] = Depends(verify_token)
):
    """Delete a device."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    if device_id not in engine.devices:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    await engine.unregister_device(device_id)
    return {"success": True, "message": f"Device {device_id} deleted"}

# Data collection endpoints
@app.post("/data/collect")
async def collect_data(
    request: DataCollectionRequest,
    user: Dict[str, Any] = Depends(verify_token)
):
    """Collect data from devices."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        if request.device_ids:
            results = {}
            for device_id in request.device_ids:
                data = await engine.collect_device(device_id)
                results[device_id] = data
        else:
            results = await engine.collect_all_devices()
        
        return {
            "success": True,
            "collected_at": datetime.utcnow().isoformat() + "Z",
            "results": results
        }
    except Exception as e:
        logger.error(f"Data collection failed: {e}")
        raise HTTPException(status_code=500, detail="Data collection failed")

@app.get("/data/history/{device_id}")
async def get_history(
    device_id: str,
    start_time: datetime,
    end_time: datetime,
    points: Optional[str] = None,
    interval: str = "5m",
    aggregation: str = "mean",
    user: Dict[str, Any] = Depends(verify_token)
):
    """Get historical data for a device."""
    # Simplified - in production, query InfluxDB
    return {
        "device_id": device_id,
        "start_time": start_time.isoformat() + "Z",
        "end_time": end_time.isoformat() + "Z",
        "interval": interval,
        "aggregation": aggregation,
        "data": []  # Placeholder
    }

@app.get("/data/latest")
async def get_latest_data(
    device_id: Optional[str] = None,
    user: Dict[str, Any] = Depends(verify_token)
):
    """Get latest data values."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    if device_id:
        data = await engine.collect_device(device_id)
        return {device_id: data}
    else:
        data = await engine.collect_all_devices()
        return data

# AI endpoints
@app.post("/ai/anomaly/detect")
async def detect_anomalies(
    request: AnomalyDetectionRequest,
    user: Dict[str, Any] = Depends(verify_token)
):
    """Detect anomalies in device data."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        # Simplified - in production, call AI module
        anomalies = {
            "device_id": request.device_id,
            "anomalies_detected": 0,
            "anomalies": []
        }
        return anomalies
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise HTTPException(status_code=500, detail="Anomaly detection failed")

@app.post("/ai/predict/maintenance")
async def predict_maintenance(
    request: PredictiveMaintenanceRequest,
    user: Dict[str, Any] = Depends(verify_token)
):
    """Predict maintenance needs."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        # Simplified - in production, call AI module
        prediction = {
            "device_id": request.device_id,
            "failure_probability": 0.15,
            "risk_level": "medium",
            "estimated_rul_hours": 850,
            "recommendation": "Schedule preventive maintenance within 30 days.",
            "prediction_time": datetime.utcnow().isoformat() + "Z"
        }
        return prediction
    except Exception as e:
        logger.error(f"Maintenance prediction failed: {e}")
        raise HTTPException(status_code=500, detail="Maintenance prediction failed")

# Protocol endpoints
@app.post("/protocols/test")
async def test_protocol_connection(
    protocol: str,
    connection_params: Dict[str, Any],
    user: Dict[str, Any] = Depends(verify_token)
):
    """Test protocol connection."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    
    try:
        # Simplified - in production, create adapter and test
        return {
            "success": True,
            "protocol": protocol,
            "latency_ms": 12.5,
            "message": "Connection successful"
        }
    except Exception as e:
        logger.error(f"Protocol test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Protocol test failed: {e}")

# WebSocket endpoints
class ConnectionManager:
    """Manage WebSocket connections."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/data")
async def websocket_data(websocket: WebSocket, token: str):
    """WebSocket for real-time data streaming."""
    # Verify token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except InvalidTokenError:
        await websocket.close(code=1008)
        return
    
    await manager.connect(websocket)
    try:
        while True:
            # In production, push real data
            await asyncio.sleep(1)
            message = {
                "type": "data_sample",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": "Real-time data stream"
            }
            await websocket.send_json(message)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Metrics endpoint (Prometheus format)
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not engine:
        return ""
    
    metrics_lines = [
        "# HELP idb_devices_connected_total Total connected devices",
        "# TYPE idb_devices_connected_total gauge",
        f"idb_devices_connected_total {len(engine.devices)}",
        "",
        "# HELP idb_data_points_collected_total Total data points collected",
        "# TYPE idb_data_points_collected_total counter",
        "idb_data_points_collected_total 0",  # Placeholder
    ]
    
    return "\n".join(metrics_lines)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    
    # Get port from config
    config = BridgeConfig()
    uvicorn.run(
        "src.web.app:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
        log_level="info"
    )