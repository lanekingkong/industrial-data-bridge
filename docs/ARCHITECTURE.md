# Architecture Design Document

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Design](#component-design)
4. [Data Flow](#data-flow)
5. [Protocol Layer](#protocol-layer)
6. [AI Layer](#ai-layer)
7. [Storage Layer](#storage-layer)
8. [Edge Computing](#edge-computing)
9. [Security](#security)
10. [Deployment Architecture](#deployment-architecture)

## Overview

Industrial Data Bridge follows a **layered microservices architecture** with the following principles:

- **Pluggable protocols**: New protocols added without modifying core
- **Data-driven AI**: Models adapt based on incoming data
- **Event-driven**: Real-time streaming for low latency
- **Cloud-native**: Designed for containerized deployment
- **Edge-cloud hybrid**: Local edge processing with cloud orchestration

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐           │
│  │ REST API │  │GraphQL  │  │WebSocket│  │ gRPC API │           │
│  └─────────┘  └─────────┘  └─────────┘  └──────────┘           │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Bridge Engine                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │  │
│  │  │ Device   │  │Schedule  │  │Collector │  │Conductor │ │  │
│  │  │ Registry │  │Manager   │  │Service   │  │Service   │ │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                     PROTOCOL ADAPTER LAYER                        │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐   │
│  │Modbus  │  │OPC-UA  │  │ MQTT   │  │ HTTP   │  │Custom  │   │
│  │Adapter │  │Adapter │  │Adapter │  │Adapter │  │Adapter │   │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘   │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                    DATA NORMALIZATION LAYER                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Type Conv │  │Unit Conv │  │Quality   │  │Range     │       │
│  │          │  │          │  │Assessment│  │Validator │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                        AI LAYER                                   │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │Anomaly Detection │  │Predictive        │                     │
│  │Engine            │  │Maintenance Engine│                     │
│  └──────────────────┘  └──────────────────┘                     │
└──────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │PostgreSQL│  │InfluxDB  │  │  MinIO   │  │  Redis   │       │
│  │Relational│  │TimeSeries│  │Objects   │  │  Cache   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└──────────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Bridge Engine

The central coordinator managing device lifecycle, data collection scheduling, and component orchestration.

```python
class BridgeEngine:
    """
    Core Responsibilities:
    - Device registration and management
    - Data collection scheduling
    - Protocol adapter lifecycle
    - AI model coordination
    - Health monitoring
    """
```

**Key Design Decisions**:
- Async-first architecture using `asyncio` for high concurrency
- Protocol adapter pattern for extensibility
- Event bus for decoupled inter-component communication
- Circuit breaker for fault tolerance

### 2. Protocol Adapter System

Each protocol adapter implements the `ProtocolAdapter` ABC:

```python
class ProtocolAdapter(ABC):
    async def connect() -> None
    async def disconnect() -> None
    async def read_point(point) -> Any
    async def write_point(point, value) -> bool
    async def read_all_points(points) -> List[Any]
    async def write_points(writes) -> List[bool]
```

**Adapter Registry**:
- Modbus: `pymodbus` (both sync/async clients)
- OPC-UA: `opcua-asyncio` (async client)
- MQTT: `paho-mqtt` (async wrapper)
- HTTP: `aiohttp` (native async)

### 3. Data Normalizer

```python
class DataNormalizer:
    """
    Processing Pipeline:
    1. Type conversion (int/float/string/bool)
    2. Unit conversion (SI/Imperial)
    3. Range validation (min/max/deadband)
    4. Quality assessment (good/bad/uncertain)
    5. Timestamp standardization (UTC)
    """
```

**Supported Unit Conversions**:
- Temperature: Celsius ↔ Fahrenheit ↔ Kelvin
- Pressure: kPa ↔ bar ↔ MPa ↔ psi
- Flow: L/min ↔ m³/h
- Energy: kWh ↔ MJ
- Length: mm/inch, m/ft

### 4. AI Processing

#### Anomaly Detection
- Isolation Forest: Lightweight, fast training, no labeled data needed
- Autoencoder: Deep neural network for complex patterns
- Statistical: Z-score, IQR for simple monitoring

#### Predictive Maintenance
- Random Forest: Remaining Useful Life (RUL) estimation
- XGBoost: Failure classification with SHAP explanations
- LSTM: Time-series forecasting (planned)

**Model Lifecycle**:
1. Training: Scheduled retraining on accumulated data
2. Evaluation: Precision/recall/F1 on held-out validation set
3. Deployment: Model serialized and loaded by engine
4. Monitoring: Drift detection and accuracy tracking

## Data Flow

### 1. Real-time Collection
```
Device → ProtocolAdapter → Normalizer → [Validation] → Storage → [AI Inference] → API
```

### 2. Batch Processing
```
Scheduler → MultiDeviceCollector → Normalizer(batch) → InfluxDB → Analytics → Dashboard
```

### 3. Command Flow
```
API → BridgeEngine → ProtocolAdapter → Device
           ↑
       [Validation & Authorization]
```

### 4. AI Inference Flow
```
InfluxDB → Feature Extractor → ML Model → Results → Alert Manager
                                              ↓
                                       PostgreSQL (logs)
```

## Protocol Layer

### Adapter States
```
[Created] → connect() → [Connected]
                           ↓
                      read/write
                           ↓
                      [Error] → retry → [Connected]
                           ↓
                      [Disconnected]
```

### Connection Management
- Connection pooling for TCP-based protocols
- Automatic reconnection with exponential backoff
- Health checks via periodic pings
- Timeout handling with graceful degradation

### Error Handling Strategy
1. **Transient** (3 retries): Network timeout, connection reset
2. **Persistent**: Authentication failure, rate limit
3. **Data Quality**: Range violation, stale data

## AI Layer

### Training Pipeline
```python
Data Collection → Cleaning → Feature Engineering → Model Training → Evaluation → Deployment
```

### Inference Pipeline
```python
Real-time Data → Feature Extraction → Model Inference → Result Filtering → Alert/Storage
```

### Model Management
- Version tracking with timestamp and metadata
- A/B testing support for model comparison
- Automatic rollback on degradation
- Model compression for edge deployment (ONNX)

## Storage Layer

### Database Strategy

| Data Type | Storage | Rationale |
|-----------|---------|-----------|
| Device metadata | PostgreSQL | Relational, ACID |
| Time-series telemetry | InfluxDB | Optimized for time-series |
| AI models | MinIO/S3 | Large binary objects |
| Session/rate limits | Redis | Low latency, TTL |
| Logs | File/Elasticsearch | Append-only, searchable |

### Data Retention
- Raw telemetry: 90 days
- Hourly aggregates: 1 year
- Daily aggregates: 5 years
- Anomaly events: Indefinite
- Model artifacts: Last 10 versions

## Edge Computing

### Edge Agent Architecture
```
┌──────────────────────────────────────┐
│             Edge Agent                │
│  ┌──────────┐  ┌──────────────────┐  │
│  │Local     │  │Protocol Adapters │  │
│  │Storage   │  │(subset)          │  │
│  └──────────┘  └──────────────────┘  │
│  ┌──────────┐  ┌──────────────────┐  │
│  │AI Models │  │Data Filter/      │  │
│  │(ONNX)    │  │Aggregator        │  │
│  └──────────┘  └──────────────────┘  │
│  ┌──────────────────────────────────┐│
│  │       Sync Manager               ││
│  │  (eventual consistency with cloud)││
│  └──────────────────────────────────┘│
└──────────────────────────────────────┘
```

### Edge-Cloud Sync Protocol
1. **Real-time**: Critical alerts transmitted immediately
2. **Batch**: Normal data synced at configured intervals
3. **Offline**: Local buffering with conflict resolution
4. **Priority**: Hierarchical data importance weighting

### Edge AI
- Model compression (quantization, pruning)
- ONNX Runtime for inference
- Feature caching for reduced computation
- Ensemble of lightweight models vs. single complex

## Security

### Authentication & Authorization
- JWT-based API authentication
- Role-based access control (RBAC)
- API key for machine-to-machine
- OAuth2 for SSO integration

### Data Protection
- TLS 1.3 for all network communications
- AES-256 for sensitive data at rest
- Configurable data retention policies
- Audit logging for all mutations

### Network Security
- Firewall-friendly port configuration
- VPN support for remote equipment access
- Rate limiting and DDoS protection
- IP allowlisting for device connections

## Deployment Architecture

### Single Node (SME)
```
┌────────────────────────────────┐
│         Docker Host            │
│  ┌──────┐ ┌──────┐ ┌──────┐  │
│  │ Core │ │ DB   │ │Cache │  │
│  └──────┘ └──────┘ └──────┘  │
└────────────────────────────────┘
```

### High Availability (Enterprise)
```
┌─────────┐   ┌─────────┐   ┌─────────┐
│ Core-1  │   │ Core-2  │   │ Core-N  │
└─────────┘   └─────────┘   └─────────┘
      │             │             │
┌─────────────────────────────────────┐
│           Load Balancer             │
└─────────────────────────────────────┘
      │             │             │
┌─────────┐   ┌─────────┐   ┌─────────┐
│  DB     │   │  DB     │   │  Cache  │
│ Primary │   │ Replica │   │ Cluster │
└─────────┘   └─────────┘   └─────────┘
```

### Edge-Cloud Hybrid
```
     ┌─────────────────────┐
     │      Cloud Core     │
     │  (Management/ML)    │
     └─────────────────────┘
           │    │    │
    ┌──────┘    │    └──────┐
    │           │           │
┌───────┐  ┌───────┐  ┌───────┐
│ Edge  │  │ Edge  │  │ Edge  │
│ Site A│  │ Site B│  │ Site C│
└───────┘  └───────┘  └───────┘
```

## Performance Characteristics

| Metric | Target | Measured |
|--------|--------|----------|
| Data point latency | < 50ms | 10-30ms |
| Concurrent devices | 1000+ | Platform dependent |
| Throughput | 10k points/s | 8-12k points/s |
| Memory per device | < 2MB | ~1.5MB |
| Model inference | < 100ms | 5-50ms |
| Dashboard refresh | < 1s | ~500ms |

## Future Roadmap

### v1.1
- [x] Core protocol adapters
- [x] Data normalization
- [x] Basic AI anomaly detection

### v1.2 (Planned)
- [ ] Protocol adapter hot-plug
- [ ] Advanced ML models (LSTM, Transformers)
- [ ] Multi-site federation

### v2.0 (Planned)
- [ ] Kubernetes operator
- [ ] Edge AI with federated learning
- [ ] Digital twin integration
- [ ] Blockchain-based data integrity