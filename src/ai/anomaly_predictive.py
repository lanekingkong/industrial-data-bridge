"""
AI-powered anomaly detection and predictive maintenance.

Uses machine learning to detect anomalies in industrial data
and predict equipment failures.
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

from ..core.config import BridgeConfig


class AnomalyDetector:
    """
    Detects anomalies in time-series industrial data.

    Uses isolation forest, autoencoders, or statistical methods
    to identify abnormal patterns in device telemetry.
    """

    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self.model_path = Path(config.ai.model_path) / "anomaly"
        self.model_path.mkdir(parents=True, exist_ok=True)
        self.sensitivity = config.ai.anomaly_sensitivity
        self._model = None
        self._scaler = None
        self._features = None

    def load_model(self, model_name: str = "isolation_forest") -> None:
        """Load a pre-trained anomaly detection model."""
        model_file = self.model_path / f"{model_name}.pkl"
        if model_file.exists():
            with open(model_file, "rb") as f:
                self._model = pickle.load(f)
            logger.info(f"Loaded anomaly model: {model_name}")
        else:
            logger.warning(f"Model not found: {model_file}, will train on first data")

    def train(
        self,
        data: pd.DataFrame,
        features: Optional[List[str]] = None,
        method: str = "isolation_forest",
    ) -> None:
        """
        Train anomaly detection model on historical data.

        Args:
            data: DataFrame with timestamp index and numeric columns.
            features: List of column names to use for training.
            method: "isolation_forest", "autoencoder", or "statistical".
        """
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler

        if features is None:
            features = [col for col in data.columns if data[col].dtype in (np.int64, np.float64)]
        self._features = features

        # Prepare training data
        X = data[features].fillna(method="ffill").fillna(0).values

        # Scale features
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        # Train model
        if method == "isolation_forest":
            contamination = 1.0 - self.sensitivity
            self._model = IsolationForest(
                n_estimators=100,
                contamination=contamination,
                random_state=42,
                n_jobs=-1,
            )
        elif method == "autoencoder":
            from tensorflow import keras
            from tensorflow.keras import layers

            input_dim = X_scaled.shape[1]
            encoding_dim = max(3, input_dim // 4)

            # Build autoencoder
            input_layer = layers.Input(shape=(input_dim,))
            encoder = layers.Dense(encoding_dim, activation="relu")(input_layer)
            decoder = layers.Dense(input_dim, activation="sigmoid")(encoder)
            autoencoder = keras.Model(inputs=input_layer, outputs=decoder)
            autoencoder.compile(optimizer="adam", loss="mse")

            # Train
            autoencoder.fit(
                X_scaled, X_scaled,
                epochs=50,
                batch_size=32,
                shuffle=True,
                validation_split=0.1,
                verbose=0,
            )
            self._model = autoencoder
        else:
            raise ValueError(f"Unknown method: {method}")

        if method != "autoencoder":
            self._model.fit(X_scaled)

        # Save model
        model_file = self.model_path / f"{method}.pkl"
        with open(model_file, "wb") as f:
            pickle.dump({
                "model": self._model,
                "scaler": self._scaler,
                "features": features,
                "method": method,
                "trained_at": datetime.now().isoformat(),
            }, f)
        logger.info(f"Anomaly model trained and saved: {model_file}")

    def detect(
        self,
        data: pd.DataFrame,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Detect anomalies in new data.

        Returns:
            Dict with anomaly scores, labels, and explanations.
        """
        if self._model is None or self._scaler is None:
            raise RuntimeError("Model not loaded or trained")

        # Prepare data
        X = data[self._features].fillna(method="ffill").fillna(0).values
        X_scaled = self._scaler.transform(X)

        # Get anomaly scores
        if hasattr(self._model, "decision_function"):  # Isolation Forest
            scores = -self._model.decision_function(X_scaled)
            labels = self._model.predict(X_scaled)
            labels = (labels == -1).astype(int)  # Convert -1/1 to 0/1
        elif hasattr(self._model, "predict"):  # Other sklearn models
            scores = self._model.predict_proba(X_scaled)[:, 1]
            labels = (scores > (threshold or 0.5)).astype(int)
        else:  # Autoencoder
            reconstructions = self._model.predict(X_scaled, verbose=0)
            mse = np.mean((X_scaled - reconstructions) ** 2, axis=1)
            scores = mse / np.max(mse) if np.max(mse) > 0 else mse
            labels = (scores > (threshold or 0.5)).astype(int)

        # Generate explanations
        explanations = []
        for idx, (label, score) in enumerate(zip(labels, scores)):
            if label == 1:
                explanation = self._explain_anomaly(
                    data.iloc[idx] if idx < len(data) else None,
                    X_scaled[idx],
                    score,
                )
                explanations.append(explanation)

        return {
            "scores": scores.tolist(),
            "labels": labels.tolist(),
            "anomalies": int(np.sum(labels)),
            "explanations": explanations,
            "timestamp": datetime.now().isoformat(),
        }

    def _explain_anomaly(
        self,
        row: Optional[pd.Series],
        scaled_values: np.ndarray,
        score: float,
    ) -> Dict[str, Any]:
        """Generate human-readable explanation for an anomaly."""
        if row is None:
            return {"score": score, "reason": "High reconstruction error"}

        # Find features deviating most from mean
        means = self._scaler.mean_
        stds = self._scaler.scale_
        deviations = np.abs(scaled_values - means) / (stds + 1e-8)
        top_features = np.argsort(deviations)[-3:][::-1]

        explanation = {
            "score": float(score),
            "timestamp": row.name.isoformat() if hasattr(row, "name") else None,
            "deviating_features": [],
        }

        for feat_idx in top_features:
            if feat_idx < len(self._features):
                feat_name = self._features[feat_idx]
                raw_value = row[feat_name] if feat_name in row else None
                deviation = deviations[feat_idx]
                explanation["deviating_features"].append({
                    "feature": feat_name,
                    "value": float(raw_value) if raw_value is not None else None,
                    "deviation_sigma": float(deviation),
                })

        return explanation


