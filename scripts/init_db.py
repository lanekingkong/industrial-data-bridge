#!/usr/bin/env python3
"""
Database initialization script for Industrial Data Bridge.
Creates tables, indexes, and initial data.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_config
from src.utils.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize database with tables and initial data."""
    config = load_config()
    db = DatabaseManager(config.database)
    
    logger.info("Initializing database...")
    
    try:
        # Connect to database
        await db.connect()
        logger.info("Connected to database")
        
        # Read SQL initialization script
        sql_file = Path(__file__).parent.parent / "docker" / "init-postgres.sql"
        if sql_file.exists():
            with open(sql_file, "r") as f:
                sql_script = f.read()
            
            # Execute SQL script
            await db.execute_raw(sql_script)
            logger.info("Database schema created")
        else:
            logger.warning(f"SQL file not found: {sql_file}")
        
        # Create additional indexes if needed
        await create_additional_indexes(db)
        
        # Insert initial data
        await insert_initial_data(db)
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await db.disconnect()


async def create_additional_indexes(db: DatabaseManager):
    """Create additional performance indexes."""
    indexes = [
        # Composite index for device data queries
        "CREATE INDEX IF NOT EXISTS idx_device_data_composite ON device_data(device_id, timestamp DESC) WHERE quality = 'good'",
        
        # Index for anomaly events by severity and timestamp
        "CREATE INDEX IF NOT EXISTS idx_anomaly_events_composite ON anomaly_events(severity, timestamp DESC) WHERE acknowledged = false",
        
        # Index for maintenance predictions by risk level
        "CREATE INDEX IF NOT EXISTS idx_maintenance_risk ON maintenance_predictions(risk_level, timestamp DESC) WHERE risk_level IN ('high', 'critical')",
        
        # Index for device status queries
        "CREATE INDEX IF NOT EXISTS idx_devices_composite ON devices(status, protocol, last_seen DESC)",
        
        # Index for edge agent monitoring
        "CREATE INDEX IF NOT EXISTS idx_edge_agents_heartbeat ON edge_agents(status, last_heartbeat DESC)",
    ]
    
    for idx_sql in indexes:
        try:
            await db.execute_raw(idx_sql)
            logger.debug(f"Created index: {idx_sql[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to create index: {e}")


async def insert_initial_data(db: DatabaseManager):
    """Insert initial configuration data."""
    logger.info("Inserting initial data...")
    
    # Insert default protocol configurations
    protocols = [
        {
            "name": "modbus_tcp",
            "description": "Modbus TCP protocol for industrial PLCs",
            "config_template": {
                "mode": "tcp",
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
                "timeout": 5.0,
                "retries": 3
            }
        },
        {
            "name": "modbus_rtu",
            "description": "Modbus RTU protocol for serial devices",
            "config_template": {
                "mode": "rtu",
                "port": "COM3",
                "baudrate": 9600,
                "bytesize": 8,
                "parity": "N",
                "stopbits": 1,
                "timeout": 3.0,
                "retries": 3
            }
        },
        {
            "name": "opcua",
            "description": "OPC UA protocol for modern industrial systems",
            "config_template": {
                "endpoint": "opc.tcp://localhost:4840",
                "security_mode": "None",
                "security_policy": "None",
                "timeout": 10.0,
                "retries": 2
            }
        },
        {
            "name": "mqtt",
            "description": "MQTT protocol for IoT devices",
            "config_template": {
                "host": "localhost",
                "port": 1883,
                "client_id": "idb-client",
                "username": "",
                "password": "",
                "qos": 1,
                "keepalive": 60
            }
        },
        {
            "name": "http",
            "description": "HTTP/REST API for web-enabled devices",
            "config_template": {
                "base_url": "http://localhost:8080",
                "timeout": 10.0,
                "retries": 3,
                "auth_type": "basic",
                "verify_ssl": true
            }
        }
    ]
    
    for protocol in protocols:
        await db.execute(
            """
            INSERT INTO protocol_configs (name, description, config_template, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (name) DO UPDATE SET
                description = EXCLUDED.description,
                config_template = EXCLUDED.config_template,
                updated_at = NOW()
            """,
            protocol["name"],
            protocol["description"],
            protocol["config_template"]
        )
    
    # Insert default device types
    device_types = [
        ("pump", "Industrial pump", "Pumps and pumping systems"),
        ("compressor", "Air compressor", "Compressed air systems"),
        ("fan", "Ventilation fan", "HVAC and ventilation systems"),
        ("motor", "Electric motor", "Motor drives and controllers"),
        ("sensor", "Sensor device", "Various sensor types"),
        ("controller", "PLC controller", "Programmable logic controllers"),
        ("valve", "Control valve", "Valves and actuators"),
        ("conveyor", "Conveyor system", "Material handling systems"),
    ]
    
    for type_name, display_name, description in device_types:
        await db.execute(
            """
            INSERT INTO device_types (type_name, display_name, description, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (type_name) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                description = EXCLUDED.description,
                updated_at = NOW()
            """,
            type_name,
            display_name,
            description
        )
    
    # Insert default alert rules
    alert_rules = [
        {
            "name": "device_offline",
            "description": "Device has been offline for more than 5 minutes",
            "condition": {
                "field": "status",
                "operator": "eq",
                "value": "offline",
                "duration": 300
            },
            "severity": "critical",
            "cooldown_seconds": 300,
            "notify_channels": ["webhook", "email"]
        },
        {
            "name": "high_temperature",
            "description": "Temperature exceeds safe operating range",
            "condition": {
                "field": "temperature",
                "operator": "gt",
                "value": 80,
                "unit": "celsius"
            },
            "severity": "warning",
            "cooldown_seconds": 60,
            "notify_channels": ["webhook"]
        },
        {
            "name": "vibration_high",
            "description": "Vibration level indicates potential bearing failure",
            "condition": {
                "field": "vibration",
                "operator": "gt",
                "value": 0.5,
                "unit": "mm/s"
            },
            "severity": "warning",
            "cooldown_seconds": 300,
            "notify_channels": ["webhook", "slack"]
        },
        {
            "name": "pressure_low",
            "description": "Pressure below minimum operating level",
            "condition": {
                "field": "pressure",
                "operator": "lt",
                "value": 2,
                "unit": "bar"
            },
            "severity": "warning",
            "cooldown_seconds": 120,
            "notify_channels": ["webhook"]
        },
        {
            "name": "anomaly_detected",
            "description": "AI anomaly detection identified abnormal behavior",
            "condition": {
                "field": "anomaly_score",
                "operator": "gt",
                "value": 0.8
            },
            "severity": "warning",
            "cooldown_seconds": 300,
            "notify_channels": ["webhook", "email", "slack"]
        }
    ]
    
    for rule in alert_rules:
        await db.execute(
            """
            INSERT INTO alert_rules (name, description, condition, severity, cooldown_seconds, notify_channels, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (name) DO UPDATE SET
                description = EXCLUDED.description,
                condition = EXCLUDED.condition,
                severity = EXCLUDED.severity,
                cooldown_seconds = EXCLUDED.cooldown_seconds,
                notify_channels = EXCLUDED.notify_channels,
                updated_at = NOW()
            """,
            rule["name"],
            rule["description"],
            rule["condition"],
            rule["severity"],
            rule["cooldown_seconds"],
            rule["notify_channels"]
        )
    
    logger.info(f"Inserted {len(protocols)} protocols, {len(device_types)} device types, {len(alert_rules)} alert rules")


