"""
Industrial Data Bridge - Redis Client
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisManager:
    """Redis connection manager with connection pooling and helpers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 6379)
        self.db = self.config.get("db", 0)
        self.password = self.config.get("password")
        self.max_connections = self.config.get("max_connections", 20)
        self._pool: Optional[aioredis.ConnectionPool] = None
        self._client: Optional[aioredis.Redis] = None
        self.connected = False

    async def initialize(self):
        """Initialize Redis connection pool."""
        try:
            self._pool = aioredis.ConnectionPool(
                host=self.host, port=self.port, db=self.db,
                password=self.password, max_connections=self.max_connections,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            self._client = aioredis.Redis(connection_pool=self._pool)
            await self._client.ping()
            self.connected = True
            logger.info(f"Redis connected {self.host}:{self.port}")
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")
            self.connected = False

    @property
    def client(self) -> Optional[aioredis.Redis]:
        return self._client

    async def close(self):
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        self.connected = False
        logger.info("Redis closed")

    # --- Cache helpers ---
    async def get(self, key: str) -> Optional[str]:
        if not self.connected:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        if not self.connected:
            return
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            if expire:
                await self._client.setex(key, expire, str(value))
            else:
                await self._client.set(key, str(value))
        except Exception as e:
            logger.error(f"Redis SET error: {e}")

    async def delete(self, key: str):
        if not self.connected:
            return
        try:
            await self._client.delete(key)
        except Exception as e:
            logger.error(f"Redis DEL error: {e}")

    async def exists(self, key: str) -> bool:
        if not self.connected:
            return False
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False

    async def expire(self, key: str, ttl: int):
        if not self.connected:
            return
        try:
            await self._client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis EXPIRE error: {e}")

    # --- Pub/Sub ---
    async def publish(self, channel: str, message: Any):
        if not self.connected:
            return
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message, default=str)
            await self._client.publish(channel, str(message))
        except Exception as e:
            logger.error(f"Redis PUBLISH error: {e}")

    async def subscribe(self, channel: str):
        if not self.connected:
            return
        try:
            pubsub = self._client.pubsub()
            await pubsub.subscribe(channel)
            return pubsub
        except Exception as e:
            logger.error(f"Redis SUBSCRIBE error: {e}")
            return None

    # --- Health ---
    async def health(self) -> bool:
        if not self.connected:
            return False
        try:
            await self._client.ping()
            return True
        except:
            return False

    async def info(self) -> Dict:
        if not self.connected:
            return {}
        try:
            return await self._client.info()
        except:
            return {}