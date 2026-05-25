"""
Industrial Data Bridge - MQTT Protocol Adapter
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

import aiomqtt
from aiomqtt import Client, Message

logger = logging.getLogger(__name__)


class MQTTAdapter:
    """MQTT adapter with QoS, TLS, LWT, and auto-subscription."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.client: Optional[Client] = None
        self.host = "localhost"
        self.port = 1883
        self.client_id = f"idb-mqtt-{id(self)}"
        self.username = None
        self.password = None
        self.topics = []
        self.qos = 1
        self.keepalive = 60
        self.use_tls = False
        self.ca_cert = None
        self.client_cert = None
        self.client_key = None
        self.is_connected = False
        self._callbacks: Dict[str, List[Callable]] = {}
        self._cache: Dict[str, bytes] = {}
        self._stats = {"sent": 0, "received": 0}

    @classmethod
    def create_from_config(cls, params: Dict[str, Any]) -> "MQTTAdapter":
        a = cls()
        a.host = params.get("host", "localhost")
        a.port = params.get("port", 1883)
        a.client_id = params.get("client_id", f"idb-mqtt-{id(a)}")
        a.username = params.get("username")
        a.password = params.get("password")
        a.topics = params.get("topics", [])
        a.qos = params.get("qos", 1)
        a.use_tls = params.get("use_tls", False)
        a.ca_cert = params.get("ca_cert")
        a.client_cert = params.get("client_cert")
        a.client_key = params.get("client_key")
        return a

    async def connect(self) -> bool:
        if self.is_connected:
            return True
        try:
            conn = {"hostname": self.host, "port": self.port,
                    "keepalive": self.keepalive, "identifier": self.client_id}
            if self.username:
                conn["username"] = self.username
            if self.password:
                conn["password"] = self.password
            if self.use_tls:
                import ssl
                ctx = ssl.create_default_context()
                if self.ca_cert:
                    ctx.load_verify_locations(self.ca_cert)
                if self.client_cert and self.client_key:
                    ctx.load_cert_chain(self.client_cert, self.client_key)
                conn["tls_context"] = ctx
            self.client = Client(**conn)
            await self.client.__aenter__()
            self.is_connected = True
            for t in self.topics:
                if isinstance(t, dict):
                    topic, qos = t.get("topic", ""), t.get("qos", self.qos)
                else:
                    topic, qos = t, self.qos
                if topic:
                    await self.client.subscribe(topic, qos=qos)
            logger.info(f"MQTT connected {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"MQTT connect error: {e}")
            return False

    async def disconnect(self):
        if self.client and self.is_connected:
            await self.client.__aexit__(None, None, None)
            self.is_connected = False
            self.client = None

    async def test_connection(self) -> bool:
        if not self.is_connected or not self.client:
            return False
        try:
            await self.client.ping()
            return True
        except:
            return False

    async def read_points(self, points: List[Dict[str, Any]]) -> List[Any]:
        results = []
        for cfg in points:
            topic = cfg.get("topic", "")
            default = cfg.get("default_value", None)
            val = self._cache.get(topic, default)
            if isinstance(val, bytes):
                try:
                    val = json.loads(val.decode("utf-8"))
                except:
                    val = val.decode("utf-8", errors="ignore")
            results.append(val)
        return results

    async def write_point(self, cfg: Dict[str, Any], value) -> bool:
        if not self.is_connected:
            raise ConnectionError("MQTT not connected")
        try:
            topic = cfg.get("topic", "")
            qos = cfg.get("qos", self.qos)
            retain = cfg.get("retain", False)
            if isinstance(value, (dict, list)):
                payload = json.dumps(value).encode("utf-8")
            elif isinstance(value, str):
                payload = value.encode("utf-8")
            else:
                payload = str(value).encode("utf-8")
            await self.client.publish(topic=topic, payload=payload, qos=qos, retain=retain)
            self._stats["sent"] += 1
            return True
        except Exception as e:
            logger.error(f"MQTT publish error: {e}")
            return False

    async def subscribe(self, topic: str, qos: int = 1, cb: Optional[Callable] = None) -> bool:
        if not self.is_connected:
            return False
        try:
            await self.client.subscribe(topic, qos=qos)
            if cb:
                if topic not in self._callbacks:
                    self._callbacks[topic] = []
                self._callbacks[topic].append(cb)
            return True
        except Exception as e:
            logger.error(f"Subscribe error: {e}")
            return False

    async def get_message(self, timeout: float = 10.0) -> Optional[Message]:
        if not self.is_connected:
            return None
        try:
            async with asyncio.timeout(timeout):
                async for msg in self.client.messages:
                    self._cache[msg.topic.value] = msg.payload
                    self._stats["received"] += 1
                    for cb in self._callbacks.get(msg.topic.value, []):
                        try:
                            await cb(msg)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                    return msg
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Get message error: {e}")
            return None

    async def close(self):
        await self.disconnect()
        self._callbacks.clear()
        self._cache.clear()