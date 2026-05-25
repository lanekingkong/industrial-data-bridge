"""
Industrial Data Bridge - Core Package

AI-powered industrial device data collection and protocol conversion solution.
"""

__version__ = "1.0.0"
__author__ = "Industrial Data Bridge Team"
__license__ = "MIT"

from src.core.config import BridgeConfig
from src.core.engine import BridgeEngine

__all__ = ["BridgeConfig", "BridgeEngine"]