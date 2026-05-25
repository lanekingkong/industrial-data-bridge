"""
MQTT IoT Gateway Example
Bridges MQTT-enabled IoT devices (sensors, actuators) into the Industrial
Data Bridge platform. Supports bidirectional communication: subscribe to
device telemetry and publish control commands.
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core import BridgeEngine, BridgeConfig
from src.protocols import MQTTAdapter


async def main():
    """Run MQTT IoT Gateway example."""
    print("=" * 60)
    print("Industrial Data Bridge - MQTT IoT Gateway Example")
    print("=" * 60)

    # Initialize bridge engine
    config = BridgeConfig()
    engine = BridgeEngine(config)

    # Configure MQTT broker connection
    mqtt_config = {
        "broker": "mqtt://localhost:1883",
        "client_id": "industrial-bridge-gateway",
        "keepalive": 60,
        "qos": 1,
        "username": "bridge_user",
        "password": "changeme",
    }

    print(f"\n[1] Connecting to MQTT broker at {mqtt_config['broker']}...")
    adapter = MQTTAdapter(mqtt_config)

    # Define IoT device topics to subscribe to
    topics = [
        {
            "topic": "plant1/+/temperature",
            "qos": 1,
            "name": "temperature_sensors",
        },
        {
            "topic": "plant1/+/humidity",
            "qos": 1,
            "name": "humidity_sensors",
        },
        {
            "topic": "plant1/+/vibration",
            "qos": 1,
            "name": "vibration_sensors",
        },
        {
            "topic": "plant1/+/status",
            "qos": 0,
            "name": "device_status",
        },
    ]

    # Control topics for sending commands to devices
    control_topics = {
        "pump": "plant1/pump/control",
        "valve": "plant1/valve/control",
        "conveyor": "plant1/conveyor/control",
    }

    print("\n[2] Subscribing to device topics...")
    for topic in topics:
        await adapter.subscribe(topic["topic"], topic["qos"])
        print(f"  Subscribed: {topic['topic']} (QoS: {topic['qos']})")

    # Register IoT devices in the bridge
    print("\n[3] Registering IoT devices...")
    iot_devices = [
        {
            "device_id": "iot_pump_001",
            "name": "IoT Smart Pump",
            "protocol": "mqtt",
            "topics": [
                {"topic": "plant1/pump/temperature", "metric": "temperature"},
                {"topic": "plant1/pump/vibration", "metric": "vibration"},
                {"topic": "plant1/pump/status", "metric": "status"},
            ],
        },
        {
            "device_id": "iot_valve_001",
            "name": "IoT Control Valve",
            "protocol": "mqtt",
            "topics": [
                {"topic": "plant1/valve/position", "metric": "position"},
                {"topic": "plant1/valve/status", "metric": "status"},
            ],
        },
    ]

    for device in iot_devices:
        engine.register_device(
            device_id=device["device_id"],
            name=device["name"],
            protocol=device["protocol"],
            connection_params=mqtt_config,
            points=[{"name": t["metric"], "topic": t["topic"]} for t in device["topics"]],
        )
        print(f"  Registered: {device['name']}")

    # Define message handler for incoming telemetry
    async def on_telemetry(topic: str, payload: bytes):
        """Process incoming device telemetry."""
        try:
            data = json.loads(payload.decode("utf-8"))
            device_id = topic.split("/")[1]  # Extract device from topic
            
            print(f"  [Telemetry] {topic} → {json.dumps(data)}")
            
            # Forward to AI anomaly detection
            if engine.is_device_registered(device_id):
                await engine.process_data(device_id, data)
                
                # Check for anomalies
                result = await engine.anomaly_detector.detect(device_id, data)
                if result["is_anomaly"]:
                    print(f"  ⚠ Anomaly detected on {device_id}: score={result['score']:.3f}")
                    
                    # Send alert via MQTT
                    alert_payload = json.dumps({
                        "type": "anomaly_alert",
                        "device_id": device_id,
                        "metric": topic.split("/")[-1],
                        "score": result["score"],
                        "timestamp": data.get("timestamp", ""),
                    })
                    await adapter.publish("plant1/alerts/anomaly", alert_payload, qos=1)
                    
        except json.JSONDecodeError:
            print(f"  Warning: Invalid JSON from {topic}")
        except Exception as e:
            print(f"  Error processing {topic}: {e}")

    # Register the telemetry handler
    adapter.on_message = on_telemetry

    # Start the gateway
    print(f"\n[4] Starting MQTT gateway...")
    print("    Listening for device telemetry...")
    print("    (Press Ctrl+C to stop)")
    print("\n" + "-" * 60)

    try:
        await adapter.connect()
        await engine.start()

        # Example: Send a control command every 30 seconds
        counter = 0
        while True:
            try:
                # Simulate periodic pump speed adjustment
                if counter % 6 == 0:  # Every 30 seconds
                    speed = 50 + (counter % 5) * 10  # Vary speed 50-90%
                    control_cmd = json.dumps({
                        "command": "set_speed",
                        "value": speed,
                        "unit": "%",
                        "timestamp": asyncio.get_event_loop().time(),
                    })
                    await adapter.publish(control_topics["pump"], control_cmd, qos=1)
                    print(f"  [Control] Pump speed set to {speed}%")

                counter += 1
                await asyncio.sleep(5)

            except Exception as e:
                print(f"  Warning: {e}")
                await asyncio.sleep(10)

    except KeyboardInterrupt:
        print("\n[5] Shutting down gateway...")
    finally:
        await engine.stop()
        await adapter.disconnect()
        print("  MQTT gateway stopped. Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())