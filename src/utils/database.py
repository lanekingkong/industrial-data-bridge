"""
Industrial Data Bridge - Database Utilities
Async PostgreSQL access layer with connection pooling and in-memory fallback.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

_fallback_store: Dict[str, List[Dict]] = {}


class DataBase:
    """Async database access layer. Uses in-memory store in fallback mode."""

    def __init__(self, dsn: str = ""):
        self.dsn = dsn
        self.pool = None
        self.use_fallback = not dsn
        self.initialized = False

    async def initialize(self):
        if self.initialized:
            return
        if self.dsn:
            try:
                import asyncpg
                self.pool = await asyncpg.create_pool(
                    dsn=self.dsn, min_size=2, max_size=20
                )
                logger.info("PostgreSQL pool created")
            except Exception as e:
                logger.warning(f"PostgreSQL unavailable, using in-memory: {e}")
                self.use_fallback = True
        else:
            self.use_fallback = True
        self.initialized = True

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
        self.initialized = False

    async def insert_data_point(
        self, device_id: str, point_name: str,
        value, unit: str = "", quality: str = "good"
    ):
        ts = datetime.utcnow().isoformat()
        row = {
            "device_id": device_id, "point_name": point_name,
            "value": value, "unit": unit, "quality": quality,
            "timestamp": ts,
        }
        if self.use_fallback:
            _fallback_store.setdefault(device_id, []).append(row)
        else:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO data_points
                       (device_id, point_name, value, unit, quality, timestamp)
                       VALUES ($1,$2,$3,$4,$5,$6)""",
                    device_id, point_name, str(value), unit, quality, ts,
                )

    async def query_data_points(
        self, device_id: str, point_name: Optional[str] = None,
        start_time: Optional[str] = None, end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        if self.use_fallback:
            rows = _fallback_store.get(device_id, [])
            if point_name:
                rows = [r for r in rows if r["point_name"] == point_name]
            return rows[-limit:]

        query = "SELECT * FROM data_points WHERE device_id = $1"
        params: list = [device_id]
        idx = 2
        if point_name:
            query += f" AND point_name = ${idx}"
            params.append(point_name)
            idx += 1
        query += f" ORDER BY timestamp DESC LIMIT ${idx}"
        params.append(limit)

        async with self.pool.acquire() as conn:
            records = await conn.fetch(query, *params)
            return [dict(r) for r in records]

    async def get_system_stats(self) -> Dict[str, Any]:
        if self.use_fallback:
            total = sum(len(v) for v in _fallback_store.values())
            return {"total_points": total, "devices": len(_fallback_store)}
        async with self.pool.acquire() as conn:
            dp = await conn.fetchrow("SELECT COUNT(*) as c FROM data_points")
            dd = await conn.fetchrow(
                "SELECT COUNT(DISTINCT device_id) as c FROM data_points"
            )
            return {"total_points": dp["c"], "devices": dd["c"]}


db = DataBase()