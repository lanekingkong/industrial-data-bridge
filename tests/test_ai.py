"""
Tests for the AI anomaly detection module.
"""

import unittest
import numpy as np
import os
import tempfile
from unittest.mock import Mock, patch

from src.ai.anomaly_predictive import AnomalyDetector, PredictiveMaintenance


class TestAnomalyDetector(unittest.TestCase):
    """Test suite for AnomalyDetector."""

    def setUp(self):
        """Set up test fixtures."""
        self.detector = AnomalyDetector(method="isolation_forest", contamination=0.1)

    def test_init_isolation_forest(self):
        """Test initialization with Isolation Forest."""
        detector = AnomalyDetector(method="isolation_forest")
        assert detector.method == "isolation_forest"
        assert detector._model is not None
        assert detector._trained is False

    def test_init_autoencoder(self):
        """Test initialization with Autoencoder."""
        detector = AnomalyDetector(method="autoencoder", contamination=0.05)
        assert detector.method == "autoencoder"
        assert detector._model is not None
        assert detector._trained is False

    def test_init_invalid_method(self):
        """Test initialization with invalid method."""
        with self.assertRaises(ValueError):
            AnomalyDetector(method="invalid_method")

    def test_preprocess_data(self):
        """Test data preprocessing."""
        data = [
            {"temperature": 30, "pressure": 5, "flow": 10},
            {"temperature": 35, "pressure": 6, "flow": 12},
            {"temperature": 32, "pressure": 5.5, "flow": 11},
        ]
        X = self.detector._preprocess(data)
        assert X.shape == (3, 3)
        assert np.allclose(X.sum(axis=0), [97, 16.5, 33])

    def test_train_isolation_forest(self):
        """Test training with Isolation Forest."""
        data = [
            {"temperature": 30, "pressure": 5, "flow": 10},
            {"temperature": 35, "pressure": 6, "flow": 12},
            {"temperature": 32, "pressure": 5.5, "flow": 11},
            {"temperature": 33, "pressure": 5.2, "flow": 10.5},
            {"temperature": 31, "pressure": 5.8, "flow": 11.5},
        ] * 20  # Need more samples for training
        
        result = self.detector.train(data)
        assert result["success"] is True
        assert "samples" in result
        assert self.detector._trained is True

    def test_predict_without_training(self):
        """Test prediction without training raises error."""
        data = [{"temperature": 120, "pressure": 20, "flow": 50}]
        
        with self.assertRaises(ValueError):
            self.detector.predict(data)

    def test_predict_with_trained_model(self):
        """Test prediction with trained model."""
        # Train first
        data = [
            {"temperature": 30, "pressure": 5, "flow": 10},
            {"temperature": 35, "pressure": 6, "flow": 12},
            {"temperature": 32, "pressure": 5.5, "flow": 11},
        ] * 20
        self.detector.train(data)
        
        # Predict normal data
        normal = [{"temperature": 33, "pressure": 5.3, "flow": 11.2}]
        result = self.detector.predict(normal)
        assert "predictions" in result
        assert "anomalies_detected" in result

    def test_save_load_model(self):
        """Test model save and load."""
        # Train
        data = [
            {"temperature": 30, "pressure": 5, "flow": 10},
            {"temperature": 35, "pressure": 6, "flow": 12},
            {"temperature": 32, "pressure": 5.5, "flow": 11},
        ] * 20
        self.detector.train(data)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "model.pkl")
            
            # Save
            result = self.detector.save_model(path)
            assert result["success"] is True
            assert os.path.exists(path)
            
            # Load into new detector
            new_detector = AnomalyDetector(method="isolation_forest")
            load_result = new_detector.load_model(path)
            assert load_result["success"] is True
            assert new_detector._trained is True

    def test_explain_anomaly(self):
        """Test anomaly explanation generation."""
        data = [{"temperature": 30, "pressure": 5, "flow": 10}] * 20
        self.detector.train(data)
        
        feature_values = {"temperature": 120, "pressure": 20, "flow": 50}
        explanation = self.detector.explain_anomaly(
            score=0.95,
            feature_values=feature_values,
        )
        assert "score" in explanation
        assert "feature_contributions" in explanation
        assert explanation["severity"] == "critical"

    def test_autoencoder_training(self):
        """Test Autoencoder training."""
        detector = AnomalyDetector(method="autoencoder", contamination=0.1)
        
        data = [
            {"temperature": 30, "pressure": 5, "flow": 10},
            {"temperature": 35, "pressure": 6, "flow": 12},
            {"temperature": 32, "pressure": 5.5, "flow": 11},
        ] * 30
        
        # Training may take a moment
        result = detector.train(data, epochs=5, batch_size=32)
        assert result["success"] is True
        assert detector._trained is True