class PredictiveMaintenance:
    """
    Predicts equipment failures using time-series data.

    Uses regression, classification, or survival analysis
    to estimate remaining useful life (RUL) and failure probability.
    """

    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self.model_path = Path(config.ai.model_path) / "predictive"
        self.model_path.mkdir(parents=True, exist_ok=True)
        self._models: Dict[str, Any] = {}
        self._feature_importances: Dict[str, List[Tuple[str, float]]] = {}

    def train_rul_model(
        self,
        run_to_failure_data: List[pd.DataFrame],
        features: List[str],
        target: str = "RUL",
    ) -> None:
        """
        Train Remaining Useful Life (RUL) prediction model.

        Args:
            run_to_failure_data: List of DataFrames, each representing a
                complete run-to-failure cycle.
            features: Feature columns for prediction.
            target: Target column name (RUL in time units).
        """
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split

        # Prepare training data
        X_list, y_list = [], []
        for cycle_df in run_to_failure_data:
            if target not in cycle_df.columns:
                # Calculate RUL as time remaining
                cycle_df = cycle_df.copy()
                cycle_df[target] = np.arange(len(cycle_df) - 1, -1, -1)

            X_list.append(cycle_df[features].values)
            y_list.append(cycle_df[target].values)

        X = np.vstack(X_list)
        y = np.concatenate(y_list)

        # Split and train
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        # Evaluate
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)
        logger.info(f"RUL model trained: R² train={train_score:.3f}, test={test_score:.3f}")

        # Save feature importances
        importances = list(zip(features, model.feature_importances_))
        importances.sort(key=lambda x: x[1], reverse=True)
        self._feature_importances["rul"] = importances

        # Save model
        self._models["rul"] = model
        model_file = self.model_path / "rul_model.pkl"
        with open(model_file, "wb") as f:
            pickle.dump({
                "model": model,
                "features": features,
                "importances": importances,
                "trained_at": datetime.now().isoformat(),
            }, f)

    def predict_rul(self, current_data: pd.DataFrame) -> Dict[str, Any]:
        """Predict remaining useful life for current equipment state."""
        if "rul" not in self._models:
            raise RuntimeError("RUL model not trained")

        model = self._models["rul"]
        features = self._feature_importances["rul"]

        # Extract features in same order as training
        feature_names = [f[0] for f in features]
        X = current_data[feature_names].fillna(method="ffill").fillna(0).values

        # Predict
        predictions = model.predict(X)
        confidence = np.std(predictions) / (np.mean(predictions) + 1e-8)

        return {
            "rul_mean": float(np.mean(predictions)),
            "rul_std": float(np.std(predictions)),
            "rul_min": float(np.min(predictions)),
            "rul_max": float(np.max(predictions)),
            "confidence": float(1.0 / (1.0 + confidence)),
            "unit": "time_units",
            "timestamp": datetime.now().isoformat(),
        }

    def train_failure_classifier(
        self,
        labeled_data: pd.DataFrame,
        features: List[str],
        target: str = "failure",
    ) -> None:
        """Train binary classifier for failure prediction."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report

        # Prepare data
        X = labeled_data[features].fillna(method="ffill").fillna(0).values
        y = labeled_data[target].values

        # Split and train
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced",
        )
        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        report = classification_report(y_test, y_pred, output_dict=True)
        logger.info(f"Failure classifier trained: accuracy={report['accuracy']:.3f}")

        # Save feature importances
        importances = list(zip(features, model.feature_importances_))
        importances.sort(key=lambda x: x[1], reverse=True)
        self._feature_importances["failure"] = importances

        # Save model
        self._models["failure"] = model
        model_file = self.model_path / "failure_classifier.pkl"
        with open(model_file, "wb") as f:
            pickle.dump({
                "model": model,
                "features": features,
                "importances": importances,
                "report": report,
                "trained_at": datetime.now().isoformat(),
            }, f)

    def predict_failure_probability(
        self,
        current_data: pd.DataFrame,
        horizon: int = 24,
    ) -> Dict[str, Any]:
        """Predict probability of failure within given horizon."""
        if "failure" not in self._models:
            raise RuntimeError("Failure classifier not trained")

        model = self._models["failure"]
        features = self._feature_importances["failure"]
        feature_names = [f[0] for f in features]

        X = current_data[feature_names].fillna(method="ffill").fillna(0).values

        # Predict probabilities
        probas = model.predict_proba(X)
        failure_proba = probas[:, 1]  # Probability of failure class

        return {
            "failure_probability": float(np.mean(failure_proba)),
            "probability_std": float(np.std(failure_proba)),
            "horizon_hours": horizon,
            "risk_level": self._assess_risk_level(np.mean(failure_proba)),
            "recommendation": self._generate_recommendation(np.mean(failure_proba)),
            "timestamp": datetime.now().isoformat(),
        }

    def _assess_risk_level(self, probability: float) -> str:
        if probability < 0.1:
            return "low"
        elif probability < 0.3:
            return "medium"
        elif probability < 0.7:
            return "high"
        else:
            return "critical"

    def _generate_recommendation(self, probability: float) -> str:
        if probability < 0.1:
            return "Continue normal operation, monitor regularly."
        elif probability < 0.3:
            return "Schedule preventive maintenance within 30 days."
        elif probability < 0.7:
            return "Schedule maintenance within 7 days, increase monitoring frequency."
        else:
            return "Immediate maintenance required, consider shutdown."