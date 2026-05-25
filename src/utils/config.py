"""
Industrial Data Bridge - Configuration Utilities
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


DEFAULT_CONFIG = {
    "server": {"host": "0.0.0.0", "port": 8000, "enable_metrics": True},
    "database": {
        "host": "localhost", "port": 5432, "name": "industrial_bridge",
        "user": "idb_user", "password": "changeme", "pool_min": 5, "pool_max": 20
    },
    "redis": {"host": "localhost", "port": 6379, "db": 0, "password": None},
    "engine": {
        "health_check_interval": 60, "stats_report_interval": 300,
        "auto_collection": {"enabled": False, "interval": 60}
    },
    "ai": {"enabled": True, "model_path": "models/", "anomaly_threshold": 0.85,
           "prediction_horizon": 3600, "batch_size": 64},
    "protocols": {
        "modbus": {"enabled": True, "default_timeout": 5},
        "opcua": {"enabled": True, "default_timeout": 10},
        "mqtt": {"enabled": True, "default_qos": 1},
        "http": {"enabled": True, "default_timeout": 30},
    },
    "logging": {"level": "INFO", "format": "json", "file": None},
    "edge": {"enabled": False, "sync_interval": 30, "batch_size": 100,
             "local_storage": True, "device_ids": []},
}

_config_cache: Optional[Dict[str, Any]] = None


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from YAML file, merge with defaults.
    
    Args:
        config_path: Path to YAML config file, or None to use defaults
        
    Returns:
        Merged configuration dictionary
    """
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config = DEFAULT_CONFIG.copy()

    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f)
        if user_config:
            config = _deep_merge(config, user_config)

    # Environment variable overrides
    _apply_env_overrides(config)

    _config_cache = config
    return config


def get_config() -> Dict[str, Any]:
    """Get cached configuration, loading from default path if needed."""
    global _config_cache
    if _config_cache is None:
        paths = ["config/config.yaml", "config.yaml", "../config/config.yaml"]
        for p in paths:
            if os.path.exists(p):
                return load_config(p)
        return load_config()
    return _config_cache


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides(config: Dict):
    """Apply environment variable overrides."""
    env_map = {
        "DB_HOST": ("database", "host"),
        "DB_PORT": ("database", "port"),
        "DB_NAME": ("database", "name"),
        "DB_USER": ("database", "user"),
        "DB_PASSWORD": ("database", "password"),
        "REDIS_HOST": ("redis", "host"),
        "REDIS_PORT": ("redis", "port"),
        "REDIS_PASSWORD": ("redis", "password"),
        "SERVER_PORT": ("server", "port"),
        "LOG_LEVEL": ("logging", "level"),
    }
    for env_var, (section, key) in env_map.items():
        val = os.getenv(env_var)
        if val is not None:
            if key == "port":
                config.setdefault(section, {})[key] = int(val)
            else:
                config.setdefault(section, {})[key] = val


def reset_config():
    """Reset cached config (useful for testing)."""
    global _config_cache
    _config_cache = None