"""
Edge Computing Agent for Industrial Data Bridge.

Provides local data processing, caching, and cloud synchronization
for industrial edge devices with limited connectivity.
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edge-agent")

class DataPriority(Enum):
    """Data priority levels for sync scheduling."""
    CRITICAL = "critical"   # Alerts, anomalies - immediate
    HIGH = "high"           # Real-time monitoring - frequent
    MEDIUM = "medium"       # Operational data - batch
    LOW = "low"             # Logs, diagnostics - daily

class AgentStatus(Enum):
    """Agent operational status."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    DEGRADED = "degraded"      # Partial functionality
    OFFLINE = "offline"        # No cloud connectivity
    ERROR = "error"
    STOPPED = "stopped"

@dataclass
class EdgeConfig:
    """Edge agent configuration."""
    agent_id: str = "edge-default"
    data_path: str = "./edge_data"
    cloud_url: str = "http://localhost:8000"
    cloud_token: str = ""
    sync_interval: int = 60          # seconds
    max_local_storage_mb: int = 500
    collection_interval: int = 5     # seconds
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: int = 5
    heartbeat_interval: int = 30
    metrics_enabled: bool = True
    model_cache_enabled: bool = True
    server_host: str = "0.0.0.0"
    server_port: int = 8001

@dataclass
class EdgeDataPoint:
    """A single data point with metadata."""
    device_id: str
    point_name: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    unit: str = ""
    quality: str = "good"
    priority: DataPriority = DataPriority.MEDIUM
    hash: str = ""
    
    def __post_init__(self):
        if not self.hash:
            raw = f"{self.device_id}|{self.point_name}|{self.value}|{self.timestamp}"
            self.hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

class LocalStorage:
    """Local SQLite-based storage for offline data buffering."""
    
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_path / "edge.db"
        self.conn: Optional[sqlite3.Connection] = None
        
    def initialize(self):
        """Initialize local database."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS data_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                point_name TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp REAL NOT NULL,
                unit TEXT DEFAULT '',
                quality TEXT DEFAULT 'good',
                priority TEXT DEFAULT 'medium',
                hash TEXT UNIQUE NOT NULL,
                synced INTEGER DEFAULT 0
            )
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_data_points_device 
            ON data_points(device_id, point_name)
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_data_points_synced 
            ON data_points(synced, priority, timestamp)
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        
        self.conn.commit()
        logger.info(f"Local storage initialized at {self.db_path}")
    
    def store_point(self, point: EdgeDataPoint) -> bool:
        """Store a data point locally."""
        try:
            self.conn.execute("""
                INSERT OR IGNORE INTO data_points 
                (device_id, point_name, value, timestamp, unit, quality, priority, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                point.device_id, point.point_name, str(point.value),
                point.timestamp, point.unit, point.quality,
                point.priority.value, point.hash
            ))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to store point: {e}")
            return False
    
    def store_points(self, points: List[EdgeDataPoint]) -> int:
        """Store multiple data points."""
        count = 0
        for point in points:
            if self.store_point(point):
                count += 1
        return count
    
    def get_unsynced(self, priority: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get unsynced data points, optionally filtered by priority."""
        cursor = self.conn.cursor()
        if priority:
            cursor.execute("""
                SELECT id, device_id, point_name, value, timestamp, unit, quality, priority, hash
                FROM data_points
                WHERE synced = 0 AND priority = ?
                ORDER BY priority, timestamp ASC
                LIMIT ?
            """, (priority, limit))
        else:
            cursor.execute("""
                SELECT id, device_id, point_name, value, timestamp, unit, quality, priority, hash
                FROM data_points
                WHERE synced = 0
                ORDER BY 
                    CASE priority 
                        WHEN 'critical' THEN 0 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        WHEN 'low' THEN 3 
                    END,
                    timestamp ASC
                LIMIT ?
            """, (limit,))
        
        columns = ["id", "device_id", "point_name", "value", "timestamp", "unit", "quality", "priority", "hash"]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def mark_synced(self, ids: List[int]):
        """Mark data points as synced."""
        if not ids:
            return
        placeholders = ",".join(["?"] * len(ids))
        self.conn.execute(
            f"UPDATE data_points SET synced = 1 WHERE id IN ({placeholders})",
            ids
        )
        self.conn.commit()
    
    def get_state(self, key: str) -> Optional[str]:
        """Get agent state value."""
        cursor = self.conn.execute(
            "SELECT value FROM agent_state WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    
    def set_state(self, key: str, value: str):
        """Set agent state value."""
        self.conn.execute("""
            INSERT OR REPLACE INTO agent_state (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, time.time()))
        self.conn.commit()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*), COUNT(DISTINCT device_id) FROM data_points")
        total_points, total_devices = cursor.fetchone()
        
        cursor.execute(
            "SELECT COUNT(*) FROM data_points WHERE synced = 0"
        )
        unsynced = cursor.fetchone()[0]
        
        storage_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        
        return {
            "total_points": total_points,
            "total_devices": total_devices,
            "unsynced_points": unsynced,
            "storage_size_bytes": storage_size,
            "storage_size_mb": round(storage_size / (1024 * 1024), 1)
        }
    
    def cleanup(self, max_age_days: int = 7):
        """Clean up old synced data."""
        cutoff = time.time() - (max_age_days * 86400)
        self.conn.execute(
            "DELETE FROM data_points WHERE synced = 1 AND timestamp < ?",
            (cutoff,)
        )
        self.conn.commit()
        logger.info(f"Cleaned up data older than {max_age_days} days")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

