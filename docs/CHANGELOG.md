# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-15

### Added - Initial Release

#### Core Engine
- `BridgeEngine` - Central coordinator for device management and data collection
- `BridgeConfig` - Comprehensive configuration management with pydantic-settings
- Device registration/unregistration lifecycle management
- Concurrent device data collection with asyncio
- Health monitoring for all components

#### Protocol Adapters
- `ModbusAdapter` - Full Modbus TCP/RTU support
  - Coil, discrete input, holding register, input register read/write
  - Data type decoding: bool, int16, uint16, int32, float32
  - Connection retry with exponential backoff
  - Simulation mode for development
- `OpcUaAdapter` - OPC-UA client implementation
  - Node browsing and subscription
  - Data change notifications
  - Certificate-based authentication
  - Simulation mode
- `MqttAdapter` - MQTT publisher/subscriber
  - QoS 0/1/2 support
  - TLS/SSL encryption
  - Authentication (username/password)
  - Multiple data format parsing (JSON, value, raw)
- `HttpAdapter` - HTTP/REST client
  - GET/POST/PUT/DELETE methods
  - Bearer/Basic/API Key authentication
  - Concurrent multi-endpoint reading
  - Multiple response format parsing

#### AI/ML Module
- `AnomalyDetector`
  - Isolation Forest for unsupervised anomaly detection
  - Autoencoder neural network for complex patterns
  - Anomaly explanation generation
  - Model persistence and loading
- `PredictiveMaintenance`
  - Random Forest for Remaining Useful Life (RUL) prediction
  - Failure classifier with SHAP explanations
  - Risk assessment with severity levels
  - Maintenance recommendation generation

#### Data Processing
- `DataNormalizer`
  - Type conversion (int/float/string/bool)
  - Unit conversion (temperature, pressure, flow, length, energy)
  - Range validation with configurable limits
  - Data quality assessment (good/bad/uncertain)
  - Custom validation rules

#### Serialization
- `MessageSerializer`
  - JSON serialization/deserialization
  - MessagePack for compact binary format
  - Protocol Buffers (protobuf) with .proto generation
  - Apache Arrow for columnar data
  - File I/O for all formats

#### Infrastructure
- Docker Compose deployment with 9 services
- PostgreSQL for relational data
- InfluxDB for time-series telemetry
- Redis for caching and rate limiting
- MinIO for object storage (models, artifacts)
- Prometheus and Grafana for monitoring
- Health checks and auto-restart for all services
- Environment-based configuration (.env)

#### Documentation
- Comprehensive README with quick start, architecture overview, and examples
- Detailed ARCHITECTURE.md with component design and data flow
- Complete API reference with all endpoints and WebSocket support
- Production deployment guide with security hardening
- Contributing guide with development workflow
- Protocol adapter development guide

## [Unreleased]

### Planned for v1.1

#### Features
- Protocol adapter hot-plug without service restart
- LSTM-based time-series anomaly detection
- Transformer models for predictive maintenance
- Multi-site federation with master-slave architecture
- WebSocket-based device command channel
- GraphQL API for flexible queries
- Custom dashboard builder with drag-and-drop widgets
- Mobile push notifications (FCM/APNs)

#### Improvements
- Protocol adapter connection pooling
- Enhanced edge-cloud conflict resolution
- Automated model retraining scheduler
- Performance optimizations for 10k+ concurrent devices

### Planned for v2.0

#### Features
- Kubernetes operator with CRDs
- Federated learning for edge AI
- Digital twin integration
- Blockchain-based data integrity ledger
- OPC-UA Historical Data Access (HDA)
- BACnet protocol support
- EtherNet/IP protocol support
- PROFINET protocol support

#### Improvements
- Multi-tenant architecture
- gRPC streaming API
- Distributed tracing (OpenTelemetry)
- Enterprise SSO (SAML/OIDC)
- Compliance reporting (ISO 50001, GDPR)

### Known Issues

#### v1.0.0
- OPC-UA subscription may miss rapid data changes under high load (workaround: increase sampling rate)
- Modbus RTU requires exclusive COM port access on Windows
- Autoencoder model training is CPU-intensive; GPU support planned for v1.1
- Large InfluxDB queries (>100MB) may timeout; use chunking in v1.1
- Edge agent auto-reconnect to cloud may cause brief data gaps