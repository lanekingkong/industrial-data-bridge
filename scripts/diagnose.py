#!/usr/bin/env python3
"""
Diagnostic tool for Industrial Data Bridge.
Checks system health, connectivity, and configuration.
"""

import asyncio
import json
import logging
import platform
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import load_config
from src.utils.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemDiagnostics:
    """System diagnostics and health checks."""
    
    def __init__(self, config=None):
        self.config = config or load_config()
        self.results = {}
        self.start_time = time.time()
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all diagnostic checks."""
        logger.info("Running system diagnostics...")
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "system": await self.check_system(),
            "python": await self.check_python(),
            "network": await self.check_network(),
            "database": await self.check_database(),
            "redis": await self.check_redis(),
            "influxdb": await self.check_influxdb(),
            "mqtt": await self.check_mqtt(),
            "config": await self.check_config(),
            "filesystem": await self.check_filesystem(),
            "services": await self.check_services(),
            "summary": {}
        }
        
        # Generate summary
        self.results["summary"] = self.generate_summary()
        
        return self.results
    
    async def check_system(self) -> Dict[str, Any]:
        """Check system information."""
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "cpu_count": self._get_cpu_count(),
            "memory": self._get_memory_info(),
            "disk": self._get_disk_info(),
        }
        
        return info
    
    async def check_python(self) -> Dict[str, Any]:
        """Check Python environment and dependencies."""
        import importlib.metadata
        
        dependencies = [
            "aiohttp", "asyncpg", "redis", "influxdb-client", "pymodbus", 
            "opcua", "paho-mqtt", "scikit-learn", "pandas", "numpy",
            "fastapi", "uvicorn", "pydantic", "python-multipart"
        ]
        
        installed = {}
        for dep in dependencies:
            try:
                version = importlib.metadata.version(dep)
                installed[dep] = version
            except importlib.metadata.PackageNotFoundError:
                installed[dep] = "NOT INSTALLED"
        
        return {
            "dependencies": installed,
            "python_path": sys.path,
            "virtual_env": sys.prefix != sys.base_prefix,
        }
    
    async def check_network(self) -> Dict[str, Any]:
        """Check network connectivity."""
        checks = {}
        
        # Check localhost
        checks["localhost"] = await self._check_port("localhost", 8000)
        
        # Check database
        checks["database"] = await self._check_port(
            self.config.database.host, 
            self.config.database.port
        )
        
        # Check Redis
        checks["redis"] = await self._check_port(
            self.config.redis.host, 
            self.config.redis.port
        )
        
        # Check InfluxDB
        checks["influxdb"] = await self._check_port(
            self.config.influxdb.host,
            self.config.influxdb.port
        )
        
        # Check MQTT
        checks["mqtt"] = await self._check_port(
            self.config.mqtt.host,
            self.config.mqtt.port
        )
        
        # Check internet connectivity
        checks["internet"] = await self._check_internet()
        
        return checks
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and health."""
        db = DatabaseManager(self.config.database)
        
        try:
            await db.connect()
            
            # Check connection
            result = await db.fetch_one("SELECT version()")
            version = result[0] if result else "Unknown"
            
            # Check tables
            tables = await db.fetch_all("""
                SELECT table_name, pg_size_pretty(pg_total_relation_size('"' || table_name || '"')) as size
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            # Check performance
            performance = await db.fetch_one("""
                SELECT 
                    (SELECT count(*) FROM pg_stat_activity) as connections,
                    (SELECT count(*) FROM pg_stat_user_tables) as user_tables,
                    (SELECT pg_database_size(current_database())) as db_size
            """)
            
            return {
                "connected": True,
                "version": version,
                "tables": [dict(row) for row in tables],
                "performance": dict(performance) if performance else {},
                "error": None
            }
            
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
        finally:
            await db.disconnect()
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        import redis.asyncio as redis
        
        try:
            client = redis.Redis(
                host=self.config.redis.host,
                port=self.config.redis.port,
                password=self.config.redis.password or None,
                db=self.config.redis.db,
                socket_timeout=self.config.redis.socket_timeout,
                socket_connect_timeout=self.config.redis.socket_connect_timeout,
            )
            
            # Test connection
            pong = await client.ping()
            info = await client.info()
            
            return {
                "connected": pong,
                "version": info.get("redis_version", "Unknown"),
                "used_memory": info.get("used_memory_human", "Unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "error": None
            }
            
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def check_influxdb(self) -> Dict[str, Any]:
        """Check InfluxDB connectivity."""
        from influxdb_client import InfluxDBClient
        
        try:
            client = InfluxDBClient(
                url=f"http://{self.config.influxdb.host}:{self.config.influxdb.port}",
                token=self.config.influxdb.token,
                org=self.config.influxdb.org,
                timeout=10_000
            )
            
            # Test connection by querying buckets
            buckets_api = client.buckets_api()
            buckets = buckets_api.find_buckets()
            
            return {
                "connected": True,
                "buckets": [bucket.name for bucket in buckets.buckets],
                "org": self.config.influxdb.org,
                "error": None
            }
            
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def check_mqtt(self) -> Dict[str, Any]:
        """Check MQTT broker connectivity."""
        import paho.mqtt.client as mqtt
        
        result = {
            "connected": False,
            "error": None
        }
        
        def on_connect(client, userdata, flags, rc):
            result["connected"] = rc == 0
            result["return_code"] = rc
            client.disconnect()
        
        def on_disconnect(client, userdata, rc):
            pass
        
        try:
            client = mqtt.Client(client_id="diagnostic")
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            
            if self.config.mqtt.username:
                client.username_pw_set(
                    self.config.mqtt.username,
                    self.config.mqtt.password
                )
            
            client.connect_async(
                self.config.mqtt.host,
                self.config.mqtt.port,
                keepalive=self.config.mqtt.keepalive
            )
            
            client.loop_start()
            time.sleep(2)  # Wait for connection
            client.loop_stop()
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def check_config(self) -> Dict[str, Any]:
        """Check configuration validity."""
        issues = []
        
        # Check required fields
        required_fields = [
            ("database.host", self.config.database.host),
            ("database.port", self.config.database.port),
            ("database.database", self.config.database.database),
            ("database.username", self.config.database.username),
            ("server.host", self.config.server.host),
            ("server.port", self.config.server.port),
        ]
        
        for field, value in required_fields:
            if not value:
                issues.append(f"Missing required field: {field}")
        
        # Check security
        if self.config.security.jwt.secret_key == "change-this-in-production":
            issues.append("WARNING: Using default JWT secret key")
        
        # Check paths
        paths_to_check = [
            ("logs", Path("./logs")),
            ("data", Path("./data")),
            ("models", Path("./models")),
        ]
        
        for name, path in paths_to_check:
            if not path.exists():
                issues.append(f"Directory does not exist: {name} ({path})")
            elif not os.access(path, os.W_OK):
                issues.append(f"Directory not writable: {name} ({path})")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "config_summary": {
                "server": f"{self.config.server.host}:{self.config.server.port}",
                "database": f"{self.config.database.host}:{self.config.database.port}/{self.config.database.database}",
                "redis": f"{self.config.redis.host}:{self.config.redis.port}",
                "influxdb": f"{self.config.influxdb.host}:{self.config.influxdb.port}",
                "mqtt": f"{self.config.mqtt.host}:{self.config.mqtt.port}",
            }
        }
    
    async def check_filesystem(self) -> Dict[str, Any]:
        """Check filesystem health and permissions."""
        import shutil
        
        checks = {}
        
        # Check disk space
        total, used, free = shutil.disk_usage(".")
        checks["disk_space"] = {
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "percent_used": round(used / total * 100, 1)
        }
        
        # Check important directories
        directories = [
            (".", "Project root"),
            ("./logs", "Logs directory"),
            ("./data", "Data directory"),
            ("./models", "AI models directory"),
            ("./config", "Config directory"),
        ]
        
        dir_checks = {}
        for path, description in directories:
            dir_path = Path(path)
            dir_checks[description] = {
                "exists": dir_path.exists(),
                "writable": os.access(dir_path, os.W_OK) if dir_path.exists() else False,
                "path": str(dir_path.absolute())
            }
        
        checks["directories"] = dir_checks
        
        # Check file permissions
        important_files = [
            (".env", "Environment variables"),
            ("config/config.yaml", "Main config file"),
            ("requirements.txt", "Dependencies"),
        ]
        
        file_checks = {}
        for file_path, description in important_files:
            path = Path(file_path)
            file_checks[description] = {
                "exists": path.exists(),
                "readable": os.access(path, os.R_OK) if path.exists() else False,
                "size": path.stat().st_size if path.exists() else 0
            }
        
        checks["files"] = file_checks
        
        return checks
    
    async def check_services(self) -> Dict[str, Any]:
        """Check if required services are running."""
        services = [
            ("API Server", "localhost", 8000),
            ("Database", self.config.database.host, self.config.database.port),
            ("Redis", self.config.redis.host, self.config.redis.port),
            ("InfluxDB", self.config.influxdb.host, self.config.influxdb.port),
            ("MQTT Broker", self.config.mqtt.host, self.config.mqtt.port),
        ]
        
        results = {}
        for name, host, port in services:
            results[name] = await self._check_port(host, port)
        
        return results
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of diagnostic results."""
        summary = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "warnings": 0,
            "critical_issues": [],
            "warnings_list": [],
            "overall_status": "HEALTHY"
        }
        
        # Check network connectivity
        network = self.results.get("network", {})
        for service, status in network.items():
            summary["total_checks"] += 1
            if status.get("connected", False):
                summary["passed_checks"] += 1
            else:
                summary["failed_checks"] += 1
                if service in ["database", "redis"]:
                    summary["critical_issues"].append(f"{service} is not reachable")
        
        # Check database
        db = self.results.get("database", {})
        summary["total_checks"] += 1
        if db.get("connected", False):
            summary["passed_checks"] += 1
        else:
            summary["failed_checks"] += 1
            summary["critical_issues"].append(f"Database: {db.get('error', 'Unknown error')}")
        
        # Check config
        config = self.results.get("config", {})
        if not config.get("valid", False):
            summary["warnings"] += len(config.get("issues", []))
            summary["warnings_list"].extend(config.get("issues", []))
        
        # Check filesystem
        fs = self.results.get("filesystem", {})
        disk_space = fs.get("disk_space", {})
        if disk_space.get("percent_used", 0) > 90:
            summary["warnings"] += 1
            summary["warnings_list"].append(
                f"Disk space low: {disk_space.get('percent_used')}% used"
            )
        
        # Determine overall status
        if summary["critical_issues"]:
            summary["overall_status"] = "CRITICAL"
        elif summary["failed_checks"] > 0:
            summary["overall_status"] = "UNHEALTHY"
        elif summary["warnings"] > 0:
            summary["overall_status"] = "WARNING"
        else:
            summary["overall_status"] = "HEALTHY"
        
        summary["diagnostic_duration"] = round(time.time() - self.start_time, 2)
        
        return summary
    
    # Helper methods
    def _get_cpu_count(self) -> int:
        """Get CPU count."""
        try:
            import multiprocessing
            return multiprocessing.cpu_count()
        except:
            return 1
    
    def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory information."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "percent_used": mem.percent
            }
        except ImportError:
            return {"error": "psutil not installed"}
    
    def _get_disk_info(self) -> Dict[str, Any]:
        """Get disk information."""
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            return {
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "percent_used": round(used / total * 100, 1)
            }
        except:
            return {"error": "Could not get disk info"}
    
    async def _check_port(self, host: str, port: int) -> Dict[str, Any]:
        """Check if a port is open."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=2.0
            )
            writer.close()
            await writer.wait_closed()
            return {"connected": True, "host": host, "port": port}
        except (ConnectionRefusedError, asyncio.TimeoutError, OSError) as e:
            return {"connected": False, "host": host, "port": port, "error": str(e)}
    
    async def _check_internet(self) -> Dict[str, Any]:
        """Check internet connectivity."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("8.8.8.8", 53),
                timeout=3.0
            )
            writer.close()
            await writer.wait_closed()
            return {"connected": True}
        except:
            return {"connected": False}


