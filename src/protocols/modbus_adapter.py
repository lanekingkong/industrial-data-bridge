"""
Industrial Data Bridge - Modbus Protocol Adapter
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from pymodbus.client import AsyncModbusTcpClient, AsyncModbusSerialClient
from pymodbus.exceptions import ConnectionException, ModbusIOException
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

logger = logging.getLogger(__name__)


class ModbusAdapter:
    """Modbus TCP/RTU adapter with auto-reconnection and retry."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.client = None
        self.timeout = self.config.get("timeout", 5)
        self.retries = self.config.get("retries", 3)
        self.is_connected = False
        self.mode = "tcp"
        self.host = "localhost"
        self.port = 502
        self.unit_id = 1
        self._error_count = 0

    @classmethod
    def create_from_config(cls, params: Dict[str, Any]) -> "ModbusAdapter":
        a = cls()
        a.mode = params.get("mode", "tcp")
        a.host = params.get("host", "localhost")
        a.port = params.get("port", 502)
        a.unit_id = params.get("unit_id", 1)
        if a.mode == "rtu":
            a.port_name = params.get("port", "/dev/ttyUSB0")
            a.baudrate = params.get("baudrate", 19200)
            a.parity = params.get("parity", "N")
            a.stopbits = params.get("stopbits", 1)
            a.bytesize = params.get("bytesize", 8)
        return a

    async def connect(self) -> bool:
        if self.is_connected:
            return True
        try:
            if self.mode == "tcp":
                self.client = AsyncModbusTcpClient(self.host, self.port, timeout=self.timeout, retries=self.retries, retry_on_empty=True)
            else:
                self.client = AsyncModbusSerialClient(port=self.port_name, baudrate=self.baudrate, parity=self.parity, stopbits=self.stopbits, bytesize=self.bytesize, timeout=self.timeout, retries=self.retries)
            self.is_connected = await self.client.connect()
            if self.is_connected:
                logger.info(f"Modbus {self.mode} connected {self.host}:{self.port}")
            return self.is_connected
        except Exception as e:
            logger.error(f"Modbus connect error: {e}")
            return False

    async def disconnect(self):
        if self.client and self.is_connected:
            self.client.close()
            self.is_connected = False
            self.client = None

    async def test_connection(self) -> bool:
        if not self.is_connected or not self.client:
            return False
        try:
            r = await self.client.read_coils(0, 1, slave=self.unit_id)
            return not r.isError()
        except:
            return False

    async def read_points(self, points: List[Dict[str, Any]]) -> List[Any]:
        if not self.is_connected:
            raise ConnectionError("Modbus not connected")
        results = []
        for cfg in points:
            try:
                results.append(await self._read_point(cfg))
            except Exception as e:
                logger.error(f"Read {cfg.get('name')}: {e}")
                results.append(None)
        return results

    async def _read_point(self, cfg: Dict[str, Any]):
        addr = cfg.get("address", 0)
        count = cfg.get("count", 1)
        dtype = cfg.get("data_type", "uint16")
        ptype = cfg.get("type", "holding_register")
        slave = self.unit_id

        if ptype == "coil":
            r = await self.client.read_coils(addr, count, slave=slave)
        elif ptype == "discrete_input":
            r = await self.client.read_discrete_inputs(addr, count, slave=slave)
        elif ptype == "holding_register":
            r = await self.client.read_holding_registers(addr, count, slave=slave)
        elif ptype == "input_register":
            r = await self.client.read_input_registers(addr, count, slave=slave)
        else:
            raise ValueError(f"Unknown type: {ptype}")

        if r.isError():
            raise ModbusIOException(str(r))

        if dtype == "uint16":
            return r.registers[0]
        elif dtype == "int16":
            v = r.registers[0]
            return v - 65536 if v > 32767 else v
        elif dtype in ("float32", "uint32", "int32"):
            d = BinaryPayloadDecoder.fromRegisters(r.registers[:2], byteorder=Endian.BIG, wordorder=Endian.BIG)
            if dtype == "float32":
                return round(d.decode_32bit_float(), 6)
            elif dtype == "int32":
                return d.decode_32bit_int()
            return d.decode_32bit_uint()
        elif dtype == "coil":
            return bool(r.bits[0])
        return r.registers[0]

    async def write_point(self, cfg: Dict[str, Any], value) -> bool:
        if not self.is_connected:
            raise ConnectionError("Modbus not connected")
        try:
            addr = cfg.get("address", 0)
            if cfg.get("type") == "coil":
                r = await self.client.write_coil(addr, bool(value), slave=self.unit_id)
            else:
                r = await self.client.write_register(addr, int(value), slave=self.unit_id)
            return not r.isError()
        except Exception as e:
            logger.error(f"Write error: {e}")
            return False

    async def close(self):
        await self.disconnect()