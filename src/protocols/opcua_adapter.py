"""
Industrial Data Bridge - OPC-UA Protocol Adapter
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from asyncua import Client, ua

logger = logging.getLogger(__name__)


class OPCUAAdapter:
    """OPC-UA protocol adapter with browse/read/write/subscribe support."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.client: Optional[Client] = None
        self.url = "opc.tcp://localhost:4840"
        self.timeout = self.config.get("timeout", 10)
        self.username = None
        self.password = None
        self.namespace = 0
        self.is_connected = False
        self._node_cache: Dict[str, Any] = {}

    @classmethod
    def create_from_config(cls, params: Dict[str, Any]) -> "OPCUAAdapter":
        a = cls()
        a.url = params.get("url", "opc.tcp://localhost:4840")
        a.username = params.get("username")
        a.password = params.get("password")
        a.namespace = params.get("namespace", 0)
        return a

    async def connect(self) -> bool:
        if self.is_connected:
            return True
        try:
            self.client = Client(url=self.url, timeout=self.timeout)
            await self.client.connect()
            if self.username and self.password:
                self.client.set_user(self.username)
                self.client.set_password(self.password)
            if self.namespace:
                self.namespace = await self.client.get_namespace_index(self.namespace)
            self.is_connected = True
            logger.info(f"OPC-UA connected to {self.url}")
            return True
        except Exception as e:
            logger.error(f"OPC-UA connect error: {e}")
            return False

    async def disconnect(self):
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            self.client = None
            self._node_cache.clear()

    async def test_connection(self) -> bool:
        if not self.is_connected or not self.client:
            return False
        try:
            node = self.client.get_node(ua.ObjectIds.Server_ServerStatus_State)
            state = await node.read_value()
            return state == 0
        except:
            return False

    async def read_points(self, points: List[Dict[str, Any]]) -> List[Any]:
        if not self.is_connected:
            raise ConnectionError("OPC-UA not connected")
        results = []
        for cfg in points:
            try:
                nid = cfg.get("node_id", "")
                if nid not in self._node_cache:
                    self._node_cache[nid] = self.client.get_node(nid)
                node = self._node_cache[nid]
                val = await node.read_value()
                results.append(val)
            except Exception as e:
                logger.error(f"OPC-UA read {cfg.get('name')}: {e}")
                results.append(None)
        return results

    async def write_point(self, cfg: Dict[str, Any], value) -> bool:
        if not self.is_connected:
            raise ConnectionError("OPC-UA not connected")
        try:
            nid = cfg.get("node_id", "")
            node = self.client.get_node(nid)
            dv = ua.DataValue(ua.Variant(value, ua.VariantType.Float))
            await node.write_value(dv)
            return True
        except Exception as e:
            logger.error(f"OPC-UA write error: {e}")
            return False

    async def browse(self, start_node: str = "Objects") -> List[Dict]:
        if not self.is_connected:
            raise ConnectionError("OPC-UA not connected")
        node = self.client.get_node(start_node)
        children = await node.get_children()
        nodes = []
        for c in children:
            dn = await c.read_display_name()
            nc = await c.read_node_class()
            nodes.append({"node_id": c.nodeid.to_string(),
                          "display_name": dn.Text if dn else "",
                          "node_class": nc.name})
        return nodes

    async def close(self):
        await self.disconnect()