async def verify_database():
    """Verify database structure and connectivity."""
    config = load_config()
    db = DatabaseManager(config.database)
    
    logger.info("Verifying database...")
    
    try:
        await db.connect()
        
        # Check if tables exist
        tables = ["users", "devices", "device_data", "anomaly_events", "maintenance_predictions", "edge_agents"]
        
        for table in tables:
            result = await db.fetch_one(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                table
            )
            exists = result[0] if result else False
            status = "✓" if exists else "✗"
            logger.info(f"  {status} {table}")
        
        # Count records
        counts = await db.fetch_all("""
            SELECT 'users' as table_name, COUNT(*) as count FROM users
            UNION ALL
            SELECT 'devices', COUNT(*) FROM devices
            UNION ALL
            SELECT 'device_data', COUNT(*) FROM device_data
            UNION ALL
            SELECT 'anomaly_events', COUNT(*) FROM anomaly_events
            UNION ALL
            SELECT 'maintenance_predictions', COUNT(*) FROM maintenance_predictions
            UNION ALL
            SELECT 'edge_agents', COUNT(*) FROM edge_agents
        """)
        
        logger.info("Record counts:")
        for row in counts:
            logger.info(f"  {row['table_name']}: {row['count']}")
        
        # Check database performance
        await db.execute("VACUUM ANALYZE")
        logger.info("Database optimization completed")
        
        logger.info("Database verification passed!")
        
    except Exception as e:
        logger.error(f"Database verification failed: {e}", exc_info=True)
        return False
    finally:
        await db.disconnect()
    
    return True


async def backup_database():
    """Create a database backup."""
    import subprocess
    import datetime
    
    config = load_config()
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"idb_backup_{timestamp}.sql"
    
    logger.info(f"Creating database backup: {backup_file}")
    
    # Create backup directory
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    # Use pg_dump to create backup
    cmd = [
        "pg_dump",
        f"--host={config.database.host}",
        f"--port={config.database.port}",
        f"--username={config.database.username}",
        f"--dbname={config.database.database}",
        "--format=custom",
        "--compress=9",
        f"--file={backup_dir / backup_file}"
    ]
    
    try:
        # Set password in environment
        env = {**os.environ, "PGPASSWORD": config.database.password}
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            file_size = (backup_dir / backup_file).stat().st_size / (1024 * 1024)
            logger.info(f"Backup created successfully: {backup_file} ({file_size:.2f} MB)")
            
            # Clean up old backups (keep last 7 days)
            cleanup_old_backups(backup_dir)
        else:
            logger.error(f"Backup failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Backup failed: {e}")


def cleanup_old_backups(backup_dir: Path, days_to_keep: int = 7):
    """Remove backup files older than specified days."""
    import datetime
    
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
    
    for backup_file in backup_dir.glob("idb_backup_*.sql"):
        if backup_file.stat().st_mtime < cutoff.timestamp():
            backup_file.unlink()
            logger.info(f"Removed old backup: {backup_file.name}")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Industrial Data Bridge Database Manager")
    parser.add_argument("action", choices=["init", "verify", "backup", "all"], 
                       help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "init":
        await init_database()
    elif args.action == "verify":
        success = await verify_database()
        sys.exit(0 if success else 1)
    elif args.action == "backup":
        await backup_database()
    elif args.action == "all":
        await init_database()
        success = await verify_database()
        if success:
            await backup_database()
        else:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())