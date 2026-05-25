"""
Example: Modbus PLC Integration

Demonstrates connecting to a Siemens S7-1200 PLC via Modbus TCP
and collecting temperature, pressure, and flow data.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import BridgeEngine, BridgeConfig
from src.protocols.modbus_adapter import ModbusAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Main example function."""
    logger.info("Starting Modbus PLC integration example...")
    
    # Configuration for Siemens S7-1200 PLC
    plc_config = {
        "device_id": "s7_1200_plc_001",
        "name": "Siemens S7-1200 PLC",
        "protocol": "modbus",
        "connection_params": {
            "mode": "tcp",
            "host": "192.168.1.100",  # PLC IP address
            "port": 502,              # Standard Modbus TCP port
            "unit_id": 1,             # PLC unit ID
            "timeout": 5.0,           # Connection timeout
            "retries": 3,             # Retry attempts
        },
        "points": [
            {
                "name": "temperature",
                "description": "Process temperature",
                "register_type": "holding_register",
                "address": 40001,     # Modbus address 40001
                "data_type": "float32",
                "unit": "celsius",
                "min": 0,
                "max": 100,
                "scale_factor": 0.1,  # Raw value * 0.1 = actual value
            },
            {
                "name": "pressure",
                "description": "Line pressure",
                "register_type": "holding_register",
                "address": 40003,     # Modbus address 40003
                "data_type": "float32",
                "unit": "bar",
                "min": 0,
                "max": 10,
            },
            {
                "name": "flow_rate",
                "description": "Flow rate",
                "register_type": "holding_register",
                "address": 40005,     # Modbus address 40005
                "data_type": "float32",
                "unit": "l/min",
                "min": 0,
                "max": 1000,
            },
            {
                "name": "pump_status",
                "description": "Pump running status",
                "register_type": "coil",
                "address": 1,         # Modbus coil address 1
                "data_type": "bool",
            },
            {
                "name": "alarm_status",
                "description": "Alarm active",
                "register_type": "discrete_input",
                "address": 1,         # Modbus discrete input address 1
                "data_type": "bool",
            },
        ],
    }
    
    # Create bridge engine
    config = BridgeConfig()
    engine = BridgeEngine(config)
    
    try:
        # Start the engine
        await engine.start()
        
        # Register the PLC
        await engine.register_device(**plc_config)
        logger.info(f"Registered PLC: {plc_config['name']}")
        
        # Collect data for 5 cycles
        for cycle in range(5):
            logger.info(f"Collection cycle {cycle + 1}")
            
            # Collect data from PLC
            start_time = datetime.now()
            data = await engine.collect_device(plc_config["device_id"])
            end_time = datetime.now()
            
            # Display collected data
            logger.info(f"Collection time: {(end_time - start_time).total_seconds():.3f}s")
            for point_name, point_data in data.items():
                value = point_data.get("value", "N/A")
                quality = point_data.get("quality", "unknown")
                unit = point_data.get("unit", "")
                logger.info(f"  {point_name}: {value} {unit} ({quality})")
            
            # Wait before next collection
            await asyncio.sleep(2)
        
        # Example: Write to a holding register
        logger.info("Writing to PLC...")
        write_point = {
            "name": "setpoint",
            "register_type": "holding_register",
            "address": 40010,
            "data_type": "int16",
        }
        
        success = await engine.write_point(
            device_id=plc_config["device_id"],
            point=write_point,
            value=75,  # Setpoint value
        )
        
        if success:
            logger.info("Write successful")
        else:
            logger.warning("Write failed")
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
    finally:
        # Clean up
        await engine.stop()
        logger.info("Example completed")


async def direct_modbus_example():
    """Example using ModbusAdapter directly."""
    logger.info("Direct Modbus adapter example...")
    
    # Create adapter
    adapter = ModbusAdapter({
        "mode": "tcp",
        "host": "192.168.1.100",
        "port": 502,
        "unit_id": 1,
    })
    
    try:
        # Connect
        await adapter.connect()
        
        # Read holding registers
        point = {
            "name": "temperature",
            "register_type": "holding_register",
            "address": 40001,
            "data_type": "float32",
        }
        
        value = await adapter.read_point(point)
        logger.info(f"Temperature: {value}°C")
        
        # Read multiple points
        points = [
            {"name": "temp", "register_type": "holding_register", "address": 40001, "data_type": "float32"},
            {"name": "pressure", "register_type": "holding_register", "address": 40003, "data_type": "float32"},
        ]
        
        values = await adapter.read_all_points(points)
        logger.info(f"Multiple values: {values}")
        
    except Exception as e:
        logger.error(f"Direct example failed: {e}")
    finally:
        await adapter.disconnect()


if __name__ == "__main__":
    # Run the main example
    asyncio.run(main())
    
    # Uncomment to run direct example
    # asyncio.run(direct_modbus_example())