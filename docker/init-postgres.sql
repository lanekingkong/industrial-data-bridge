-- Industrial Data Bridge - PostgreSQL Initialization
-- This script runs on first container startup

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schema
CREATE SCHEMA IF NOT EXISTS idb;

-- Set search path
SET search_path TO idb, public;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    role VARCHAR(50) DEFAULT 'operator',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Devices table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    device_type VARCHAR(100),
    manufacturer VARCHAR(200),
    model VARCHAR(200),
    serial_number VARCHAR(200),
    protocol VARCHAR(50) NOT NULL,
    connection_params JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'offline',
    last_seen TIMESTAMP WITH TIME ZONE,
    location VARCHAR(255),
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Data templates (configuration for data points on each device)
CREATE TABLE IF NOT EXISTS data_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_name VARCHAR(200) NOT NULL,
    points JSONB NOT NULL DEFAULT '[]',
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Device data points configuration
CREATE TABLE IF NOT EXISTS data_points_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    point_name VARCHAR(200) NOT NULL,
    description TEXT,
    data_type VARCHAR(50) NOT NULL,
    unit VARCHAR(50),
    min_val DOUBLE PRECISION,
    max_val DOUBLE PRECISION,
    register_type VARCHAR(100),
    register_address INTEGER,
    scale_factor DOUBLE PRECISION DEFAULT 1.0,
    offset DOUBLE PRECISION DEFAULT 0.0,
    sampling_interval INTEGER DEFAULT 60,
    priority VARCHAR(50) DEFAULT 'medium',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(device_id, point_name)
);

-- Device data cache table
CREATE TABLE IF NOT EXISTS device_data (
    id BIGSERIAL,
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    data JSONB NOT NULL,
    quality VARCHAR(20) DEFAULT 'good',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create hypertable if TimescaleDB is available
-- SELECT create_hypertable('device_data', 'timestamp', if_not_exists => TRUE);

-- AI models table
CREATE TABLE IF NOT EXISTS ai_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    description TEXT,
    version VARCHAR(50),
    model_path TEXT,
    parameters JSONB DEFAULT '{}',
    metrics JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    trained_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Anomaly detection results
CREATE TABLE IF NOT EXISTS anomaly_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    severity VARCHAR(50) NOT NULL,
    detection_method VARCHAR(100),
    score DOUBLE PRECISION,
    details JSONB DEFAULT '{}',
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Predictive maintenance results
CREATE TABLE IF NOT EXISTS maintenance_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    predicted_rul DOUBLE PRECISION,
    failure_probability DOUBLE PRECISION,
    risk_level VARCHAR(50),
    recommendations JSONB,
    model_id UUID REFERENCES ai_models(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Alert rules
CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    condition JSONB NOT NULL,
    severity VARCHAR(50) DEFAULT 'warning',
    is_active BOOLEAN DEFAULT true,
    cooldown_seconds INTEGER DEFAULT 300,
    notify_channels JSONB DEFAULT '["webhook"]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Edge agents table
CREATE TABLE IF NOT EXISTS edge_agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(200),
    status VARCHAR(50) DEFAULT 'offline',
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Protocol tests table
CREATE TABLE IF NOT EXISTS protocol_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    protocol VARCHAR(50) NOT NULL,
    connection_params JSONB DEFAULT '{}',
    test_result JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_protocol ON devices(protocol);
CREATE INDEX IF NOT EXISTS idx_device_data_device_id ON device_data(device_id);
CREATE INDEX IF NOT EXISTS idx_device_data_timestamp ON device_data(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_device_id ON anomaly_events(device_id);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_timestamp ON anomaly_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_events_severity ON anomaly_events(severity);
CREATE INDEX IF NOT EXISTS idx_maintenance_predictions_device_id ON maintenance_predictions(device_id);
CREATE INDEX IF NOT EXISTS idx_edge_agents_agent_id ON edge_agents(agent_id);
CREATE INDEX IF NOT EXISTS idx_edge_agents_status ON edge_agents(status);

-- Insert default admin user (password: admin123)
INSERT INTO users (username, email, password_hash, full_name, role)
VALUES ('admin', 'admin@idb.local', '$2b$12$LJ3m4ys3Gx7KYf6Z1q8xFeJ9MwXN5z0qP.7EYrZL.FyL7kxKq.Ze6', 'System Administrator', 'admin')
ON CONFLICT (username) DO NOTHING;

-- Insert default data template
INSERT INTO data_templates (template_name, points, description)
VALUES (
    'industrial_pump_default',
    '[
        {"name": "temperature", "data_type": "float32", "unit": "celsius", "min": 0, "max": 100, "register_type": "holding_register", "address": 40001},
        {"name": "pressure", "data_type": "float32", "unit": "bar", "min": 0, "max": 20, "register_type": "holding_register", "address": 40003},
        {"name": "flow_rate", "data_type": "float32", "unit": "l/min", "min": 0, "max": 1000, "register_type": "holding_register", "address": 40005},
        {"name": "vibration", "data_type": "float32", "unit": "mm/s", "min": 0, "max": 10, "register_type": "holding_register", "address": 40007}
    ]',
    'Default monitoring points for industrial pumps'
)
ON CONFLICT DO NOTHING;