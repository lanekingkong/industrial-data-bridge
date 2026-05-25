"""
Tests for the Data Normalizer module.
"""

import unittest
from datetime import datetime, timezone

from src.utils.data_normalizer import DataNormalizer


class TestDataNormalizer(unittest.TestCase):
    """Test suite for DataNormalizer."""

    def setUp(self):
        """Set up test fixtures."""
        self.normalizer = DataNormalizer(default_unit="celsius")

    def test_normalize_single_value_celsius(self):
        """Test normalizing a single temperature value."""
        result = self.normalizer.normalize_point(
            point_name="temp_in",
            raw_value=25,
            unit="celsius",
            data_type="float",
        )
        assert result["quality"] == "good"
        assert result["value"] == 25.0
        assert result["unit"] == "celsius"

    def test_normalize_single_value_fahrenheit_to_celsius(self):
        """Test Fahrenheit to Celsius conversion."""
        result = self.normalizer.normalize_point(
            point_name="temp_in",
            raw_value=77,
            unit="fahrenheit",
            data_type="float",
            target_unit="celsius",
        )
        assert result["quality"] == "good"
        assert abs(result["value"] - 25.0) < 0.1
        assert result["unit"] == "celsius"

    def test_normalize_single_value_celsius_to_kelvin(self):
        """Test Celsius to Kelvin conversion."""
        result = self.normalizer.normalize_point(
            point_name="temp_in",
            raw_value=25,
            unit="celsius",
            data_type="float",
            target_unit="kelvin",
        )
        assert result["quality"] == "good"
        assert abs(result["value"] - 298.15) < 0.01
        assert result["unit"] == "kelvin"

    def test_normalize_single_value_pressure_kpa_to_bar(self):
        """Test kPa to bar conversion."""
        result = self.normalizer.normalize_point(
            point_name="pressure",
            raw_value=500,
            unit="kpa",
            data_type="float",
            target_unit="bar",
        )
        assert result["quality"] == "good"
        assert abs(result["value"] - 5.0) < 0.01
        assert result["unit"] == "bar"

    def test_normalize_value_out_of_range(self):
        """Test value exceeding max range."""
        result = self.normalizer.normalize_point(
            point_name="temp_in",
            raw_value=150,
            unit="celsius",
            data_type="float",
            min_val=0,
            max_val=100,
        )
        assert result["quality"] == "bad"
        assert "exceeds maximum" in result["quality_message"].lower()

    def test_normalize_value_below_range(self):
        """Test value below min range."""
        result = self.normalizer.normalize_point(
            point_name="temp_in",
            raw_value=-10,
            unit="celsius",
            data_type="float",
            min_val=0,
            max_val=100,
        )
        assert result["quality"] == "bad"
        assert "below minimum" in result["quality_message"].lower()

    def test_normalize_value_within_range(self):
        """Test value within range."""
        result = self.normalizer.normalize_point(
            point_name="temp_in",
            raw_value=50,
            unit="celsius",
            data_type="float",
            min_val=0,
            max_val=100,
        )
        assert result["quality"] == "good"

    def test_normalize_none_value(self):
        """Test None value handling."""
        result = self.normalizer.normalize_point(
            point_name="temp_in",
            raw_value=None,
            unit="celsius",
            data_type="float",
        )
        assert result["quality"] == "bad"
        assert result["value"] is None

    def test_normalize_empty_string_value(self):
        """Test empty string handling."""
        result = self.normalizer.normalize_point(
            point_name="status",
            raw_value="",
            unit="",
            data_type="string",
        )
        assert result["quality"] == "uncertain"

    def test_convert_unit_temperature(self):
        """Test temperature conversion function."""
        assert abs(DataNormalizer.convert_unit(0, "celsius", "fahrenheit") - 32) < 0.01
        assert abs(DataNormalizer.convert_unit(32, "fahrenheit", "celsius") - 0) < 0.01
        assert abs(DataNormalizer.convert_unit(0, "celsius", "kelvin") - 273.15) < 0.01

    def test_convert_unit_pressure(self):
        """Test pressure conversion function."""
        assert abs(DataNormalizer.convert_unit(100, "kpa", "bar") - 1.0) < 0.01
        assert abs(DataNormalizer.convert_unit(1, "bar", "kpa") - 100) < 0.01
        assert abs(DataNormalizer.convert_unit(100, "kpa", "mpa") - 0.1) < 0.01

    def test_convert_unit_same_unit(self):
        """Test same unit conversion returns same value."""
        assert DataNormalizer.convert_unit(50, "celsius", "celsius") == 50
        assert DataNormalizer.convert_unit(100, "kpa", "kpa") == 100

    def test_normalize_batch(self):
        """Test batch normalization."""
        points = [
            {"name": "temp1", "value": 25, "unit": "celsius"},
            {"name": "temp2", "value": 77, "unit": "fahrenheit"},
            {"name": "pressure1", "value": 500, "unit": "kpa"},
        ]
        config = {
            "data_type": "float",
            "target_unit": "celsius",
        }
        
        results = self.normalizer.normalize_points(points, config)
        
        assert len(results) == 3
        assert results[0]["quality"] == "good"
        assert abs(results[0]["value"] - 25.0) < 0.1
        
        # temp2: 77°F → °C
        assert abs(results[1]["value"] - 25.0) < 0.1
        
        # pressure1: 500 kPa (not converted since target is celsius)
        assert results[2]["value"] == 500

    def test_set_quality_rules(self):
        """Test custom quality rules."""
        normalizer = DataNormalizer(default_unit="celsius")
        normalizer.set_quality_rules({
            "temp_critical": [("temp_in", "gt", 90)],
        })
        
        result = normalizer.normalize_point(
            point_name="temp_in",
            raw_value=95,
            unit="celsius",
            data_type="float",
        )
        assert result["quality"] == "bad"


if __name__ == "__main__":
    unittest.main()