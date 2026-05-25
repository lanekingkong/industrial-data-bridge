# Industrial Data Bridge

<div align="center">

![Industrial Data Bridge Logo](docs/images/logo.png)

**AI-powered industrial device data collection and protocol conversion solution**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://industrial-data-bridge.github.io/docs)
[![Docker Pulls](https://img.shields.io/docker/pulls/industrialdatabridge/core)](https://hub.docker.com/r/industrialdatabridge)
[![Tests](https://github.com/industrial-data-bridge/industrial-data-bridge/actions/workflows/tests.yml/badge.svg)](https://github.com/industrial-data-bridge/industrial-data-bridge/actions)

</div>

## 🚀 Overview

**Industrial Data Bridge** is an open-source solution that solves the critical pain point in SME digital transformation: **"old equipment, messy protocols, data can't be collected, can't be connected"**.

Our platform bridges legacy industrial equipment with modern data systems through:

- **Multi-protocol data collection** (Modbus, OPC-UA, MQTT, HTTP, etc.)
- **Intelligent protocol conversion** and data standardization
- **AI-driven anomaly detection** and predictive maintenance
- **Real-time visualization** and monitoring dashboards
- **Edge computing** support for low-latency processing

## 🎯 Why Industrial Data Bridge?

| Problem | Traditional Solution | Our Solution |
|---------|---------------------|--------------|
| Old equipment with proprietary protocols | Manual data collection, custom scripts | **Universal protocol adapters** |
| Data formats inconsistent across devices | Manual data cleaning, Excel macros | **AI-powered data normalization** |
| No early warning for equipment failures | Reactive maintenance, costly downtime | **Predictive maintenance with ML** |
| High cost of industrial IoT platforms | $50k+ annual licenses | **Open-source, self-hosted** |
| Complex deployment and management | Vendor lock-in, long implementation | **Docker-based, one-command deploy** |

## ✨ Key Features

### 🔌 Multi-Protocol Support
- **Modbus TCP/RTU** - Connect to PLCs, sensors, meters
- **OPC-UA** - Industrial automation standard
- **MQTT** - IoT messaging protocol
- **HTTP/REST APIs** - Web services and cloud platforms
- **Custom protocols** - Extensible adapter framework

### 🧠 AI-Powered Intelligence
- **Anomaly Detection** - Identify abnormal patterns in real-time
- **Predictive Maintenance** - Forecast equipment failures
- **Data Quality Assessment** - Automatic validation and cleaning
- **Adaptive Learning** - Models improve with more data

### 📊 Visualization & Monitoring
- **Real-time Dashboards** - Live equipment status
- **Historical Analytics** - Trend analysis and reporting
- **Alert Management** - Email, SMS, webhook notifications
- **Mobile Support** - Responsive web interface

### ⚙️ Edge Computing
- **Local Processing** - Reduce cloud dependency
- **Low Latency** - Sub-second response times
- **Offline Operation** - Continue working without internet
- **Data Filtering** - Send only relevant data to cloud

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Industrial Data Bridge                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Protocol │  │ Protocol │  │ Protocol │  │ Protocol │   │
│  │ Adapters │  │ Adapters │  │ Adapters │  │ Adapters │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│         │            │            │            │            │
├─────────────────────────────────────────────────────────────┤
│                  Data Normalization Engine                   │
│         ┌──────────────────────────────────────┐            │
│         │  Unit Conversion │ Quality Assessment │            │
│         │  Type Casting    │ Range Validation   │            │
│         └──────────────────────────────────────┘            │
│                     │                                        │
├─────────────────────────────────────────────────────────────┤
│                    AI Processing Layer                       │
│         ┌──────────────────────────────────────┐            │
│         │  Anomaly Detection  │  Predictive    │            │
│         │  Pattern Learning   │  Maintenance   │            │
│         └──────────────────────────────────────┘            │
│                     │                                        │
├─────────────────────────────────────────────────────────────┤
│                    Storage & Analytics                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Time-Series│  │Relational │  │Object    │  │Cache     │   │
│  │Database   │  │Database   │  │Storage   │  │Layer     │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                     │                                        │
├─────────────────────────────────────────────────────────────┤
│                    API & Visualization                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │REST API   │  │WebSocket │  │Dashboard │  │Mobile    │   │
│  │GraphQL    │  │Streaming │  │Reports   │  │App       │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🚦 Quick Start

### Prerequisites
- Python 3.8+ or Docker
- PostgreSQL 12+ (optional, SQLite for development)
- Redis (optional, for caching)

### Installation

#### Using Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/industrial-data-bridge/industrial-data-bridge.git
cd industrial-data-bridge

# Copy environment configuration
cp .env.example .env
# Edit .env with your settings

# Start all services
docker compose up -d

# Access the web interface
# Windows: start http://localhost:8000
# macOS: open http://localhost:8000
# Linux: xdg-open http://localhost:8000
```

#### Manual Installation
```bash
# Clone the repository
git clone https://github.com/industrial-data-bridge/industrial-data-bridge.git
cd industrial-data-bridge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev,ai,edge]"

# Initialize database
python scripts/init_db.py

# Start the bridge
python -m src.main
```

### Basic Usage

```python
from src.core import BridgeEngine, BridgeConfig

# Initialize bridge
config = BridgeConfig()
engine = BridgeEngine(config)

# Register a Modbus device
engine.register_device(
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
            "name": "pressure",
            "register_type": "holding_register",
            "address": 102,
            "data_type": "float32",
            "unit": "kpa",
        },
    ]
)

# Start collecting data
await engine.start()
data = await engine.collect_device("pump_001")
print(f"Collected {len(data)} data points")
```

## 📖 Documentation

Comprehensive documentation is available at [https://industrial-data-bridge.github.io/docs](https://industrial-data-bridge.github.io/docs)

- [Architecture Overview](docs/ARCHITECTURE.md) - Detailed system design
- [API Reference](docs/API.md) - REST API and SDK documentation
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment
- [Protocol Adapters](docs/PROTOCOLS.md) - Supported protocols and configuration
- [AI Features](docs/AI.md) - Machine learning capabilities
- [Contributing Guide](docs/CONTRIBUTING.md) - How to contribute

## 🧪 Examples

Check out the [examples/](examples/) directory for practical use cases:

- [Modbus PLC Integration](examples/modbus_plc/) - Connect to Siemens/Allen-Bradley PLCs
- [OPC-UA Server](examples/opcua_server/) - Create OPC-UA server for legacy equipment
- [MQTT IoT Gateway](examples/mqtt_gateway/) - Bridge MQTT devices to industrial systems
- [Predictive Maintenance](examples/predictive_maintenance/) - ML model for equipment failure prediction
- [Dashboard Customization](examples/dashboard/) - Custom Grafana/React dashboards

## 🛠️ Development

### Project Structure
```
industrial-data-bridge/
├── src/                    # Source code
│   ├── core/              # Core engine and configuration
│   ├── protocols/         # Protocol adapters
│   ├── ai/                # AI/ML modules
│   ├── web/               # Web interface and APIs
│   ├── edge/              # Edge computing components
│   └── utils/             # Utilities and helpers
├── tests/                 # Test suite
├── docs/                  # Documentation
├── examples/              # Example implementations
├── docker/                # Docker configurations
├── config/                # Configuration files
└── scripts/               # Utility scripts
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test module
pytest tests/test_protocols.py -v
```

### Code Quality
```bash
# Format code
black src tests

# Lint code
flake8 src tests

# Type checking
mypy src
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests before committing
pytest
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by real-world challenges in SME digital transformation
- Built with amazing open-source projects: FastAPI, PostgreSQL, InfluxDB, Redis, Docker
- Thanks to all contributors and users who make this project better

## 📞 Support

- 📖 [Documentation](https://github.com/industrial-data-bridge/industrial-data-bridge/tree/main/docs)
- 🐛 [Issue Tracker](https://github.com/industrial-data-bridge/industrial-data-bridge/issues)
- 💬 [Discussions](https://github.com/industrial-data-bridge/industrial-data-bridge/discussions)
- 📧 [Email Support](mailto:team@industrial-data-bridge.org)

---

<div align="center">
Made with ❤️ for the industrial community
</div>