"""
Example: Dashboard and Visualization

Demonstrates creating dashboards for monitoring
industrial equipment data.
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import BridgeEngine, BridgeConfig
from src.utils.data_normalizer import DataNormalizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_sample_data(days: int = 7, devices: int = 3):
    """Generate sample data for dashboard demonstration."""
    data = []
    base_time = datetime.now() - timedelta(days=days)
    
    device_names = ["Pump-001", "Compressor-002", "Fan-003"]
    device_types = ["pump", "compressor", "fan"]
    
    for device_idx in range(devices):
        device_id = f"device_{device_idx:03d}"
        device_name = device_names[device_idx]
        device_type = device_types[device_idx]
        
        for day in range(days):
            for hour in range(24):
                timestamp = base_time + timedelta(days=day, hours=hour)
                
                # Generate realistic data based on device type
                if device_type == "pump":
                    temperature = random.uniform(30, 50)
                    pressure = random.uniform(5, 10)
                    flow = random.uniform(100, 500)
                    vibration = random.uniform(0.1, 0.3)
                    power = random.uniform(10, 20)
                    
                elif device_type == "compressor":
                    temperature = random.uniform(40, 70)
                    pressure = random.uniform(8, 15)
                    flow = random.uniform(50, 200)
                    vibration = random.uniform(0.2, 0.5)
                    power = random.uniform(20, 40)
                    
                else:  # fan
                    temperature = random.uniform(25, 40)
                    pressure = random.uniform(1, 3)
                    flow = random.uniform(1000, 5000)
                    vibration = random.uniform(0.05, 0.2)
                    power = random.uniform(5, 15)
                
                # Add occasional anomalies
                if random.random() < 0.02:  # 2% anomaly rate
                    temperature *= 1.5
                    vibration *= 2.0
                
                data_point = {
                    "timestamp": timestamp.isoformat(),
                    "device_id": device_id,
                    "device_name": device_name,
                    "device_type": device_type,
                    "temperature": round(temperature, 1),
                    "pressure": round(pressure, 1),
                    "flow": round(flow, 1),
                    "vibration": round(vibration, 2),
                    "power": round(power, 1),
                    "efficiency": round(flow / power, 1) if power > 0 else 0,
                }
                
                data.append(data_point)
    
    return data


def create_grafana_dashboard(devices: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a Grafana dashboard JSON configuration."""
    
    # Base dashboard template
    dashboard = {
        "dashboard": {
            "id": None,
            "uid": "industrial-data-bridge",
            "title": "Industrial Data Bridge Dashboard",
            "tags": ["industrial", "iot", "monitoring", "predictive-maintenance"],
            "timezone": "browser",
            "schemaVersion": 36,
            "version": 0,
            "refresh": "30s",
            "panels": [],
            "time": {
                "from": "now-7d",
                "to": "now"
            },
            "timepicker": {
                "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"],
                "time_options": ["5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"]
            }
        },
        "folderId": 0,
        "overwrite": True
    }
    
    # Create panels for each device type
    panel_id = 1
    
    # 1. Overview Panel
    overview_panel = {
        "id": panel_id,
        "type": "stat",
        "title": "System Overview",
        "gridPos": {"h": 3, "w": 12, "x": 0, "y": 0},
        "targets": [
            {
                "refId": "A",
                "queryType": "randomWalk",
                "datasource": {"type": "influxdb", "uid": "influxdb"},
                "query": "SELECT count(\"value\") FROM \"device_status\" WHERE $timeFilter GROUP BY time($__interval) fill(null)",
            }
        ],
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "red", "value": 80}
                    ]
                }
            }
        },
        "options": {
            "orientation": "horizontal",
            "reduceOptions": {"values": False, "calcs": ["lastNotNull"]},
            "showThresholdLabels": False,
            "showThresholdMarkers": True
        }
    }
    dashboard["dashboard"]["panels"].append(overview_panel)
    panel_id += 1
    
    # 2. Temperature Time Series
    temp_panel = {
        "id": panel_id,
        "type": "timeseries",
        "title": "Temperature Monitoring",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 3},
        "targets": [
            {
                "refId": "A",
                "query": "SELECT mean(\"temperature\") FROM \"device_metrics\" WHERE $timeFilter GROUP BY time($__interval), \"device_name\" fill(null)",
                "datasource": {"type": "influxdb", "uid": "influxdb"},
            }
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "celsius",
                "color": {"mode": "palette-classic"},
                "custom": {
                    "axisLabel": "Temperature (°C)",
                    "axisPlacement": "auto",
                    "barAlignment": 0,
                    "drawStyle": "line",
                    "fillOpacity": 10,
                    "gradientMode": "none",
                    "lineInterpolation": "linear",
                    "lineWidth": 1,
                    "pointSize": 5,
                    "showPoints": "auto",
                    "spanNulls": False,
                    "stacking": {"mode": "none", "group": "A"},
                    "thresholdsStyle": {"mode": "off"}
                }
            }
        },
        "options": {
            "tooltip": {"mode": "single"},
            "legend": {"displayMode": "list", "placement": "bottom", "calcs": []}
        }
    }
    dashboard["dashboard"]["panels"].append(temp_panel)
    panel_id += 1
    
    # 3. Pressure Gauge
    pressure_panel = {
        "id": panel_id,
        "type": "gauge",
        "title": "Pressure",
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 11},
        "targets": [
            {
                "refId": "A",
                "query": "SELECT last(\"pressure\") FROM \"device_metrics\" WHERE $timeFilter GROUP BY \"device_name\"",
                "datasource": {"type": "influxdb", "uid": "influxdb"},
            }
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "pressurebar",
                "min": 0,
                "max": 20,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "green", "value": None},
                        {"color": "yellow", "value": 10},
                        {"color": "red", "value": 15}
                    ]
                }
            }
        },
        "options": {
            "orientation": "vertical",
            "reduceOptions": {"values": False, "calcs": ["lastNotNull"]},
            "showThresholdLabels": True,
            "showThresholdMarkers": True
        }
    }
    dashboard["dashboard"]["panels"].append(pressure_panel)
    panel_id += 1
    
    # 4. Vibration Monitoring
    vibration_panel = {
        "id": panel_id,
        "type": "timeseries",
        "title": "Vibration Levels",
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 11},
        "targets": [
            {
                "refId": "A",
                "query": "SELECT mean(\"vibration\") FROM \"device_metrics\" WHERE $timeFilter GROUP BY time($__interval), \"device_name\" fill(null)",
                "datasource": {"type": "influxdb", "uid": "influxdb"},
            }
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "lengthmm",
                "custom": {
                    "axisLabel": "Vibration (mm/s)",
                    "drawStyle": "line",
                    "lineInterpolation": "smooth",
                    "lineWidth": 2,
                    "fillOpacity": 20,
                }
            }
        }
    }
    dashboard["dashboard"]["panels"].append(vibration_panel)
    panel_id += 1
    
    # 5. Device Status Table
    status_panel = {
        "id": panel_id,
        "type": "table",
        "title": "Device Status",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 19},
        "targets": [
            {
                "refId": "A",
                "query": "SELECT \"device_name\", last(\"temperature\") as temp, last(\"pressure\") as pressure, last(\"vibration\") as vibration, last(\"efficiency\") as efficiency FROM \"device_metrics\" WHERE $timeFilter GROUP BY \"device_name\"",
                "datasource": {"type": "influxdb", "uid": "influxdb"},
            }
        ],
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "align": "auto",
                    "displayMode": "auto",
                    "inspect": False
                }
            }
        },
        "options": {
            "showHeader": True,
            "footer": {"show": False}
        }
    }
    dashboard["dashboard"]["panels"].append(status_panel)
    
    return dashboard


