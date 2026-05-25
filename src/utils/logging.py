"""
Industrial Data Bridge - Logging Utilities
"""

import logging
import sys
import json
from datetime import datetime
from typing import Optional


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Add extra fields
        for key in ("device_id", "protocol", "request_id"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable colored log formatter."""

    COLORS = {
        logging.DEBUG: "\033[36m",   # Cyan
        logging.INFO: "\033[32m",    # Green
        logging.WARNING: "\033[33m", # Yellow
        logging.ERROR: "\033[31m",   # Red
        logging.CRITICAL: "\033[35m",# Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = f"{color}{record.levelname:<8}{self.RESET}"
        msg = f"{timestamp} | {level} | {record.name}:{record.funcName}:{record.lineno} | {record.getMessage()}"
        if record.exc_info and record.exc_info[0]:
            msg += "\n" + self.formatException(record.exc_info)
        return msg


def setup_logging(
    level: str = "INFO",
    format_type: str = "text",
    log_file: Optional[str] = None,
    module_levels: Optional[dict] = None,
) -> logging.Logger:
    """Configure logging for the application.
    
    Args:
        level: Root log level
        format_type: 'json' for structured, 'text' for human-readable
        log_file: Optional file path for log output
        module_levels: Optional dict of module_name: level for per-module levels
        
    Returns:
        Root logger
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers
    root.handlers.clear()
    
    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    if format_type == "json":
        console.setFormatter(JsonFormatter())
    else:
        console.setFormatter(TextFormatter())
    
    root.addHandler(console)
    
    # File handler
    if log_file:
        import os
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JsonFormatter())
        root.addHandler(file_handler)
    
    # Module-level overrides
    if module_levels:
        for mod, lvl in module_levels.items():
            logging.getLogger(mod).setLevel(getattr(logging, lvl.upper(), logging.INFO))
    
    # Reduce noise from libraries
    for lib in ("asyncio", "urllib3", "aiohttp", "aiomqtt", "pymodbus", "asyncua"):
        logging.getLogger(lib).setLevel(logging.WARNING)
    
    return root


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)