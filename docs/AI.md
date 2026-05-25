# AI Features

Industrial Data Bridge includes AI capabilities for intelligent data processing and predictive maintenance.

## Overview

The AI subsystem provides:

- **Anomaly Detection**: Real-time identification of abnormal device behavior
- **Predictive Maintenance**: ML-based equipment failure forecasting
- **Data Quality Assessment**: Automatic validation and scoring of incoming data
- **Pattern Recognition**: Time-series pattern matching for operational insights

## Anomaly Detection

### Supported Algorithms

| Algorithm | Best For | Training Required |
|-----------|----------|-------------------|
| Isolation Forest | High-dimensional data, fast detection | Yes |
| LSTM Autoencoder | Time-series anomaly detection | Yes |
| Statistical (Z-score, IQR) | Simple threshold-based | No |
| DBSCAN | Clustering-based outlier detection | No |

### Configuration

```yaml
ai:
  anomaly_detection:
    enabled: true
    algorithm: isolation_forest
    sensitivity: 0.95
    window_size: 100
    min_training_samples: 1000

  models:
    isolation_forest:
      n_estimators: 100
      contamination: 0.05
      random_state: 42

    lstm_autoencoder:
      sequence_length: 50
      encoding_dim: 32
      epochs: 50
      batch_size: 32
```

### Usage

```python
from src.ai.anomaly_predictive import AnomalyDetector

detector = AnomalyDetector(config)
result = await detector.detect(device_id="pump_001", data=data_points)

if result["is_anomaly"]:
    print(f"Anomaly detected: {result['score']} (threshold: {result['threshold']})")
```

## Predictive Maintenance

### Model Architecture

The predictive maintenance model uses a multi-layer approach:

1. **Feature Engineering**: Extract statistical features from time-series
2. **Sequence Modeling**: LSTM/Transformer for temporal patterns
3. **Failure Classification**: Predict failure probability and estimated time

### Configuration

```yaml
ai:
  predictive_maintenance:
    enabled: true
    prediction_window: 24h
    retrain_interval: 7d
    failure_threshold: 0.7

  models:
    predictive:
      model_type: lstm
      lookback_window: 168  # 7 days of hourly data
      forecast_horizon: 24  # 24 hours prediction
      features: ["temperature", "pressure", "vibration", "current", "rpm"]
```

### Usage

```python
from src.ai.anomaly_predictive import PredictiveMaintenance

pm = PredictiveMaintenance(config)
prediction = await pm.predict(device_id="pump_001")

print(f"Failure probability: {prediction['probability']:.2%}")
print(f"Estimated time to failure: {prediction['ttf_hours']:.1f} hours")
if prediction['alert']:
    print("Maintenance recommended!")
```

## Model Training

### Training Data Requirements

- Minimum 1000 data points per device
- At least 50 labeled anomaly examples (optional)
- Data covering normal and abnormal operating conditions

### Training Command

```bash
# Train anomaly detection model
python -m src.ai.anomaly_predictive --train --device pump_001

# Train predictive maintenance model
python -m src.ai.anomaly_predictive --train-predictive --device pump_001

# Retrain all models
python -m src.ai.anomaly_predictive --retrain-all
```

## Model Management

Models are stored in the `./models/` directory:

```
models/
├── anomaly/
│   ├── pump_001_isolation_forest.pkl
│   └── conveyor_002_lstm.h5
├── predictive/
│   ├── pump_001_lstm.h5
│   └── compressor_001_lstm.h5
└── scalers/
    ├── pump_001_scaler.pkl
    └── compressor_001_scaler.pkl
```

## Performance Considerations

- Inference latency: < 50ms for Isolation Forest, < 100ms for LSTM
- Memory: ~10-50MB per loaded model
- GPU support: Available for LSTM models (CUDA)
- Batch processing: Up to 1000 data points per inference call

## Limitations

- Models require device-specific training; no universal model across device types
- Prediction accuracy improves with more historical data
- Sudden mechanical failures (e.g., physical breakage) may not be predictable
- Requires consistent data quality for reliable predictions