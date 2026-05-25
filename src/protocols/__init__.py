"""
Industrial Data Bridge - Protocol Adapters Package
"""

from src.protocols.modbus_adapter import ModbusAdapter
from src.protocols.opcua_adapter import OPCUAAdapter
from src.protocols.mqtt_adapter import MQTTAdapter
from src.protocols.http_adapter import HTTPAdapter

__all__ = ["ModbusAdapter", "OPCUAAdapter", "MQTTAdapter", "HTTPAdapter"]

PROTOCOL_MAP = {
    "modbus": ModbusAdapter,
    "opcua": OPCUAAdapter,
    "mqtt": MQTTAdapter,
    "http": HTTPAdapter,
}


def get_adapter(protocol: str):
    """Get adapter class by protocol name."""
    adapter = PROTOCOL_MAP.get(protocol.lower())
    if not adapter:
        raise ValueError(f"Unknown protocol: {protocol}")
    return adapter