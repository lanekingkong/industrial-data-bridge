"""
OPC-UA Server Example
Creates an OPC-UA server to expose data from legacy equipment that lacks
native OPC-UA support. This bridges non-OPCUA devices into the Industrial
Data Bridge ecosystem.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core import BridgeEngine, BridgeConfig
from src.protocols import OPCUAAdapter


async def main():
    """Run OPC-UA server example."""
    print("=" * 60)
    print("Industrial Data Bridge - OPC-UA Server Example")
    print("=" * 60)

    # Initialize bridge engine
    config = BridgeConfig()
    config.load_yaml(os.path.join(os.path.dirname(__file__), 'config.yaml'))
    engine = BridgeEngine(config)

    # Configure OPC-UA server endpoint
    opcua_config = {
        "endpoint": "opc.tcp://0.0.0.0:4840",
        "security_policy": "None",
        "server_name": "Industrial Data Bridge OPC-UA",
        "allow_anonymous": True,
    }

    print(f"\n[1] Starting OPC-UA server at {opcua_config['endpoint']}...")
    adapter = OPCUAAdapter(opcua_config)

    # Create address space nodes
    print("\n[2] Creating address space...")
    nodes = {
        "temperature": {"ns": 2, "id": "TemperatureSensor", "value": 0, "unit": "°C"},
        "pressure": {"ns": 2, "id": "PressureSensor", "value": 0, "unit": "kPa"},
        "humidity": {"ns": 2, "id": "HumiditySensor", "value": 0, "unit": "%"},
        "flow_rate": {"ns": 2, "id": "FlowRateSensor", "value": 0, "unit": "L/min"},
    }

    for name, node_config in nodes.items():
        adapter.add_variable(
            node_id=f"ns={node_config['ns']};s={node_config['id']}",
            name=name,
            value=node_config["value"],
            unit=node_config["unit"],
        )
        print(f"  Registered: {name} ({node_config['unit']})")

    # Register legacy device data sources
    print("\n[3] Configuring data sources for legacy devices...")
    
    # Example: map Modbus RTU sensor readings to OPC-UA nodes
    engine.register_device(
        device_id="legacy_pump_001",
        name="Legacy Water Pump",
        protocol="modbus",
        connection_params={
            "mode": "rtu",
            "port": "/dev/ttyUSB0",
            "baudrate": 9600,
            "unit_id": 1,
            "timeout": 2,
        },
        points=[
            {"name": "temperature", "register_type": "input_register", "address": 100, "data_type": "float32"},
            {"name": "pressure", "register_type": "input_register", "address": 102, "data_type": "float32"},
            {"name": "flow_rate", "register_type": "input_register", "address": 104, "data_type": "float32"},
        ],
    )

    print("  Legacy pump registered with Modbus RTU interface")

    # Start data collection and OPC-UA exposure
    print("\n[4] Starting data collection and OPC-UA exposure...")
    print("    (Press Ctrl+C to stop)")
    print("\n" + "-" * 60)

    try:
        await adapter.start()
        await engine.start()

        while True:
            try:
                # Collect data from legacy device
                if engine.is_device_registered("legacy_pump_001"):
                    data = await engine.collect_device("legacy_pump_001")
                    
                    # Update OPC-UA nodes with collected data
                    for point_name, point_data in data.items():
                        if point_name in nodes:
                            node_id = f"ns={nodes[point_name]['ns']};s={nodes[point_name]['id']}"
                            await adapter.write_value(node_id, point_data["value"])
                    
                    print(f"  Updated {len(data)} OPC-UA nodes with live data")

                await asyncio.sleep(5)  # 5-second polling interval

            except Exception as e:
                print(f"  Warning: Data collection error - {e}")
                await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("\n[5] Shutting down...")
    finally:
        await engine.stop()
        await adapter.stop()
        print("  OPC-UA server stopped. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())