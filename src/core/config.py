"""
Core configuration module using Pydantic Settings.

Loads environment variables and provides typed configuration
for all components of the Industrial Data Bridge.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    host: str = "localhost"
    port: int = 5432
    db: str = "industrial_bridge"
    user: str = "bridge_user"
    password: str = "changeme"

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_", env_file=".env", extra="ignore"
    )

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def sync_url(self) -> str:
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class InfluxDBSettings(BaseSettings):
    """InfluxDB time-series database configuration."""

    url: str = "http://localhost:8086"
    token: str = "changeme"
    org: str = "industrial-bridge"
    bucket: str = "device_telemetry"

    model_config = SettingsConfigDict(
        env_prefix="INFLUXDB_", env_file=".env", extra="ignore"
    )


class RedisSettings(BaseSettings):
    """Redis cache configuration."""

    url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_prefix="REDIS_", env_file=".env", extra="ignore"
    )


class ModbusSettings(BaseSettings):
    """Modbus gateway configuration."""

    default_port: int = 5020
    timeout: float = 3.0
    retries: int = 3

    model_config = SettingsConfigDict(
        env_prefix="MODBUS_", env_file=".env", extra="ignore"
    )


class OpcUASettings(BaseSettings):
    """OPC-UA gateway configuration."""

    endpoint: str = "opc.tcp://localhost:4840"
    timeout: float = 10.0
    security_policy: str = "None"

    model_config = SettingsConfigDict(
        env_prefix="OPCUA_", env_file=".env", extra="ignore"
    )


class MQTTSettings(BaseSettings):
    """MQTT broker configuration."""

    broker_url: str = "mqtt://localhost:1883"
    client_id: str = "industrial-bridge-gateway"
    keepalive: int = 60
    qos: int = 1

    model_config = SettingsConfigDict(
        env_prefix="MQTT_", env_file=".env", extra="ignore"
    )


class AISettings(BaseSettings):
    """AI model configuration."""

    model_path: str = "./models"
    anomaly_sensitivity: float = 0.95
    prediction_window: str = "24h"
    retrain_interval: str = "7d"

    model_config = SettingsConfigDict(
        env_prefix="AI_", env_file=".env", extra="ignore"
    )


class EdgeSettings(BaseSettings):
    """Edge computing configuration."""

    enabled: bool = False
    data_path: str = "/data/edge"
    sync_interval: str = "60s"

    model_config = SettingsConfigDict(
        env_prefix="EDGE_", env_file=".env", extra="ignore"
    )


class ServerSettings(BaseSettings):
    """Application server configuration."""

    name: str = "IndustrialDataBridge"
    version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", extra="ignore"
    )


class SecuritySettings(BaseSettings):
    """Security and authentication configuration."""

    jwt_secret_key: str = "change-this-to-a-random-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    encryption_key: str = "change-this-32-byte-key-xxxxxx"

    model_config = SettingsConfigDict(
        env_prefix="JWT_", env_file=".env", extra="ignore"
    )


class BridgeConfig:
    """
    Aggregated configuration for the Industrial Data Bridge.

    Usage:
        config = BridgeConfig()
        db_url = config.db.url
    """

    def __init__(self, env_file: Optional[str] = None) -> None:
        env_file = env_file or os.getenv("BRIDGE_ENV_FILE", ".env")
        if not Path(env_file).exists():
            env_file = ".env"

        self.server = ServerSettings(_env_file=env_file)
        self.db = DatabaseSettings(_env_file=env_file)
        self.influxdb = InfluxDBSettings(_env_file=env_file)
        self.redis = RedisSettings(_env_file=env_file)
        self.modbus = ModbusSettings(_env_file=env_file)
        self.opcua = OpcUASettings(_env_file=env_file)
        self.mqtt = MQTTSettings(_env_file=env_file)
        self.ai = AISettings(_env_file=env_file)
        self.edge = EdgeSettings(_env_file=env_file)
        self.security = SecuritySettings(_env_file=env_file)

    @classmethod
    def from_dict(cls, data: dict) -> BridgeConfig:
        """Create config from dictionary (useful for testing)."""
        config = cls.__new__(cls)
        for section_name, section_data in data.items():
            section_cls_map = {
                "server": ServerSettings,
                "db": DatabaseSettings,
                "influxdb": InfluxDBSettings,
                "redis": RedisSettings,
                "modbus": ModbusSettings,
                "opcua": OpcUASettings,
                "mqtt": MQTTSettings,
                "ai": AISettings,
                "edge": EdgeSettings,
                "security": SecuritySettings,
            }
            if section_name in section_cls_map:
                setattr(config, section_name, section_cls_map[section_name](**section_data))
        return config