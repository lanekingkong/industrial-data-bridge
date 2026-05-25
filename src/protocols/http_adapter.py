"""
Industrial Data Bridge - HTTP Protocol Adapter
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

import aiohttp
from aiohttp import ClientSession, BasicAuth

logger = logging.getLogger(__name__)


class HTTPAdapter:
    """HTTP/REST adapter with retry, rate limiting, and connection pooling."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.session: Optional[ClientSession] = None
        self.base_url = "http://localhost:8080"
        self.timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", 30))
        self.max_conn = self.config.get("max_connections", 100)
        self.max_conn_host = self.config.get("max_connections_per_host", 10)
        self.retries = self.config.get("retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1)
        self.verify_ssl = self.config.get("verify_ssl", True)
        self.username = None
        self.password = None
        self.headers = {}
        self.auth_type = "basic"
        self.api_key = None
        self.api_key_header = "X-API-Key"
        self.bearer_token = None
        self.is_connected = False
        self._rate_times: List[float] = []
        self.rate_limit = self.config.get("rate_limit", 0)
        self.rate_period = self.config.get("rate_limit_period", 1)
        self._stats = {"total": 0, "ok": 0, "fail": 0}

    @classmethod
    def create_from_config(cls, params: Dict[str, Any]) -> "HTTPAdapter":
        a = cls()
        a.base_url = params.get("base_url", "http://localhost:8080")
        a.username = params.get("username")
        a.password = params.get("password")
        a.headers = params.get("headers", {})
        a.auth_type = params.get("auth_type", "basic")
        a.api_key = params.get("api_key")
        a.api_key_header = params.get("api_key_header", "X-API-Key")
        a.bearer_token = params.get("bearer_token")
        return a

    async def connect(self) -> bool:
        if self.is_connected:
            return True
        try:
            hdrs = dict(self.headers)
            hdrs.setdefault("User-Agent", "IndustrialDataBridge/1.0.0")
            hdrs.setdefault("Accept", "application/json")
            if self.auth_type == "api_key" and self.api_key:
                hdrs[self.api_key_header] = self.api_key
            elif self.auth_type == "bearer" and self.bearer_token:
                hdrs["Authorization"] = f"Bearer {self.bearer_token}"
            conn = aiohttp.TCPConnector(limit=self.max_conn, limit_per_host=self.max_conn_host,
                                         ssl=self.verify_ssl)
            self.session = ClientSession(base_url=self.base_url, headers=hdrs,
                                         timeout=self.timeout, connector=conn)
            self.is_connected = True
            logger.info(f"HTTP session to {self.base_url}")
            return True
        except Exception as e:
            logger.error(f"HTTP session error: {e}")
            return False

    async def disconnect(self):
        if self.session and self.is_connected:
            await self.session.close()
            self.is_connected = False
            self.session = None

    async def test_connection(self) -> bool:
        if not self.is_connected or not self.session:
            return False
        try:
            async with self.session.get("/health") as r:
                return r.status < 500
        except:
            return False

    async def read_points(self, points: List[Dict[str, Any]]) -> List[Any]:
        if not self.is_connected:
            raise ConnectionError("HTTP not connected")
        results = []
        for cfg in points:
            try:
                endpoint = cfg.get("endpoint", "/")
                method = cfg.get("method", "GET").upper()
                params = cfg.get("params", {})
                val = await self._request(method, endpoint, params=params)
                results.append(val)
            except Exception as e:
                logger.error(f"HTTP read {cfg.get('name')}: {e}")
                results.append(None)
        return results

    async def write_point(self, cfg: Dict[str, Any], value) -> bool:
        if not self.is_connected:
            raise ConnectionError("HTTP not connected")
        try:
            endpoint = cfg.get("endpoint", "/")
            method = cfg.get("method", "POST").upper()
            await self._request(method, endpoint, json_data={"value": value})
            return True
        except Exception as e:
            logger.error(f"HTTP write error: {e}")
            return False

    async def _enforce_rate(self):
        if self.rate_limit <= 0:
            return
        now = datetime.now().timestamp()
        self._rate_times = [t for t in self._rate_times if now - t < self.rate_period]
        if len(self._rate_times) >= self.rate_limit:
            wait = self._rate_times[0] + self.rate_period - now
            if wait > 0:
                await asyncio.sleep(wait)
        self._rate_times.append(now)

    def _auth(self):
        if self.auth_type == "basic" and self.username and self.password:
            return BasicAuth(self.username, self.password)
        return None

    async def _request(self, method, url, params=None, json_data=None, data=None, retries=None):
        retries = retries if retries is not None else self.retries
        for attempt in range(retries + 1):
            try:
                await self._enforce_rate()
                async with self.session.request(method=method, url=url, params=params,
                                                json=json_data, data=data, auth=self._auth()) as r:
                    self._stats["total"] += 1
                    if r.status < 400:
                        self._stats["ok"] += 1
                        ct = r.headers.get("Content-Type", "")
                        if "application/json" in ct:
                            return await r.json()
                        return await r.text()
                    elif r.status in (429, 503):
                        wait = int(r.headers.get("Retry-After", self.retry_delay))
                        await asyncio.sleep(wait)
                        continue
                    else:
                        txt = await r.text()
                        self._stats["fail"] += 1
                        if attempt < retries:
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        raise Exception(f"HTTP {r.status}: {txt}")
            except aiohttp.ClientError as e:
                self._stats["fail"] += 1
                if attempt < retries:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise

    async def get(self, url, params=None):
        return await self._request("GET", url, params=params)

    async def post(self, url, json_data=None, data=None):
        return await self._request("POST", url, json_data=json_data, data=data)

    async def put(self, url, json_data=None):
        return await self._request("PUT", url, json_data=json_data)

    async def delete(self, url):
        return await self._request("DELETE", url)

    async def close(self):
        await self.disconnect()