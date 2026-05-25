"""
Message Serializer - Serializes data points for transport/storage.

Supports: JSON, MessagePack, Protobuf, and Arrow columnar formats.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union


class MessageSerializer:
    """
    Serializes industrial data points for transport and storage.

    Supports multiple formats optimized for different use cases:
    - JSON: Human-readable, universal, good for debugging and APIs
    - MessagePack: Compact binary, good for MQTT and low-bandwidth
    - Protobuf: Schema-based, strongly typed, good for gRPC
    - Arrow: Columnar, zero-copy, good for batch analytics
    """

    def __init__(self) -> None:
        self._msgpack_available = False
        self._protobuf_available = False
        self._arrow_available = False

        try:
            import msgpack
            self._msgpack_available = True
        except ImportError:
            pass

        try:
            from google.protobuf import __version__ as protobuf_version
            self._protobuf_available = True
        except ImportError:
            pass

        try:
            import pyarrow
            self._arrow_available = True
        except ImportError:
            pass

    # ── JSON ──────────────────────────────────

    def to_json(
        self,
        data: Union[Dict, List, Any],
        indent: Optional[int] = None,
    ) -> str:
        """
        Serialize to JSON string.

        Args:
            data: Data point(s) to serialize.
            indent: Indentation for pretty-printing.

        Returns:
            JSON string.
        """
        return json.dumps(
            data,
            default=self._json_default,
            indent=indent,
            ensure_ascii=False,
        )

    def from_json(self, json_str: str) -> Any:
        """Deserialize from JSON string."""
        return json.loads(json_str)

    def to_json_bytes(self, data: Any) -> bytes:
        """Serialize to JSON bytes."""
        return self.to_json(data).encode("utf-8")

    def from_json_bytes(self, data_bytes: bytes) -> Any:
        """Deserialize from JSON bytes."""
        return self.from_json(data_bytes.decode("utf-8"))

    # ── MessagePack ───────────────────────────

    def to_msgpack(self, data: Any) -> bytes:
        """Serialize to MessagePack binary."""
        if not self._msgpack_available:
            return self.to_json_bytes(data)  # Fallback
        import msgpack
        return msgpack.packb(data, default=self._msgpack_default)

    def from_msgpack(self, data_bytes: bytes) -> Any:
        """Deserialize from MessagePack binary."""
        if not self._msgpack_available:
            return self.from_json_bytes(data_bytes)
        import msgpack
        return msgpack.unpackb(data_bytes, raw=False)

    # ── Protobuf ──────────────────────────────

    def to_protobuf(self, data: List[Dict]) -> bytes:
        """
        Serialize to Protobuf binary.

        Uses a generic key-value approach if no specific
        .proto schema is loaded.
        """
        if not self._protobuf_available:
            return self.to_json_bytes({"entries": data})

        try:
            from google.protobuf import struct_pb2, timestamp_pb2, any_pb2

            data_struct = struct_pb2.Struct()
            for i, entry in enumerate(data):
                entry_struct = struct_pb2.Struct()
                for key, value in entry.items():
                    entry_struct[key] = value
                data_struct[f"entry_{i}"] = entry_struct

            return data_struct.SerializeToString()
        except Exception:
            return self.to_json_bytes({"entries": data})

    def from_protobuf(self, data_bytes: bytes) -> Any:
        """Deserialize from Protobuf binary."""
        if not self._protobuf_available:
            return self.from_json_bytes(data_bytes)

        try:
            from google.protobuf import struct_pb2

            data_struct = struct_pb2.Struct()
            data_struct.ParseFromString(data_bytes)
            result = []
            for key in sorted(data_struct.keys()):
                result.append(dict(data_struct[key]))
            return result
        except Exception:
            return self.from_json_bytes(data_bytes)

    # ── Arrow ─────────────────────────────────

    def to_arrow(
        self,
        data: List[Dict[str, Any]],
        schema: Optional[Any] = None,
    ) -> bytes:
        """
        Serialize to Apache Arrow RecordBatch.

        Args:
            data: List of data point dicts.
            schema: Optional PyArrow schema.

        Returns:
            Arrow IPC bytes.
        """
        if not self._arrow_available:
            return self.to_json_bytes(data)

        import pyarrow as pa

        # Convert list of dicts to dict of lists
        if not data:
            empty_schema = pa.schema([("device_id", pa.string())])
            batch = pa.RecordBatch.from_pylist([], schema=schema or empty_schema)
            return batch.serialize().to_pybytes()

        columns = {}
        for row in data:
            for key, value in row.items():
                if key not in columns:
                    columns[key] = []
                columns[key].append(value)

        # Infer types or use schema
        if schema:
            table = pa.table(columns, schema=schema)
        else:
            table = pa.table(columns)

        # Serialize to IPC format
        sink = pa.BufferOutputStream()
        with pa.ipc.new_stream(sink, table.schema) as writer:
            writer.write_table(table)
        return sink.getvalue().to_pybytes()

    def from_arrow(self, data_bytes: bytes) -> List[Dict[str, Any]]:
        """Deserialize from Apache Arrow IPC bytes."""
        if not self._arrow_available:
            return self.from_json_bytes(data_bytes)

        import pyarrow as pa

        with pa.ipc.open_stream(pa.py_buffer(data_bytes)) as reader:
            table = reader.read_all()
            return table.to_pylist()

    # ── Utility ────────────────────────────────

    def serialize(
        self,
        data: Any,
        fmt: str = "json",
        **kwargs,
    ) -> Union[str, bytes]:
        """
        Serialize data to specified format.

        Args:
            data: Data to serialize.
            fmt: "json", "msgpack", "protobuf", or "arrow".
            **kwargs: Additional serializer-specific arguments.

        Returns:
            Serialized data as string or bytes.
        """
        serializers = {
            "json": self.to_json,
            "msgpack": self.to_msgpack,
            "protobuf": self.to_protobuf,
            "arrow": self.to_arrow,
        }
        if fmt not in serializers:
            raise ValueError(f"Unknown format: {fmt}. Supported: {list(serializers.keys())}")
        return serializers[fmt](data, **kwargs)

    def deserialize(
        self,
        data: Union[str, bytes],
        fmt: str = "json",
    ) -> Any:
        """
        Deserialize data from specified format.

        Args:
            data: Serialized data.
            fmt: "json", "msgpack", "protobuf", or "arrow".

        Returns:
            Deserialized data structure.
        """
        deserializers = {
            "json": self.from_json if isinstance(data, str) else self.from_json_bytes,
            "msgpack": self.from_msgpack,
            "protobuf": self.from_protobuf,
            "arrow": self.from_arrow,
        }
        if fmt not in deserializers:
            raise ValueError(f"Unknown format: {fmt}")
        return deserializers[fmt](data)

    def _json_default(self, obj: Any) -> Any:
        """JSON serialization helper for custom types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if isinstance(obj, bytes):
            return obj.hex()
        raise TypeError(f"Type not serializable: {type(obj)}")

    def _msgpack_default(self, obj: Any) -> Any:
        """MessagePack serialization helper."""
        if isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}
        if isinstance(obj, bytes):
            return obj  # MessagePack supports bytes natively
        return str(obj)