def create_react_dashboard_component():
    """Create a React component for a custom dashboard."""
    
    react_code = """import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

// Mock data - in production, this would come from API
const mockDeviceData = [
  { name: 'Pump-001', temperature: 45, pressure: 7.2, vibration: 0.25, efficiency: 85, status: 'normal' },
  { name: 'Compressor-002', temperature: 55, pressure: 12.5, vibration: 0.42, efficiency: 78, status: 'warning' },
  { name: 'Fan-003', temperature: 32, pressure: 2.1, vibration: 0.15, efficiency: 92, status: 'normal' },
];

const timeSeriesData = [
  { time: '00:00', pump: 42, compressor: 52, fan: 30 },
  { time: '04:00', pump: 44, compressor: 55, fan: 31 },
  { time: '08:00', pump: 47, compressor: 58, fan: 33 },
  { time: '12:00', pump: 49, compressor: 62, fan: 35 },
  { time: '16:00', pump: 46, compressor: 59, fan: 32 },
  { time: '20:00', pump: 43, compressor: 54, fan: 30 },
];

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

export function IndustrialDashboard() {
  const [selectedDevice, setSelectedDevice] = useState('Pump-001');
  const [alerts, setAlerts] = useState([
    { id: 1, device: 'Compressor-002', message: 'Vibration level above threshold', severity: 'warning', timestamp: '2024-01-15 14:30' },
    { id: 2, device: 'Pump-001', message: 'Temperature rising trend detected', severity: 'info', timestamp: '2024-01-15 13:45' },
  ]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'normal': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'warning': return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case 'critical': return <XCircle className="h-4 w-4 text-red-500" />;
      default: return null;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'normal': return 'bg-green-100 text-green-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'critical': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Industrial Data Bridge</h1>
          <p className="text-muted-foreground">Real-time monitoring and predictive maintenance dashboard</p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className={getStatusColor('normal')}>
            <CheckCircle className="mr-1 h-3 w-3" />
            3 Devices Online
          </Badge>
          <Badge variant="outline" className={getStatusColor('warning')}>
            <AlertTriangle className="mr-1 h-3 w-3" />
            1 Warning
          </Badge>
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <Alert variant={alerts[0].severity === 'critical' ? 'destructive' : 'default'}>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {alerts[0].message} on {alerts[0].device}
          </AlertDescription>
        </Alert>
      )}

      {/* Main Dashboard Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Device Overview Card */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Device Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockDeviceData.map((device) => (
                <div
                  key={device.name}
                  className={`flex items-center justify-between p-4 rounded-lg border ${
                    device.status === 'warning' ? 'border-yellow-200 bg-yellow-50' : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-center space-x-4">
                    {getStatusIcon(device.status)}
                    <div>
                      <h3 className="font-medium">{device.name}</h3>
                      <p className="text-sm text-muted-foreground">Last updated: 2 min ago</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-6">
                    <div className="text-center">
                      <p className="text-sm text-muted-foreground">Temp</p>
                      <p className="font-semibold">{device.temperature}°C</p>
                    </div>
                    <div className="text-center">
                      <p className="text-sm text-muted-foreground">Pressure</p>
                      <p className="font-semibold">{device.pressure} bar</p>
                    </div>
                    <div className="text-center">
                      <p className="text-sm text-muted-foreground">Efficiency</p>
                      <p className="font-semibold">{device.efficiency}%</p>
                    </div>
                    <Badge className={getStatusColor(device.status)}>
                      {device.status.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Efficiency Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Efficiency Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={mockDeviceData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, efficiency }) => `${name}: ${efficiency}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="efficiency"
                >
                  {mockDeviceData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Temperature Time Series */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Temperature Trends (Last 24 Hours)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={timeSeriesData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis label={{ value: 'Temperature (°C)', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="pump" stroke="#8884d8" activeDot={{ r: 8 }} />
                <Line type="monotone" dataKey="compressor" stroke="#82ca9d" />
                <Line type="monotone" dataKey="fan" stroke="#ffc658" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Vibration Monitoring */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Vibration Levels</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={mockDeviceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis label={{ value: 'Vibration (mm/s)', angle: -90, position: 'insideLeft' }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="vibration" fill="#ff7300" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Key Metrics */}
        <Card>
          <CardHeader>
            <CardTitle>Key Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <p className="text-sm font-medium">Overall Efficiency</p>
                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-green-500" style={{ width: '78%' }} />
                </div>
                <p className="text-sm text-muted-foreground">78% - Within target range</p>
              </div>
              <div className="space-y-2">
                <p className="text-sm font-medium">Energy Consumption</p>
                <p className="text-2xl font-bold">1,245 kWh</p>
                <p className="text-sm text-muted-foreground">↓ 12% from last week</p>
              </div>
              <div className="space-y-2">
                <p className="text-sm font-medium">Uptime</p>
                <p className="text-2xl font-bold">99.7%</p>
                <p className="text-sm text-muted-foreground">Last downtime: 2 hours ago</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for Detailed Views */}
      <Tabs defaultValue="alerts" className="w-full">
        <TabsList>
          <TabsTrigger value="alerts">Alerts & Notifications</TabsTrigger>
          <TabsTrigger value="predictive">Predictive Insights</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
        </TabsList>
        <TabsContent value="alerts">
          <Card>
            <CardHeader>
              <CardTitle>Recent Alerts</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {alerts.map((alert) => (
                  <div key={alert.id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center space-x-4">
                      {getStatusIcon(alert.severity)}
                      <div>
                        <p className="font-medium">{alert.message}</p>
                        <p className="text-sm text-muted-foreground">{alert.device} • {alert.timestamp}</p>
                      </div>
                    </div>
                    <Badge className={getStatusColor(alert.severity)}>
                      {alert.severity.toUpperCase()}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        <TabsContent value="predictive">
          <Card>
            <CardHeader>
              <CardTitle>Predictive Maintenance Insights</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h4 className="font-medium text-blue-800">Compressor-002 Maintenance Due</h4>
                  <p className="text-sm text-blue-600">Estimated RUL: 240 hours • Recommended action: Schedule bearing inspection</p>
                </div>
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <h4 className="font-medium text-yellow-800">Pump-001 Efficiency Decline</h4>
                  <p className="text-sm text-yellow-600">Efficiency dropped 5% in last week • Check for cavitation</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
"""
    
    return react_code


