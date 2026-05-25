"""
Industrial Data Bridge - Main Application Entry Point
AI-powered industrial device data collection and protocol conversion.
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from src.core.engine import BridgeEngine
from src.web.routes import router as api_router
from src.utils.database import db
from src.utils.redis_client import RedisManager
from src.utils.config import load_config

logger = logging.getLogger(__name__)


class IndustrialDataBridge:
    def __init__(self, config_path: Optional[str] = None):
        self.config = load_config(config_path)
        self.engine: Optional[BridgeEngine] = None
        self.app: Optional[FastAPI] = None
        self.server: Optional[uvicorn.Server] = None
        self.redis: Optional[RedisManager] = None
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(self.shutdown()))
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(self.shutdown()))

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        logger.info("Starting Industrial Data Bridge...")
        try:
            await db.initialize()
            logger.info("Database initialized")
            self.redis = RedisManager(self.config.get("redis", {}))
            await self.redis.initialize()
            logger.info("Redis initialized")
            self.engine = BridgeEngine(config=self.config)
            await self.engine.initialize()
            await self.engine.start_background_tasks()
            app.state.engine = self.engine
            logger.info("Bridge engine started")
            yield
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            raise
        finally:
            logger.info("Shutting down...")
            if self.engine:
                await self.engine.stop()
            if self.redis:
                await self.redis.close()
            await db.close()
            logger.info("Shutdown complete")

    def create_app(self) -> FastAPI:
        app = FastAPI(
            title="Industrial Data Bridge",
            description="AI-powered industrial device data collection & protocol conversion",
            version="1.0.0",
            docs_url="/docs", redoc_url="/redoc",
            openapi_url="/api/v1/openapi.json",
            lifespan=self.lifespan,
        )
        app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                           allow_methods=["*"], allow_headers=["*"])
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        app.include_router(api_router, prefix="/api/v1")

        @app.middleware("http")
        async def log_security(request: Request, call_next):
            start = asyncio.get_event_loop().time()
            response = await call_next(request)
            elapsed = asyncio.get_event_loop().time() - start
            logger.info(f"{request.method} {request.url.path} status={response.status_code} time={elapsed:.3f}s")
            response.headers["X-Process-Time"] = str(elapsed)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            return response

        @app.exception_handler(Exception)
        async def global_handler(request: Request, exc: Exception):
            logger.error(f"Unhandled: {exc}")
            return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": str(exc)}})

        if self.config.get("server", {}).get("enable_metrics", True):
            Instrumentator().instrument(app).expose(app)

        self.app = app
        return app

    async def run_server(self, host="0.0.0.0", port=8000):
        if not self.app:
            self.create_app()
        cfg = uvicorn.Config(app=self.app, host=host, port=port, log_config=None,
                             access_log=False, loop="asyncio", http="h11", ws="none",
                             timeout_keep_alive=5, limit_concurrency=100, backlog=2048)
        self.server = uvicorn.Server(cfg)
        logger.info(f"Server on {host}:{port}")
        await self.server.serve()

    async def shutdown(self):
        if self.server:
            self.server.should_exit = True
        await asyncio.sleep(2)
        sys.exit(0)


def create_app(config_path=None) -> FastAPI:
    return IndustrialDataBridge(config_path).create_app()


async def main():
    import argparse
    p = argparse.ArgumentParser(description="Industrial Data Bridge")
    p.add_argument("--mode", choices=["web", "engine", "edge", "test"], default="web")
    p.add_argument("--config", default="config/config.yaml")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()
    idb = IndustrialDataBridge(args.config)
    if args.mode == "web":
        await idb.run_server(args.host, args.port)
    elif args.mode == "edge":
        from src.edge.agent import EdgeAgent
        await EdgeAgent(config_path=args.config).run()
    elif args.mode == "test":
        import pytest
        sys.exit(pytest.main(["tests/"]))

if __name__ == "__main__":
    asyncio.run(main())