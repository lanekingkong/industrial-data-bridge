"""
Industrial Data Bridge - API Routes
RESTful API endpoints for device management, data collection, and monitoring.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Models ---
class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Human-readable device name")
    protocol: str = Field(..., pattern="^(modbus|opcua|mqtt|http)$")
    connection_params: Dict[str, Any]
    description: str = ""
    tags: Dict[str, str] = {}
    points: List[Dict[str, Any]] = []

class PointData(BaseModel):
    name: str
    value: Any
    quality: str = "good"

class DeviceResponse(BaseModel):
    id: str; name: str; protocol: str
    status: str; is_connected: bool; collection_count: int


# --- Helper: get engine ---
def _engine(request: Request):
    return request.app.state.engine


# --- Health & Status ---
@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}

@router.get("/status")
async def system_status(request: Request):
    engine = _engine(request)
    return await engine.get_status()

# --- Device Management ---
@router.post("/devices", status_code=201)
async def register_device(req: DeviceRegisterRequest, request: Request):
    engine = _engine(request)
    try:
        did = await engine.register_device(
            device_id=req.device_id, name=req.name, protocol=req.protocol,
            connection_params=req.connection_params, description=req.description,
            tags=req.tags, points=req.points,
        )
        return {"device_id": did, "message": "Device registered"}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/devices", response_model=List[DeviceResponse])
async def list_devices(
    request: Request,
    status: Optional[str] = Query(None),
    protocol: Optional[str] = Query(None),
):
    engine = _engine(request)
    return engine.list_devices(status=status, protocol=protocol)

@router.get("/devices/{device_id}")
async def get_device(device_id: str, request: Request):
    engine = _engine(request)
    dev = engine.get_device(device_id)
    if not dev:
        raise HTTPException(404, "Device not found")
    return dev

@router.delete("/devices/{device_id}")
async def remove_device(device_id: str, request: Request):
    engine = _engine(request)
    ok = await engine.unregister_device(device_id)
    if not ok:
        raise HTTPException(404, "Device not found")
    return {"message": "Device removed"}

# --- Connection Management ---
@router.post("/devices/{device_id}/connect")
async def connect_device(device_id: str, request: Request):
    engine = _engine(request)
    ok = await engine.connect_device(device_id)
    if not ok:
        raise HTTPException(400, "Connection failed")
    return {"message": "Connected", "device_id": device_id}

@router.post("/devices/{device_id}/disconnect")
async def disconnect_device(device_id: str, request: Request):
    engine = _engine(request)
    await engine.disconnect_device(device_id)
    return {"message": "Disconnected", "device_id": device_id}

# --- Data Collection ---
@router.post("/devices/{device_id}/collect", response_model=List[PointData])
async def collect_data(
    device_id: str,
    request: Request,
    point_names: Optional[List[str]] = Query(None),
):
    engine = _engine(request)
    try:
        return await engine.collect_device_data(device_id, point_names)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except ConnectionError as e:
        raise HTTPException(503, str(e))

@router.post("/devices/{device_id}/write")
async def write_to_device(device_id: str, point_name: str = Query(...),
                          value: Any = Query(...), request: Request = None):
    engine = _engine(request)
    try:
        ok = await engine.write_to_device(device_id, point_name, value)
        return {"success": ok, "device_id": device_id, "point": point_name, "value": value}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except ConnectionError as e:
        raise HTTPException(503, str(e))

# --- Data Query ---
@router.get("/devices/{device_id}/data")
async def get_device_data(
    device_id: str,
    request: Request,
    point_name: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=10000),
):
    from src.utils.database import db
    rows = await db.query_data_points(device_id, point_name, start_time, end_time, limit)
    return {"device_id": device_id, "count": len(rows), "data": rows}

@router.get("/metrics")
async def get_metrics(request: Request):
    from src.utils.database import db
    stats = await db.get_system_stats()
    engine = _engine(request)
    es = await engine.get_status()
    stats["engine"] = es
    return stats

# --- Edge ---
@router.post("/edge/sync")
async def edge_sync(data: List[Dict[str, Any]], request: Request):
    from src.utils.database import db
    synced = 0
    for item in data:
        await db.insert_data_point(item.get("device_id", ""), item.get("name", ""),
                                   item.get("value"), item.get("unit", ""), item.get("quality", "good"))
        synced += 1
    return {"synced": synced, "timestamp": datetime.now().isoformat()}