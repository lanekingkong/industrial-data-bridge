"""
Example: Predictive Maintenance

Demonstrates using AI models to predict equipment failures
and schedule maintenance.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import BridgeEngine, BridgeConfig
from src.ai.anomaly_predictive import AnomalyDetector, PredictiveMaintenance
from src.utils.data_normalizer import DataNormalizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_historical_data(days: int = 30, samples_per_day: int = 24):
    """Generate historical data for training."""
    data = []
    base_time = datetime.now() - timedelta(days=days)
    
    for day in range(days):
        for sample in range(samples_per_day):
            # Normal operating conditions
            timestamp = base_time + timedelta(days=day, hours=sample)
            
            # Simulate gradual degradation
            degradation_factor = 1 + (day / days) * 0.5
            
            point = {
                "timestamp": timestamp.isoformat(),
                "temperature": random.uniform(30, 40) * degradation_factor,
                "vibration": random.uniform(0.1, 0.3) * degradation_factor,
                "current": random.uniform(10, 15) * degradation_factor,
                "pressure": random.uniform(5, 7) * degradation_factor,
                "hours_run": day * 24 + sample,
            }
            
            # Add occasional anomalies (5% of samples)
            if random.random() < 0.05:
                point["temperature"] *= 1.5
                point["vibration"] *= 2.0
            
            data.append(point)
    
    return data


def generate_failure_labels(data):
    """Generate RUL (Remaining Useful Life) labels."""
    labels = []
    total_samples = len(data)
    
    for i, point in enumerate(data):
        # Simulate RUL decreasing over time
        rul = total_samples - i
        labels.append(rul)
    
    return labels


async def main():
    """Main predictive maintenance example."""
    logger.info("Starting Predictive Maintenance example...")
    
    # Generate training data
    logger.info("Generating training data...")
    historical_data = generate_historical_data(days=30, samples_per_day=24)
    logger.info(f"Generated {len(historical_data)} historical data points")
    
    # 1. Anomaly Detection
    logger.info("1. Training Anomaly Detector...")
    anomaly_detector = AnomalyDetector(method="isolation_forest", contamination=0.1)
    
    # Train on historical data
    train_result = anomaly_detector.train(historical_data)
    logger.info(f"Anomaly detector trained: {train_result}")
    
    # Test with new data
    test_data = [
        {"temperature": 35, "vibration": 0.2, "current": 12, "pressure": 6, "hours_run": 800},
        {"temperature": 65, "vibration": 0.8, "current": 25, "pressure": 10, "hours_run": 800},  # Anomaly
    ]
    
    anomaly_result = anomaly_detector.predict(test_data)
    logger.info(f"Anomaly detection results: {anomaly_result}")
    
    # Explain anomalies
    for i, prediction in enumerate(anomaly_result["predictions"]):
        if prediction["is_anomaly"]:
            explanation = anomaly_detector.explain_anomaly(
                score=prediction["score"],
                feature_values=test_data[i],
            )
            logger.info(f"Anomaly explanation for sample {i}: {explanation}")
    
    # 2. Predictive Maintenance
    logger.info("\n2. Training Predictive Maintenance Model...")
    pm_predictor = PredictiveMaintenance()
    
    # Generate RUL labels
    rul_labels = generate_failure_labels(historical_data)
    
    # Train model
    pm_train_result = pm_predictor.train(
        features=historical_data,
        labels={"rul": rul_labels},
    )
    logger.info(f"Predictive maintenance model trained: {pm_train_result}")
    
    # Test predictions
    test_features = [
        {"temperature": 55, "vibration": 0.95, "current": 22, "pressure": 9, "hours_run": 5000},
        {"temperature": 32, "vibration": 0.15, "current": 11, "pressure": 5.5, "hours_run": 1000},
    ]
    
    for i, features in enumerate(test_features):
        prediction = pm_predictor.predict([features])
        logger.info(f"Sample {i} prediction: {prediction}")
        
        # Risk assessment
        risk_assessment = pm_predictor.assess_failure_risk(features)
        logger.info(f"Sample {i} risk assessment: {risk_assessment}")
    
    # 3. Integration with Bridge Engine
    logger.info("\n3. Integration with Bridge Engine...")
    
    # Create bridge configuration
    config = BridgeConfig()
    engine = BridgeEngine(config)
    
    try:
        await engine.start()
        
        # Register a simulated device
        await engine.register_device(
            device_id="pump_001",
            name="Main Water Pump",
            protocol="modbus",
            connection_params={
                "mode": "tcp",
                "host": "192.168.1.100",
                "port": 502,
                "unit_id": 1,
            },
            points=[
                {
                    "name": "temperature",
                    "register_type": "holding_register",
                    "address": 100,
                    "data_type": "float32",
                    "unit": "celsius",
                },
                {
                    "name": "vibration",
                    "register_type": "holding_register",
                    "address": 102,
                    "data_type": "float32",
                    "unit": "mm/s",
                },
            ],
        )
        
        # Simulate data collection and AI processing
        logger.info("Simulating real-time monitoring...")
        
        for cycle in range(3):
            # Collect data
            data = await engine.collect_device("pump_001")
            
            # Prepare for AI processing
            features = {}
            for point_name, point_data in data.items():
                if point_data["quality"] == "good":
                    features[point_name] = point_data["value"]
            
            if features:
                # Anomaly detection
                anomaly_result = anomaly_detector.predict([features])
                
                # Predictive maintenance
                pm_result = pm_predictor.predict([features])
                
                logger.info(f"Cycle {cycle + 1}:")
                logger.info(f"  Features: {features}")
                logger.info(f"  Anomaly: {anomaly_result['predictions'][0]['is_anomaly']}")
                logger.info(f"  RUL estimate: {pm_result['rul_estimate']} hours")
                logger.info(f"  Risk level: {pm_result['risk_level']}")
            
            await asyncio.sleep(1)
        
    except Exception as e:
        logger.error(f"Integration failed: {e}", exc_info=True)
    finally:
        await engine.stop()
    
    # 4. Save models for production use
    logger.info("\n4. Saving trained models...")
    
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)
    
    # Save anomaly detector
    anomaly_model_path = models_dir / "anomaly_detector.pkl"
    save_result = anomaly_detector.save_model(str(anomaly_model_path))
    if save_result["success"]:
        logger.info(f"Anomaly detector saved to {anomaly_model_path}")
    
    # Save predictive maintenance model
    pm_model_path = models_dir / "predictive_maintenance"
    save_result = pm_predictor.save_model(str(pm_model_path))
    if save_result["success"]:
        logger.info(f"Predictive maintenance model saved to {pm_model_path}")
    
    logger.info("Predictive Maintenance example completed!")


async def real_time_monitoring_example():
    """Example of real-time monitoring with AI."""
    logger.info("Real-time monitoring example...")
    
    # Initialize components
    normalizer = DataNormalizer(default_unit="celsius")
    anomaly_detector = AnomalyDetector(method="autoencoder")
    pm_predictor = PredictiveMaintenance()
    
    # Simulate real-time data stream
    logger.info("Starting real-time monitoring...")
    
    try:
        for i in range(10):
            # Simulate incoming data
            raw_data = {
                "temperature": random.uniform(30, 50),
                "vibration": random.uniform(0.1, 0.5),
                "current": random.uniform(10, 20),
                "pressure": random.uniform(5, 8),
                "hours_run": 1000 + i * 10,
            }
            
            # Normalize data
            normalized = {}
            for key, value in raw_data.items():
                if key == "temperature":
                    result = normalizer.normalize_point(
                        point_name=key,
                        raw_value=value,
                        unit="celsius",
                        data_type="float",
                    )
                    normalized[key] = result["value"]
                else:
                    normalized[key] = value
            
            # Anomaly detection
            anomaly_result = anomaly_detector.predict([normalized])
            is_anomaly = anomaly_result["predictions"][0]["is_anomaly"]
            
            # Predictive maintenance
            pm_result = pm_predictor.predict([normalized])
            
            # Log results
            status = "⚠️ ANOMALY" if is_anomaly else "✓ NORMAL"
            logger.info(f"Sample {i}: {status}")
            logger.info(f"  Data: {normalized}")
            if is_anomaly:
                logger.info(f"  Anomaly score: {anomaly_result['predictions'][0]['score']:.3f}")
            logger.info(f"  RUL: {pm_result.get('rul_estimate', 'N/A')} hours")
            logger.info(f"  Risk: {pm_result.get('risk_level', 'N/A')}")
            
            await asyncio.sleep(0.5)
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring error: {e}")


if __name__ == "__main__":
    # Run main example
    asyncio.run(main())
    
    # Uncomment to run real-time monitoring example
    # asyncio.run(real_time_monitoring_example())