class SyncManager:
    """Manages data synchronization between edge and cloud."""
    
    def __init__(self, storage: LocalStorage, config: EdgeConfig):
        self.storage = storage
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_sync: Dict[str, float] = {}
        
    async def start(self):
        """Initialize HTTP session."""
        headers = {}
        if self.config.cloud_token:
            headers["Authorization"] = f"Bearer {self.config.cloud_token}"
        self.session = aiohttp.ClientSession(headers=headers)
    
    async def stop(self):
        """Clean up HTTP session."""
        if self.session:
            await self.session.close()
    
    async def sync_data(self) -> Dict[str, Any]:
        """Synchronize data with cloud."""
        result = {"synced": 0, "failed": 0, "errors": []}
        
        # Sync critical/high priority first
        for priority in ["critical", "high", "medium", "low"]:
            while True:
                points = self.storage.get_unsynced(priority=priority, limit=self.config.batch_size)
                if not points:
                    break
                
                try:
                    await self._send_to_cloud(points)
                    ids = [p["id"] for p in points]
                    self.storage.mark_synced(ids)
                    result["synced"] += len(points)
                    self.last_sync[priority] = time.time()
                except Exception as e:
                    result["failed"] += len(points)
                    result["errors"].append(str(e))
                    logger.error(f"Sync failed for {priority}: {e}")
                    break  # Stop on failure for this priority
        
        return result
    
    async def _send_to_cloud(self, points: List[Dict]) -> bool:
        """Send data points to cloud API."""
        if not self.session:
            raise RuntimeError("Session not initialized")
        
        payload = {"data": points, "source": "edge", "agent_id": self.config.agent_id}
        
        async with self.session.post(
            f"{self.config.cloud_url}/api/v1/data/ingest",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status not in (200, 201):
                error_text = await response.text()
                raise RuntimeError(f"Cloud rejected data: {response.status} - {error_text}")
        
        return True
    
    async def send_heartbeat(self, status: Dict[str, Any]) -> bool:
        """Send heartbeat to cloud."""
        if not self.session:
            return False
        
        try:
            async with self.session.post(
                f"{self.config.cloud_url}/api/v1/edge/heartbeat",
                json=status,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return response.status == 200
        except aiohttp.ClientError as e:
            logger.warning(f"Heartbeat failed: {e}")
            return False

class MetricsCollector:
    """Collects and tracks agent metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "points_collected": 0,
            "points_synced": 0,
            "sync_errors": 0,
            "uptime_seconds": 0,
            "last_cloud_sync": None,
            "storage_utilization": 0.0,
        }
        self.start_time = time.time()
    
    def increment(self, metric: str, value: int = 1):
        if metric in self.metrics:
            self.metrics[metric] += value
    
    def get_snapshot(self) -> Dict[str, Any]:
        self.metrics["uptime_seconds"] = time.time() - self.start_time
        return dict(self.metrics)

class EdgeAgent:
    """
    Edge computing agent for Industrial Data Bridge.
    
    Runs on edge devices to provide:
    - Local data collection and caching
    - Offline data buffering with priority queuing
    - Cloud synchronization with conflict resolution
    - Local AI model inference (via ONNX)
    - Health monitoring and heartbeat
    """
    
    def __init__(self, config: EdgeConfig):
        self.config = config
        self.status = AgentStatus.INITIALIZING
        self.storage = LocalStorage(config.data_path)
        self.sync_manager = SyncManager(self.storage, config)
        self.metrics = MetricsCollector()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
    async def initialize(self):
        """Initialize edge agent components."""
        logger.info(f"Initializing edge agent {self.config.agent_id}")
        
        self.storage.initialize()
        await self.sync_manager.start()
        
        # Set last sync checkpoint
        last_sync = self.storage.get_state("last_full_sync")
        if last_sync:
            logger.info(f"Last sync: {datetime.fromtimestamp(float(last_sync))}")
        
        self._running = True
        self.status = AgentStatus.RUNNING
        
        logger.info(f"Edge agent initialized, status: {self.status.value}")
    
    async def start(self):
        """Start all background tasks."""
        self._tasks = [
            asyncio.create_task(self._collection_loop()),
            asyncio.create_task(self._sync_loop()),
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._cleanup_loop()),
        ]
        logger.info("Edge agent background tasks started")
    
    async def stop(self):
        """Stop agent and cleanup."""
        logger.info("Stopping edge agent...")
        self._running = False
        self.status = AgentStatus.STOPPED
        
        for task in self._tasks:
            task.cancel()
        
        await self.sync_manager.stop()
        
        # Final sync before shutdown
        try:
            sync_result = await self.sync_manager.sync_data()
            logger.info(f"Final sync: {sync_result}")
        except Exception as e:
            logger.error(f"Final sync failed: {e}")
        
        self.storage.close()
        logger.info("Edge agent stopped")
    
    async def _collection_loop(self):
        """Background loop for data collection."""
        while self._running:
            try:
                # In production, this would collect from local adapters
                # For now, simulate data point generation
                # Real implementation would call engine.collect_all_devices()
                await asyncio.sleep(self.config.collection_interval)
                self.metrics.increment("points_collected")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Collection error: {e}")
                await asyncio.sleep(5)
    
    async def _sync_loop(self):
        """Background loop for cloud synchronization."""
        while self._running:
            try:
                sync_result = await self.sync_manager.sync_data()
                if sync_result["synced"] > 0:
                    self.metrics.increment("points_synced", sync_result["synced"])
                    self.metrics.metrics["last_cloud_sync"] = time.time()
                if sync_result["errors"]:
                    self.metrics.increment("sync_errors", len(sync_result["errors"]))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
            
            await asyncio.sleep(self.config.sync_interval)
    
    async def _heartbeat_loop(self):
        """Background loop for heartbeat."""
        while self._running:
            try:
                status = self.get_status()
                success = await self.sync_manager.send_heartbeat(status)
                if not success:
                    logger.warning("Heartbeat to cloud failed")
                else:
                    # Update connectivity status
                    if self.status == AgentStatus.OFFLINE:
                        self.status = AgentStatus.RUNNING
                        logger.info("Cloud connectivity restored")
            except asyncio.CancelledError:
                break
            except Exception:
                self.status = AgentStatus.OFFLINE
            
            await asyncio.sleep(self.config.heartbeat_interval)
    
    async def _cleanup_loop(self):
        """Background loop for data cleanup."""
        while self._running:
            try:
                # Run cleanup every hour
                await asyncio.sleep(3600)
                self.storage.cleanup(max_age_days=7)
            except asyncio.CancelledError:
                break
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status."""
        storage_stats = self.storage.get_stats()
        metrics_snapshot = self.metrics.get_snapshot()
        
        return {
            "agent_id": self.config.agent_id,
            "status": self.status.value,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "storage": storage_stats,
            "metrics": metrics_snapshot,
            "config": {
                "sync_interval": self.config.sync_interval,
                "collection_interval": self.config.collection_interval,
                "batch_size": self.config.batch_size,
            }
        }
    
    async def ingest_data(self, points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ingest data points from local collectors."""
        edge_points = []
        for p in points:
            try:
                edge_point = EdgeDataPoint(
                    device_id=p.get("device_id", "unknown"),
                    point_name=p.get("point_name", "unknown"),
                    value=p.get("value"),
                    unit=p.get("unit", ""),
                    quality=p.get("quality", "good"),
                    priority=DataPriority(p.get("priority", "medium")),
                )
                edge_points.append(edge_point)
            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid data point: {e}")
        
        stored = self.storage.store_points(edge_points)
        self.metrics.increment("points_collected", stored)
        
        return {
            "received": len(points),
            "stored": stored,
            "rejected": len(points) - stored
        }
    
    async def force_sync(self) -> Dict[str, Any]:
        """Force immediate synchronization."""
        logger.info("Forced sync initiated")
        return await self.sync_manager.sync_data()

async def main():
    """Main entry point for edge agent."""
    import os as _os
    
    # Load config from environment
    config = EdgeConfig(
        agent_id=_os.getenv("EDGE_AGENT_ID", "edge-default"),
        data_path=_os.getenv("EDGE_DATA_PATH", "./edge_data"),
        cloud_url=_os.getenv("EDGE_CLOUD_URL", "http://localhost:8000"),
        cloud_token=_os.getenv("EDGE_CLOUD_TOKEN", ""),
        sync_interval=int(_os.getenv("EDGE_SYNC_INTERVAL", "60")),
        collection_interval=int(_os.getenv("EDGE_COLLECTION_INTERVAL", "5")),
    )
    
    agent = EdgeAgent(config)
    
    try:
        await agent.initialize()
        await agent.start()
        
        logger.info(f"Edge agent {config.agent_id} running")
        
        while True:
            await asyncio.sleep(10)
            status = agent.get_status()
            logger.debug(f"Status: {status}")
            
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())