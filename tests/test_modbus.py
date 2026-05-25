"""
Tests for the Modbus Protocol Adapter.
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

import pytest

from src.protocols.modbus_adapter import ModbusAdapter


class TestModbusAdapter(unittest.TestCase):
    """Test suite for ModbusAdapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.tcp_config = {
            "mode": "tcp",
            "host": "127.0.0.1",
            "port": 5020,
            "unit_id": 1,
        }
        self.rtu_config = {
            "mode": "rtu",
            "port": "COM3",
            "baudrate": 9600,
            "unit_id": 1,
        }

    def test_init_tcp(self):
        """Test TCP adapter initialization."""
        adapter = ModbusAdapter(self.tcp_config)
        assert adapter.mode == "tcp"
        assert adapter.host == "127.0.0.1"
        assert adapter.port == 5020

    def test_init_rtu(self):
        """Test RTU adapter initialization."""
        adapter = ModbusAdapter(self.rtu_config)
        assert adapter.mode == "rtu"
        assert adapter.port == "COM3"
        assert adapter.baudrate == 9600

    def test_init_invalid_mode(self):
        """Test adapter with invalid mode raises error."""
        with pytest.raises(ValueError, match="Invalid Modbus mode"):
            ModbusAdapter({"mode": "invalid"})

    def test_supported_protocols(self):
        """Test supported_protocols returns correct value."""
        assert "modbus" in ModbusAdapter.supported_protocols()

    def test_decode_register_bool(self):
        """Test boolean register decoding."""
        adapter = ModbusAdapter(self.tcp_config)
        val = adapter._decode_register(1, "bool")
        assert val is True
        val = adapter._decode_register(0, "bool")
        assert val is False

    def test_decode_register_int16(self):
        """Test int16 register decoding."""
        adapter = ModbusAdapter(self.tcp_config)
        val = adapter._decode_register(100, "int16")
        assert val == 100
        val = adapter._decode_register(0xFFFF, "int16")
        assert val == -1  # Signed interpretation

    def test_decode_register_float32(self):
        """Test float32 register decoding from two registers."""
        adapter = ModbusAdapter(self.tcp_config)
        # Register values for IEEE 754 float 3.14
        high = 0x4048
        low = 0xF5C3
        val = adapter._decode_registers_pair(high, low, "float32")
        assert abs(val - 3.14) < 0.01

    def test_decode_register_uint16(self):
        """Test uint16 register decoding."""
        adapter = ModbusAdapter(self.tcp_config)
        val = adapter._decode_register(0xFFFF, "uint16")
        assert val == 65535

    def test_decode_register_int32(self):
        """Test int32 register decoding from two registers."""
        adapter = ModbusAdapter(self.tcp_config)
        val = adapter._decode_registers_pair(0x0001, 0x0000, "int32")
        assert val == 65536

    def test_read_point_tcp(self):
        """Test reading a point via TCP (mocked)."""
        adapter = ModbusAdapter(self.tcp_config)
        adapter._client = Mock()
        adapter._client.connected = True
        
        # Mock holding register read
        adapter._client.read_holding_registers = Mock(return_value=Mock(registers=[123]))
        
        point = {
            "name": "temperature",
            "register_type": "holding_register",
            "address": 100,
            "data_type": "int16",
        }
        
        async def run():
            val = await adapter.read_point(point)
            assert val == 123
        
        asyncio.run(run())

    def test_write_point_tcp(self):
        """Test writing a point via TCP (mocked)."""
        adapter = ModbusAdapter(self.tcp_config)
        adapter._client = Mock()
        adapter._client.connected = True
        adapter._client.write_register = Mock()
        
        point = {
            "name": "setpoint",
            "register_type": "holding_register",
            "address": 200,
            "data_type": "int16",
        }
        
        async def run():
            result = await adapter.write_point(point, 50)
            assert result is True
        
        asyncio.run(run())

    def test_connect_simulation_mode(self):
        """Test simulated connection."""
        adapter = ModbusAdapter(self.tcp_config)
        
        async def run():
            await adapter.connect()
            assert adapter._simulated is True
            await adapter.disconnect()
        
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()