def print_diagnostic_report(results: Dict[str, Any]):
    """Print a formatted diagnostic report."""
    summary = results.get("summary", {})
    
    print("\n" + "="*60)
    print("INDUSTRIAL DATA BRIDGE - DIAGNOSTIC REPORT")
    print("="*60)
    print(f"Timestamp: {results.get('timestamp', 'Unknown')}")
    print(f"Overall Status: {summary.get('overall_status', 'UNKNOWN')}")
    print(f"Duration: {summary.get('diagnostic_duration', 0)} seconds")
    print("="*60)
    
    # System Info
    print("\n[SYSTEM INFORMATION]")
    system = results.get("system", {})
    print(f"  Platform: {system.get('platform', 'Unknown')}")
    print(f"  Python: {system.get('python_version', 'Unknown')}")
    print(f"  CPU Cores: {system.get('cpu_count', 'Unknown')}")
    
    # Network Connectivity
    print("\n[NETWORK CONNECTIVITY]")
    network = results.get("network", {})
    for service, status in network.items():
        icon = "✓" if status.get("connected", False) else "✗"
        print(f"  {icon} {service}: {status.get('host', '')}:{status.get('port', '')}")
    
    # Database
    print("\n[DATABASE]")
    db = results.get("database", {})
    icon = "✓" if db.get("connected", False) else "✗"
    print(f"  {icon} PostgreSQL: {db.get('version', 'Unknown')}")
    if db.get("connected"):
        print(f"    Tables: {len(db.get('tables', []))}")
    
    # Filesystem
    print("\n[FILESYSTEM]")
    fs = results.get("filesystem", {})
    disk = fs.get("disk_space", {})
    print(f"  Disk: {disk.get('used_gb', 0)}/{disk.get('total_gb', 0)} GB ({disk.get('percent_used', 0)}% used)")
    
    # Configuration
    print("\n[CONFIGURATION]")
    config = results.get("config", {})
    if config.get("valid", False):
        print("  ✓ Configuration is valid")
    else:
        print("  ✗ Configuration has issues:")
        for issue in config.get("issues", []):
            print(f"    - {issue}")
    
    # Summary
    print("\n" + "="*60)
    print("[SUMMARY]")
    print(f"  Total Checks: {summary.get('total_checks', 0)}")
    print(f"  Passed: {summary.get('passed_checks', 0)}")
    print(f"  Failed: {summary.get('failed_checks', 0)}")
    print(f"  Warnings: {summary.get('warnings', 0)}")
    
    if summary.get("critical_issues"):
        print("\n  [CRITICAL ISSUES]")
        for issue in summary.get("critical_issues", []):
            print(f"    • {issue}")
    
    if summary.get("warnings_list"):
        print("\n  [WARNINGS]")
        for warning in summary.get("warnings_list", []):
            print(f"    • {warning}")
    
    print("\n" + "="*60)
    print(f"Diagnostic completed. Status: {summary.get('overall_status', 'UNKNOWN')}")
    print("="*60)


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Industrial Data Bridge Diagnostic Tool")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text",
                       help="Output format")
    parser.add_argument("--save", "-s", action="store_true",
                       help="Save results to file")
    
    args = parser.parse_args()
    
    # Run diagnostics
    diag = SystemDiagnostics()
    results = await diag.run_all_checks()
    
    # Output results
    if args.output == "json":
        output = json.dumps(results, indent=2, default=str)
        print(output)
    else:
        print_diagnostic_report(results)
    
    # Save to file if requested
    if args.save:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"diagnostic_report_{timestamp}.json"
        
        with open(filename, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Diagnostic report saved to {filename}")
    
    # Exit with appropriate code
    summary = results.get("summary", {})
    if summary.get("overall_status") == "CRITICAL":
        sys.exit(2)
    elif summary.get("overall_status") == "UNHEALTHY":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())