class TestPredictiveMaintenance(unittest.TestCase):
    """Test suite for PredictiveMaintenance."""

    def setUp(self):
        """Set up test fixtures."""
        self.predictor = PredictiveMaintenance()

    def test_init(self):
        """Test initialization."""
        assert self.predictor._rul_model is not None
        assert self.predictor._failure_classifier is not None
        assert self.predictor._trained is False

    def test_preprocess_features(self):
        """Test feature preprocessing."""
        data = [
            {"temperature": 30, "vibration": 0.5, "hours_run": 1000},
            {"temperature": 35, "vibration": 0.6, "hours_run": 1500},
            {"temperature": 40, "vibration": 0.7, "hours_run": 2000},
        ]
        X = self.predictor._preprocess_features(data)
        assert X.shape == (3, 3)

    def test_train_rul(self):
        """Test RUL model training."""
        train_data = [
            {"temperature": 30 + i, "vibration": 0.5 + i * 0.01, "hours_run": 1000 + i * 100}
            for i in range(50)
        ]
        train_labels = [50 - i for i in range(50)]  # RUL decreasing
        
        result = self.predictor.train(
            features=train_data,
            labels={"rul": train_labels},
        )
        assert result["success"] is True
        assert self.predictor._trained is True

    def test_predict_without_training(self):
        """Test prediction without training raises error."""
        data = [{"temperature": 35, "vibration": 0.6, "hours_run": 1500}]
        
        with self.assertRaises(RuntimeError):
            self.predictor.predict(data)

    def test_predict_rul(self):
        """Test RUL prediction."""
        # Train first
        train_data = [
            {"temperature": 30 + i * 0.5, "vibration": 0.5 + i * 0.01, "hours_run": 1000 + i * 100}
            for i in range(50)
        ]
        train_labels = [50 - i for i in range(50)]
        self.predictor.train(features=train_data, labels={"rul": train_labels})
        
        # Predict
        sample = [{"temperature": 55, "vibration": 0.95, "hours_run": 5000}]
        result = self.predictor.predict(sample)
        
        assert "rul_estimate" in result
        assert "failure_probability" in result
        assert "risk_level" in result
        assert "recommendation" in result

    def test_risk_level_categorization(self):
        """Test risk level categorization."""
        assert self.predictor._categorize_risk(0.05) == "low"
        assert self.predictor._categorize_risk(0.3) == "medium"
        assert self.predictor._categorize_risk(0.6) == "high"
        assert self.predictor._categorize_risk(0.9) == "critical"

    def test_assess_failure_risk(self):
        """Test failure risk assessment."""
        # Train first
        train_data = [
            {"temperature": 30 + i * 0.5, "vibration": 0.5 + i * 0.01, "hours_run": 1000 + i * 100}
            for i in range(50)
        ]
        train_labels = [50 - i for i in range(50)]
        self.predictor.train(features=train_data, labels={"rul": train_labels})
        
        features = {"temperature": 55, "vibration": 0.95, "hours_run": 5000}
        assessment = self.predictor.assess_failure_risk(features)
        
        assert "failure_probability" in assessment
        assert "risk_level" in assessment
        assert "estimated_rul_hours" in assessment
        assert "recommended_action" in assessment

    def test_save_load_model(self):
        """Test model save and load."""
        train_data = [
            {"temperature": 30 + i, "vibration": 0.5 + i * 0.01, "hours_run": 1000 + i * 100}
            for i in range(50)
        ]
        train_labels = [50 - i for i in range(50)]
        self.predictor.train(features=train_data, labels={"rul": train_labels})
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "pm_model")
            
            # Save
            result = self.predictor.save_model(path)
            assert result["success"] is True
            
            # Load into new predictor
            new_predictor = PredictiveMaintenance()
            load_result = new_predictor.load_model(path)
            assert load_result["success"] is True


if __name__ == "__main__":
    unittest.main()