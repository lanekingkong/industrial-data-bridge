"""
Base Protocol Adapter - Abstract interface for all protocol adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ProtocolAdapter(ABC):
    """
    Abstract base class for industrial protocol adapters.

    Each concrete adapter implements the specifics of a protocol
    (Modbus, OPC-UA, MQTT, HTTP, etc.) while exposing a uniform
    interface to the BridgeEngine.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the device/gateway."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection and clean up resources."""
        ...

    @abstractmethod
    async def read_point(self, point: Dict[str, Any]) -> Any:
        """
        Read a single data point.

        Args:
            point: Dict with keys like 'address', 'type', 'name'.

        Returns:
            Raw value from the device.
        """
        ...

    @abstractmethod
    async def write_point(self, point: Dict[str, Any], value: Any) -> bool:
        """
        Write a value to a data point.

        Args:
            point: Dict specifying the target point.
            value: The value to write.

        Returns:
            True if the write was successful.
        """
        ...

    async def read_all_points(self, points: List[Dict[str, Any]]) -> List[Any]:
        """
        Read multiple data points. Default implementation reads
        sequentially; subclasses may optimize for batch reads.

        Args:
            points: List of point descriptors.

        Returns:
            List of raw values, corresponding to points order.
        """
        results = []
        for point in points:
            try:
                val = await self.read_point(point)
                results.append(val)
            except Exception:
                results.append(None)
        return results

    async def write_points(
        self, writes: List[Dict[str, Any]]
    ) -> List[bool]:
        """
        Write multiple values. Default sequential implementation.

        Args:
            writes: List of dicts with 'point' and 'value' keys.

        Returns:
            List of bool results.
        """
        results = []
        for w in writes:
            try:
                ok = await self.write_point(w["point"], w["value"])
                results.append(ok)
            except Exception:
                results.append(False)
        return results

    @property
    def is_connected(self) -> bool:
        return self._connected

    @staticmethod
    def supported_protocols() -> List[str]:
        """Return list of protocol names this adapter supports."""
        return []