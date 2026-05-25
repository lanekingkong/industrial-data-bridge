"""
Industrial Data Bridge - Core Bridge Engine
Manages device registration, connection, data collection, and health monitoring.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum

from src.protocols.modbus_adapter import ModbusAdapter
from src.protocols.opcua_adapter import OPCUAAdapter
from src.protocols.mqtt_adapter import MQTTAdapter
from src.protocols.http_adapter import HTTPAdapter
from src.utils.database import db
from src.utils.redis_client import RedisManager
from src.utils.config import get_config

logger = logging.getLogger(__name__)


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    UNKNOWN = "unknown"


class ProtocolType(str, Enum):
    MODBUS = "modbus"
    OPCUA = "opcua"
    MQTT = "mqtt"
    HTTP = "http"


class DeviceConnection:
    """Tracks device connection state."""
    __slots__ = ("device_id", "name", "protocol", "status", "connection_params",
                 "points", "tags", "adapter", "last_collection", "collection_count",
                 "error_count", "consecutive_errors", "is_connected", "last_seen")

    def __init__(self, record):
        self.device_id = record.get("device_id")
        self.name = record.get("name", "")
        self.protocol = record.get("protocol", "unknown")
        self.status = record.get("status", "unknown")
        self.connection_params = record.get("connection_params", {})
        self.points = record.get("points", [])
        self.tags = record.get("tags", {})
        self.adapter = None
        self.last_collection = None
        self.collection_count = 0
        self.error_count = 0
        self.consecutive_errors = 0
        self.is_connected = False
        self.last_seen = None


class BridgeEngine:
    """Main bridge engine for device management and data collection."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config()
        # Normalize config: BridgeConfig object or dict
        if hasattr(self.config, 'get'):
            self._cfg = self.config
        else:
            self._cfg = self._bridge_config_to_dict(self.config)
        self.engine_config = self._get_cfg("engine", {})
        self.devices: Dict[str, DeviceConnection] = {}
        self.protocol_adapters: Dict[str, Any] = {}
        self.tasks: Set[asyncio.Task] = set()
        self.running = False
        self.stats = {"start_time": None, "data_points_collected": 0, "collection_errors": 0}
        self.redis: Optional[RedisManager] = None
        adapter_cfg = self._get_cfg("protocols", {})
        if adapter_cfg.get("modbus", {}).get("enabled", True):
            self.protocol_adapters["modbus"] = ModbusAdapter
        if adapter_cfg.get("opcua", {}).get("enabled", True):
            self.protocol_adapters["opcua"] = OPCUAAdapter
        if adapter_cfg.get("mqtt", {}).get("enabled", True):
            self.protocol_adapters["mqtt"] = MQTTAdapter
        if adapter_cfg.get("http", {}).get("enabled", True):
            self.protocol_adapters["http"] = HTTPAdapter

    def _get_cfg(self, key: str, default=None):
        """Unified config access for both dict and BridgeConfig."""
        if hasattr(self._cfg, key):
            return getattr(self._cfg, key, default)
        return self._cfg.get(key, default)

    @staticmethod
    def _bridge_config_to_dict(cfg) -> dict:
        """Convert BridgeConfig object to dictionary."""
        result = {}
        for attr_name in dir(cfg):
            if attr_name.startswith('_'):
                continue
            attr = getattr(cfg, attr_name, None)
            if attr is not None and hasattr(attr, '__dict__'):
                result[attr_name] = {k: v for k, v in attr.__dict__.items() if not k.startswith('_')}
        return result

    async def initialize(self):
        redis_cfg = self._get_cfg("redis", {})
        if isinstance(redis_cfg, dict):
            self.redis = RedisManager(redis_cfg)
        else:
            self.redis = RedisManager(redis_cfg.__dict__)
        await self.redis.initialize()
        try:
            # Simulate DB load for now
            logger.info("DB load simulated - no actual devices loaded")
        except Exception as e:
            logger.warning(f"DB load skipped: {e}")
        self.stats["start_time"] = datetime.now()

    async def register_device(self, device_id: str, name: str, protocol: str,
                              connection_params: Dict, description: str = "",
                              tags: Dict = None, points: List = None) -> str:
        if device_id not in self.devices:
            adapter_cls = self.protocol_adapters.get(protocol)
            if not adapter_cls:
                raise ValueError(f"Unknown protocol: {protocol}")
            dc = DeviceConnection({
                "device_id": device_id, "name": name, "protocol": protocol,
                "connection_params": connection_params, "points": points or [],
                "tags": tags or {}, "status": "unknown"
            })
            dc.adapter = adapter_cls.create_from_config(connection_params)
            self.devices[device_id] = dc
        await db.insert_device(device_id, name, protocol, connection_params, description, tags or {})
        logger.info(f"Device registered: {device_id}")
        return device_id

    async def unregister_device(self, device_id: str) -> bool:
        if device_id not in self.devices:
            return False
        dc = self.devices[device_id]
        if dc.is_connected and hasattr(dc.adapter, "disconnect"):
            try:
                await dc.adapter.disconnect()
            except: pass
        del self.devices[device_id]
        await db.execute("UPDATE devices SET deleted_at=NOW() WHERE device_id=$1", device_id)
        return True

    async def connect_device(self, device_id: str) -> bool:
        dc = self.devices.get(device_id)
        if not dc or not dc.adapter:
            return False
        if dc.is_connected:
            return True
        try:
            success = await dc.adapter.connect()
            if success:
                dc.is_connected = True
                dc.consecutive_errors = 0
                dc.status = "online"
                dc.last_seen = datetime.now()
                await db.update_device_status(device_id, "online", dc.last_seen)
                return True
        except Exception as e:
            dc.consecutive_errors += 1
            logger.error(f"Connect {device_id}: {e}")
        return False

    async def disconnect_device(self, device_id: str) -> bool:
        dc = self.devices.get(device_id)
        if not dc or not dc.is_connected:
            return True
        try:
            if hasattr(dc.adapter, "disconnect"):
                await dc.adapter.disconnect()
            dc.is_connected = False
            dc.status = "offline"
            await db.update_device_status(device_id, "offline")
            return True
        except Exception as e:
            logger.error(f"Disconnect {device_id}: {e}")
            return False

    async def collect_device_data(self, device_id: str, point_names: List[str] = None):
        dc = self.devices.get(device_id)
        if not dc:
            raise ValueError(f"Device not found: {device_id}")
        if not dc.is_connected:
            ok = await self.connect_device(device_id)
            if not ok:
                raise ConnectionError(f"Failed to connect: {device_id}")
        points_to_read = [p for p in dc.points if not point_names or p.get("name") in point_names]
        if not points_to_read:
            return []
        raw = await dc.adapter.read_points(points_to_read)
        results = []
        for cfg, val in zip(points_to_read, raw):
            quality = "good" if val is not None else "error"
            await db.insert_data_point(device_id, cfg.get("name", ""), val,
                                       cfg.get("unit", ""), quality)
            results.append({"name": cfg.get("name"), "value": val, "quality": quality})
        dc.last_collection = datetime.now()
        dc.last_seen = datetime.now()
        dc.collection_count += len(results)
        self.stats["data_points_collected"] += len(results)
        await db.update_device_status(device_id, "online", dc.last_seen)
        return results

    async def write_to_device(self, device_id: str, point_name: str, value) -> bool:
        dc = self.devices.get(device_id)
        if not dc or not dc.adapter:
            raise ValueError(f"Device not found: {device_id}")
        if not dc.is_connected:
            ok = await self.connect_device(device_id)
            if not ok:
                raise ConnectionError(f"Failed to connect: {device_id}")
        cfg = next((p for p in dc.points if p.get("name") == point_name), None)
        if not cfg:
            raise ValueError(f"Point not found: {point_name}")
        return await dc.adapter.write_point(cfg, value)

    async def start_background_tasks(self):
        interval = self.engine_config.get("health_check_interval", 60)
        auto = self.engine_config.get("auto_collection", {})

        async def health_check():
            while self.running:
                await asyncio.sleep(interval)
                for did, dc in list(self.devices.items()):
                    try:
                        if dc.is_connected and hasattr(dc.adapter, "test_connection"):
                            healthy = await dc.adapter.test_connection()
                            if not healthy:
                                logger.warning(f"Device {did} unhealthy, reconnecting...")
                                await self.disconnect_device(did)
                                await self.connect_device(did)
                    except Exception as e:
                        logger.error(f"Health check {did}: {e}")
                self.stats["uptime"] = int((datetime.now() - self.stats["start_time"]).total_seconds())

        async def auto_collect():
            if not auto.get("enabled", False):
                return
            while self.running:
                await asyncio.sleep(auto.get("interval", 60))
                online = [did for did, dc in self.devices.items() if dc.is_connected]
                for did in online:
                    try:
                        await self.collect_device_data(did)
                    except: pass

        async def stats_report():
            while self.running:
                await asyncio.sleep(self.engine_config.get("stats_report_interval", 300))
                if self.redis:
                    online = sum(1 for dc in self.devices.values() if dc.is_connected)
                    await self.redis.set("engine:stats", {
                        "timestamp": datetime.now().isoformat(),
                        "devices_registered": len(self.devices),
                        "devices_online": online,
                        "data_points_collected": self.stats["data_points_collected"],
                        "uptime_seconds": self.stats.get("uptime", 0),
                    }, expire=3600)

        for coro in [health_check, auto_collect, stats_report]:
            t = asyncio.create_task(coro())
            self.tasks.add(t)
            t.add_done_callback(self.tasks.discard)
        self.running = True
        logger.info(f"Started {len(self.tasks)} background tasks")

    async def stop(self):
        self.running = False
        for t in self.tasks:
            t.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        for dc in self.devices.values():
            if dc.is_connected and hasattr(dc.adapter, "disconnect"):
                try:
                    await dc.adapter.disconnect()
                except: pass
        if self.redis:
            await self.redis.close()
        logger.info("Engine stopped")

    async def get_status(self):
        online = sum(1 for dc in self.devices.values() if dc.is_connected)
        return {
            "status": "running", "devices_registered": len(self.devices),
            "devices_online": online, "devices_offline": len(self.devices) - online,
            "data_points_collected": self.stats["data_points_collected"],
            "uptime_seconds": self.stats.get("uptime", 0),
            "protocols": list(self.protocol_adapters.keys()),
        }

    def list_devices(self, status=None, protocol=None):
        return [
            {"id": dc.device_id, "name": dc.name, "protocol": dc.protocol,
             "status": dc.status, "is_connected": dc.is_connected,
             "collection_count": dc.collection_count}
            for dc in self.devices.values()
            if (status is None or dc.status == status) and (protocol is None or dc.protocol == protocol)
        ]

    def get_device(self, device_id: str):
        dc = self.devices.get(device_id)
        if dc:
            return {"id": dc.device_id, "name": dc.name, "protocol": dc.protocol,
                    "status": dc.status, "is_connected": dc.is_connected,
                    "points": dc.points, "tags": dc.tags}
        return None