async def main():
    """Main dashboard example."""
    logger.info("Starting Dashboard and Visualization example...")
    
    # 1. Generate sample data
    logger.info("1. Generating sample data...")
    sample_data = generate_sample_data(days=7, devices=3)
    logger.info(f"Generated {len(sample_data)} data points")
    
    # Save sample data to JSON
    data_file = Path(__file__).parent / "sample_data.json"
    with open(data_file, "w") as f:
        json.dump(sample_data, f, indent=2, default=str)
    logger.info(f"Sample data saved to {data_file}")
    
    # 2. Create Grafana dashboard
    logger.info("2. Creating Grafana dashboard...")
    devices = [
        {"id": "device_001", "name": "Pump-001", "type": "pump"},
        {"id": "device_002", "name": "Compressor-002", "type": "compressor"},
        {"id": "device_003", "name": "Fan-003", "type": "fan"},
    ]
    
    grafana_dashboard = create_grafana_dashboard(devices)
    
    # Save Grafana dashboard
    dashboard_file = Path(__file__).parent / "grafana_dashboard.json"
    with open(dashboard_file, "w") as f:
        json.dump(grafana_dashboard, f, indent=2)
    logger.info(f"Grafana dashboard saved to {dashboard_file}")
    
    # 3. Create React dashboard component
    logger.info("3. Creating React dashboard component...")
    react_component = create_react_dashboard_component()
    
    # Save React component
    react_file = Path(__file__).parent / "IndustrialDashboard.jsx"
    with open(react_file, "w") as f:
        f.write(react_component)
    logger.info(f"React component saved to {react_file}")
    
    # 4. Demonstrate data normalization for dashboard
    logger.info("4. Demonstrating data normalization...")
    normalizer = DataNormalizer(default_unit="celsius")
    
    # Normalize sample points
    sample_points = [
        {"name": "temp1", "value": 77, "unit": "fahrenheit"},
        {"name": "temp2", "value": 25, "unit": "celsius"},
        {"name": "pressure1", "value": 500, "unit": "kpa"},
    ]
    
    normalized = normalizer.normalize_points(
        points=sample_points,
        config={"data_type": "float", "target_unit": "celsius"}
    )
    
    logger.info("Normalized data:")
    for point in normalized:
        logger.info(f"  {point['name']}: {point['value']} {point['unit']} ({point['quality']})")
    
    # 5. Create summary statistics
    logger.info("5. Creating summary statistics...")
    
    # Group by device
    device_stats = {}
    for point in sample_data:
        device_id = point["device_id"]
        if device_id not in device_stats:
            device_stats[device_id] = {
                "name": point["device_name"],
                "type": point["device_type"],
                "temperatures": [],
                "pressures": [],
                "vibrations": [],
                "efficiencies": [],
            }
        
        device_stats[device_id]["temperatures"].append(point["temperature"])
        device_stats[device_id]["pressures"].append(point["pressure"])
        device_stats[device_id]["vibrations"].append(point["vibration"])
        device_stats[device_id]["efficiencies"].append(point["efficiency"])
    
    # Calculate statistics
    summary_stats = []
    for device_id, stats in device_stats.items():
        summary = {
            "device": stats["name"],
            "type": stats["type"],
            "avg_temperature": round(sum(stats["temperatures"]) / len(stats["temperatures"]), 1),
            "max_temperature": round(max(stats["temperatures"]), 1),
            "avg_pressure": round(sum(stats["pressures"]) / len(stats["pressures"]), 1),
            "avg_vibration": round(sum(stats["vibrations"]) / len(stats["vibrations"]), 2),
            "avg_efficiency": round(sum(stats["efficiencies"]) / len(stats["efficiencies"]), 1),
        }
        summary_stats.append(summary)
    
    # Save statistics
    stats_file = Path(__file__).parent / "summary_statistics.json"
    with open(stats_file, "w") as f:
        json.dump(summary_stats, f, indent=2)
    
    logger.info("Summary statistics:")
    for stats in summary_stats:
        logger.info(f"  {stats['device']}:")
        logger.info(f"    Type: {stats['type']}")
        logger.info(f"    Avg Temp: {stats['avg_temperature']}°C")
        logger.info(f"    Max Temp: {stats['max_temperature']}°C")
        logger.info(f"    Avg Pressure: {stats['avg_pressure']} bar")
        logger.info(f"    Avg Vibration: {stats['avg_vibration']} mm/s")
        logger.info(f"    Avg Efficiency: {stats['avg_efficiency']}%")
    
    logger.info("Dashboard and Visualization example completed!")
    logger.info(f"Generated files:")
    logger.info(f"  - {data_file} (Sample data)")
    logger.info(f"  - {dashboard_file} (Grafana dashboard)")
    logger.info(f"  - {react_file} (React component)")
    logger.info(f"  - {stats_file} (Summary statistics)")


if __name__ == "__main__":
    asyncio.run(main())