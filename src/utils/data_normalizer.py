"""
Data Normalizer - Converts raw protocol data to standardized format.

Handles:
- Unit conversions
- Data type normalization
- Quality flagging
- Range validation
- Missing value handling
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from loguru import logger


class DataNormalizer:
    """
    Normalizes industrial data from various protocols to a common format.

    Features:
        - Unit conversion (Celsius ↔ Fahrenheit, kPa ↔ psi, etc.)
        - Data type standardization
        - Range validation and clipping
        - Quality assessment (good/bad/uncertain)
        - Timestamp normalization (UTC)
    """

    UNIT_CONVERSIONS = {
        # Temperature
        ("celsius", "kelvin"): lambda x: x + 273.15,
        ("celsius", "fahrenheit"): lambda x: x * 9/5 + 32,
        ("fahrenheit", "celsius"): lambda x: (x - 32) * 5/9,
        ("fahrenheit", "kelvin"): lambda x: (x - 32) * 5/9 + 273.15,
        ("kelvin", "celsius"): lambda x: x - 273.15,
        ("kelvin", "fahrenheit"): lambda x: (x - 273.15) * 9/5 + 32,
        # Pressure
        ("kpa", "psi"): lambda x: x * 0.145038,
        ("psi", "kpa"): lambda x: x * 6.89476,
        ("bar", "kpa"): lambda x: x * 100,
        ("kpa", "bar"): lambda x: x / 100,
        ("mpa", "kpa"): lambda x: x * 1000,
        ("kpa", "mpa"): lambda x: x / 1000,
        # Flow
        ("lpm", "m3h"): lambda x: x * 0.06,
        ("m3h", "lpm"): lambda x: x / 0.06,
        # Energy
        ("kwh", "mj"): lambda x: x * 3.6,
        ("mj", "kwh"): lambda x: x / 3.6,
        # Length
        ("mm", "inch"): lambda x: x * 0.0393701,
        ("inch", "mm"): lambda x: x * 25.4,
        ("m", "ft"): lambda x: x * 3.28084,
        ("ft", "m"): lambda x: x / 3.28084,
    }

    DATA_TYPE_MAP = {
        "bool": bool,
        "int8": np.int8,
        "int16": np.int16,
        "int32": np.int32,
        "int64": np.int64,
        "uint8": np.uint8,
        "uint16": np.uint16,
        "uint32": np.uint32,
        "uint64": np.uint64,
        "float32": np.float32,
        "float64": np.float64,
        "string": str,
        "datetime": datetime,
    }

    def __init__(self, default_unit_system: str = "si") -> None:
        self.default_unit_system = default_unit_system.lower()
        self._quality_rules: Dict[str, Dict[str, Any]] = {}
        self._custom_conversions: Dict[tuple, callable] = {}

    def normalize(
        self,
        raw_value: Any,
        point_config: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Normalize a single data point.

        Args:
            raw_value: Raw value from protocol adapter.
            point_config: Point configuration dict.
            timestamp: Optional timestamp (defaults to now).

        Returns:
            Dict with keys: value, unit, quality, timestamp.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Extract config
        point_name = point_config.get("name", "unknown")
        expected_type = point_config.get("data_type", "float64")
        expected_unit = point_config.get("unit")
        min_val = point_config.get("min")
        max_val = point_config.get("max")
        deadband = point_config.get("deadband", 0.0)

        # Step 1: Type conversion
        try:
            typed_value = self._convert_type(raw_value, expected_type)
        except (ValueError, TypeError) as exc:
            logger.warning(f"Type conversion failed for {point_name}: {exc}")
            typed_value = raw_value
            quality = "bad"

        # Step 2: Unit conversion (if needed)
        if expected_unit:
            try:
                typed_value, final_unit = self._convert_units(
                    typed_value, expected_unit
                )
            except ValueError as exc:
                logger.warning(f"Unit conversion failed for {point_name}: {exc}")
                final_unit = expected_unit
                quality = "uncertain"
        else:
            final_unit = None

        # Step 3: Range validation
        quality = "good"
        if min_val is not None and typed_value < min_val:
            if abs(typed_value - min_val) > deadband:
                logger.debug(f"{point_name} below min: {typed_value} < {min_val}")
                quality = "bad"
            else:
                quality = "uncertain"
        if max_val is not None and typed_value > max_val:
            if abs(typed_value - max_val) > deadband:
                logger.debug(f"{point_name} above max: {typed_value} > {max_val}")
                quality = "bad"
            else:
                quality = "uncertain"

        # Step 4: Special value handling
        if typed_value is None or (isinstance(typed_value, float) and np.isnan(typed_value)):
            quality = "bad"
        elif isinstance(typed_value, str) and typed_value.strip() == "":
            quality = "bad"

        # Step 5: Apply quality rules
        quality = self._apply_quality_rules(point_name, typed_value, quality)

        return {
            "value": typed_value,
            "unit": final_unit,
            "quality": quality,
            "timestamp": timestamp.isoformat(),
            "raw_value": raw_value,
            "point_name": point_name,
        }

    def normalize_batch(
        self,
        raw_values: List[Any],
        point_configs: List[Dict[str, Any]],
        timestamps: Optional[List[datetime]] = None,
    ) -> List[Dict[str, Any]]:
        """Normalize a batch of data points."""
        if timestamps is None:
            timestamps = [datetime.now(timezone.utc)] * len(raw_values)

        results = []
        for i, (raw_val, config) in enumerate(zip(raw_values, point_configs)):
            ts = timestamps[i] if i < len(timestamps) else timestamps[-1]
            try:
                result = self.normalize(raw_val, config, ts)
                results.append(result)
            except Exception as exc:
                logger.error(f"Batch normalization failed at index {i}: {exc}")
                results.append({
                    "value": None,
                    "unit": config.get("unit"),
                    "quality": "bad",
                    "timestamp": ts.isoformat(),
                    "raw_value": raw_val,
                    "point_name": config.get("name", f"point_{i}"),
                })
        return results

    def add_quality_rule(
        self,
        point_pattern: str,
        condition: Dict[str, Any],
        quality: str,
    ) -> None:
        """
        Add a custom quality assessment rule.

        Args:
            point_pattern: Regex pattern to match point names.
            condition: Dict with keys like 'min', 'max', 'rate_of_change'.
            quality: 'good', 'uncertain', or 'bad'.
        """
        self._quality_rules[point_pattern] = {
            "pattern": re.compile(point_pattern),
            "condition": condition,
            "quality": quality,
        }
        logger.debug(f"Added quality rule for pattern: {point_pattern}")

    def add_custom_conversion(
        self,
        from_unit: str,
        to_unit: str,
        converter: callable,
    ) -> None:
        """Add custom unit conversion."""
        key = (from_unit.lower(), to_unit.lower())
        self._custom_conversions[key] = converter
        logger.debug(f"Added custom conversion: {from_unit} → {to_unit}")

    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target data type."""
        if value is None:
            return None

        type_func = self.DATA_TYPE_MAP.get(target_type.lower())
        if type_func is None:
            logger.warning(f"Unknown data type: {target_type}, using float64")
            type_func = np.float64

        try:
            if type_func == bool:
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on", "t")
                return bool(value)
            elif type_func == datetime:
                if isinstance(value, (int, float)):
                    return datetime.fromtimestamp(value, timezone.utc)
                elif isinstance(value, str):
                    # Try ISO format
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                else:
                    raise ValueError(f"Cannot convert {type(value)} to datetime")
            else:
                return type_func(value)
        except Exception as exc:
            raise ValueError(f"Type conversion failed: {value} → {target_type}: {exc}")

    def _convert_units(
        self,
        value: Union[int, float],
        target_unit: str,
    ) -> tuple:
        """
        Convert value to target unit system.

        Returns:
            (converted_value, final_unit)
        """
        if not isinstance(value, (int, float)):
            return value, target_unit

        # If no source unit specified, assume it's already in target
        # (or we can't convert)
        if "source_unit" not in locals():
            return value, target_unit

        # Check for direct conversion
        key = (source_unit.lower(), target_unit.lower())
        if key in self.UNIT_CONVERSIONS:
            return self.UNIT_CONVERSIONS[key](value), target_unit
        elif key in self._custom_conversions:
            return self._custom_conversions[key](value), target_unit

        # Try SI base units conversion
        si_converted = self._convert_to_si(value, source_unit)
        if si_converted is not None:
            from_si = self._convert_from_si(si_converted, target_unit)
            if from_si is not None:
                return from_si, target_unit

        logger.warning(
            f"No conversion found: {source_unit} → {target_unit}. "
            f"Using source unit."
        )
        return value, source_unit

    def _convert_to_si(self, value: float, unit: str) -> Optional[float]:
        """Convert to SI base units if possible."""
        unit = unit.lower()
        conversions = {
            "celsius": lambda x: x + 273.15,  # to Kelvin
            "fahrenheit": lambda x: (x - 32) * 5/9 + 273.15,
            "psi": lambda x: x * 6894.76,  # to Pascal
            "bar": lambda x: x * 100000,
            "inch": lambda x: x * 0.0254,  # to meter
            "ft": lambda x: x * 0.3048,
            "lpm": lambda x: x / 60000,  # to m³/s
        }
        if unit in conversions:
            return conversions[unit](value)
        return None

    def _convert_from_si(self, value: float, target_unit: str) -> Optional[float]:
        """Convert from SI base units to target unit."""
        target_unit = target_unit.lower()
        conversions = {
            "celsius": lambda x: x - 273.15,  # from Kelvin
            "fahrenheit": lambda x: (x - 273.15) * 9/5 + 32,
            "psi": lambda x: x / 6894.76,  # from Pascal
            "bar": lambda x: x / 100000,
            "inch": lambda x: x / 0.0254,  # from meter
            "ft": lambda x: x / 0.3048,
            "lpm": lambda x: x * 60000,  # from m³/s
        }
        if target_unit in conversions:
            return conversions[target_unit](value)
        return None

    def _apply_quality_rules(
        self,
        point_name: str,
        value: Any,
        current_quality: str,
    ) -> str:
        """Apply custom quality rules to a data point."""
        if current_quality == "bad":
            return current_quality  # Don't override bad quality

        for rule in self._quality_rules.values():
            if rule["pattern"].match(point_name):
                condition = rule["condition"]
                if self._check_condition(value, condition):
                    return rule["quality"]
        return current_quality

    def _check_condition(self, value: Any, condition: Dict[str, Any]) -> bool:
        """Check if value meets condition."""
        if "min" in condition and value < condition["min"]:
            return True
        if "max" in condition and value > condition["max"]:
            return True
        if "equals" in condition and value != condition["equals"]:
            return True
        if "not_equals" in condition and value == condition["not_equals"]:
            return True
        if "in" in condition and value not in condition["in"]:
            return True
        if "not_in" in condition and value in condition["not_in"]:
            return True
        return False