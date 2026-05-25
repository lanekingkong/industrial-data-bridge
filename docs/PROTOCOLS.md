# Protocol Adapters

Industrial Data Bridge supports multiple industrial communication protocols through its extensible adapter framework.

## Supported Protocols

| Protocol | Adapter Class | Status | Use Case |
|----------|--------------|--------|----------|
| Modbus TCP/RTU | `ModbusAdapter` | Stable | PLCs, sensors, meters |
| OPC-UA | `OPCUAAdapter` | Stable | Industrial automation |
| MQTT | `MQTTAdapter` | Stable | IoT messaging, cloud pub/sub |
| HTTP/REST | `HTTPAdapter` | Stable | Web services, custom APIs |

## Modbus Configuration

```yaml
device:
  protocol: modbus
  connection:
    mode: tcp
    host: 192.168.1.100
    port: 502
    unit_id: 1
    timeout: 5
  points:
    - name: "temperature"
      register_type: holding_register
      address: 100
      data_type: float32
      byte_order: big
      unit: "celsius"
```

### Register Types
- `coil` - Digital output (read/write)
- `discrete_input` - Digital input (read-only)
- `holding_register` - Analog output (read/write)
- `input_register` - Analog input (read-only)

### Data Types
- `int16`, `uint16` - 16-bit integers
- `int32`, `uint32` - 32-bit integers
- `float32`, `float64` - IEEE 754 floating point
- `string` - ASCII string (multiple registers)

## OPC-UA Configuration

```yaml
device:
  protocol: opcua
  connection:
    endpoint: "opc.tcp://192.168.1.200:4840"
    security_policy: None
    username: ""
    password: ""
  points:
    - name: "pressure"
      node_id: "ns=2;s=Pressure"
      sampling_interval: 1000
      unit: "bar"
```

## MQTT Configuration

```yaml
device:
  protocol: mqtt
  connection:
    broker: "mqtt://localhost:1883"
    client_id: "bridge-gateway"
    username: ""
    password: ""
    qos: 1
    keepalive: 60
  topics:
    - topic: "plant1/sensor/temperature"
      qos: 1
      name: "temperature_sensor_1"
```

## HTTP Adapter Configuration

```yaml
device:
  protocol: http
  connection:
    base_url: "http://192.168.1.50/api"
    method: GET
    headers:
      Authorization: "Bearer token"
    interval: 5
  points:
    - name: "humidity"
      endpoint: "/sensors/humidity"
      json_path: "$.value"
      unit: "%"
```

## Creating Custom Adapters

Extend `BaseProtocolAdapter` to add support for new protocols:

```python
from src.protocols.base import BaseProtocolAdapter

class MyCustomAdapter(BaseProtocolAdapter):
    protocol_name = "my_protocol"

    async def connect(self) -> bool:
        # Establish connection
        pass

    async def disconnect(self) -> None:
        # Clean up connection
        pass

    async def read_point(self, point: dict) -> dict:
        # Read a single data point
        pass

    async def read_all(self) -> list[dict]:
        # Read all configured points
        pass
```

## Error Handling

All adapters implement automatic reconnection with exponential backoff. Configure via:

```yaml
connection:
  retry_max: 5
  retry_delay: 2
  retry_backoff: 2.0
  timeout: 10
```

## Performance Tuning

- **Batch reading**: Modbus supports reading contiguous registers in a single request, set `batch_size` for automatic optimization
- **Sampling intervals**: Adjust per-device to balance data freshness with network load
- **Connection pooling**: HTTP adapter reuses connections, OPC-UA maintains persistent sessions