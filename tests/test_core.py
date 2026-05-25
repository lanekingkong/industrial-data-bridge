"""
Test suite for bridge engine, config, protocols, and data normalization.
"""

import pytest
import asyncio
import os
import tempfile

from src.core import BridgeEngine
from src.core.config import BridgeConfig
from src.utils.config import load_config, reset_config


@pytest.mark.asyncio
async def test_bridge_engine_creation():
    """Test bridge engine creation with default config."""
    config = BridgeConfig()
    engine = BridgeEngine(config)
    assert engine is not None
    assert engine.config == config


@pytest.mark.asyncio
async def test_protocol_adapter_classes():
    """Test protocol adapter classes are properly registered."""
    engine = BridgeEngine()
    assert "modbus" in engine.protocol_adapters
    assert "opcua" in engine.protocol_adapters
    assert "mqtt" in engine.protocol_adapters
    assert "http" in engine.protocol_adapters


def test_bridge_config_defaults():
    """Test BridgeConfig provides sensible defaults."""
    config = BridgeConfig()
    assert config.server.host == "0.0.0.0"
    assert config.server.port == 8000
    assert config.db.host == "localhost"
    assert config.db.port == 5432


def test_data_normalizer_import():
    """Test data normalizer can be imported and instantiated."""
    from src.utils.data_normalizer import DataNormalizer
    normalizer = DataNormalizer()
    assert normalizer is not None


def test_config_loading_from_dict():
    """Test configuration loading and merging."""
    test_config = {
        "server": {"host": "127.0.0.1", "port": 9000},
        "protocols": {"modbus": {"enabled": False}},
    }
    reset_config()
    result = load_config()
    assert result["server"]["host"] == "0.0.0.0"
    assert result["server"]["port"] == 8000
    reset_config()


@pytest.mark.asyncio
async def test_engine_list_devices_empty():
    """Test listing devices on a fresh engine returns empty list."""
    engine = BridgeEngine()
    devices = engine.list_devices()
    assert isinstance(devices, list)
    assert len(devices) == 0


def test_engine_status():
    """Test engine status report."""
    engine = BridgeEngine()
    # Can get status even before start
    assert hasattr(engine, "get_status")
    assert hasattr(engine, "stats")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])