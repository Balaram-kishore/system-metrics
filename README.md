# System Metrics Collection with InfluxDB & Grafana

## 📋 Overview
This guide provides a complete walkthrough for demonstrating the system metrics collection project on a Linux Ubuntu EC2 machine with InfluxDB for metrics storage and Grafana for dashboard visualization.

## 🏗️ Architecture Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   EC2 Instance  │    │  Metrics API    │    │    InfluxDB     │    │     Grafana     │
│                 │    │                 │    │                 │    │                 │
│ Metrics         │───▶│ FastAPI Server  │───▶│ Time Series DB  │───▶│ Dashboard UI    │
│ Collector       │    │ (Port 8000)     │    │ (Port 8086)     │    │ (Port 3000)     │
│                 │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🎯 Prerequisites

### EC2 Instance Requirements
- **Instance Type**: t3.medium or larger (2 vCPU, 4GB RAM minimum)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 20GB+ EBS volume
- **Security Groups**: 
  - SSH (22) - Your IP
  - HTTP (80) - 0.0.0.0/0
  - Custom TCP (3000) - 0.0.0.0/0 (Grafana)
  - Custom TCP (8000) - 0.0.0.0/0 (API)
  - Custom TCP (8086) - 0.0.0.0/0 (InfluxDB)

## 🚀 Step-by-Step Demo Setup

### Step 1: Initial EC2 Setup

```bash
# Connect to your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-public-ip

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y git curl wget python3 python3-pip python3-venv \
    build-essential software-properties-common apt-transport-https \
    ca-certificates gnupg lsb-release
```

### Step 2: Install InfluxDB 2.x

```bash
# Add InfluxDB repository
wget -q https://repos.influxdata.com/influxdata-archive_compat.key
echo '393e8779c89ac8d958f81f942f9ad7fb82a25e133fddaf92e7b9f8857e81b6b1 influxdata-archive_compat.key' | sha256sum -c && cat influxdata-archive_compat.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg > /dev/null
echo 'deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg] https://repos.influxdata.com/debian stable main' | sudo tee /etc/apt/sources.list.d/influxdata.list

# Install InfluxDB
sudo apt update
sudo apt install -y influxdb2

# Start and enable InfluxDB
sudo systemctl start influxdb
sudo systemctl enable influxdb

# Verify InfluxDB is running
sudo systemctl status influxdb
curl -I http://localhost:8086/ping
```

### Step 3: Install Grafana

```bash
# Add Grafana repository
sudo mkdir -p /etc/apt/keyrings/
wget -q -O - https://apt.grafana.com/gpg.key | gpg --dearmor | sudo tee /etc/apt/keyrings/grafana.gpg > /dev/null
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list

# Install Grafana
sudo apt update
sudo apt install -y grafana

# Start and enable Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server

# Verify Grafana is running
sudo systemctl status grafana-server
```

### Step 4: Setup InfluxDB

```bash
# Initialize InfluxDB (run this once)
influx setup \
  --username admin \
  --password your-secure-password \
  --org metrics-org \
  --bucket system-metrics \
  --retention 30d \
  --force

# Create API token for metrics ingestion
influx auth create \
  --org metrics-org \
  --all-access \
  --description "Metrics Collector Token"

# Note: Save the token output - you'll need it later
```

### Step 5: Clone and Setup Metrics Project

```bash
# Clone the project
cd /home/ubuntu
git clone https://github.com/Balaram-kishore/system-metrics.git
cd system-metrics-final

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r metric_collector/requirements.txt
pip install -r cloud_ingestion/requirements.txt
pip install -r dashboard/requirements.txt
pip install influxdb-client  # Add InfluxDB client
```

### Step 6: Configure InfluxDB Integration

Create InfluxDB configuration file:

```bash
# Create InfluxDB config
cat > influxdb_config.yaml << 'EOF'
influxdb:
  url: "http://localhost:8086"
  token: "YOUR_INFLUXDB_TOKEN_HERE"  # Replace with actual token
  org: "metrics-org"
  bucket: "system-metrics"
  timeout: 10
EOF
```

### Step 7: Demo Script Preparation

Create demo scripts for the presentation:

```bash
# Create demo directory
mkdir -p demo-scripts

# Create system load generator for demo
cat > demo-scripts/load_generator.py << 'EOF'
#!/usr/bin/env python3
"""
System Load Generator for Demo
Generates CPU, memory, and disk load for demonstration purposes
"""
import time
import threading
import os
import random
from multiprocessing import Process, cpu_count

def cpu_load(duration=60):
    """Generate CPU load"""
    end_time = time.time() + duration
    while time.time() < end_time:
        # Busy wait to consume CPU
        pass

def memory_load(size_mb=100, duration=60):
    """Generate memory load"""
    data = []
    end_time = time.time() + duration
    while time.time() < end_time:
        # Allocate memory in chunks
        chunk = 'x' * (1024 * 1024)  # 1MB chunk
        data.append(chunk)
        if len(data) > size_mb:
            data.pop(0)
        time.sleep(0.1)

def disk_load(duration=60):
    """Generate disk I/O load"""
    end_time = time.time() + duration
    while time.time() < end_time:
        # Write and read files
        with open('/tmp/demo_load_file', 'w') as f:
            f.write('x' * 1024 * 1024)  # 1MB
        with open('/tmp/demo_load_file', 'r') as f:
            f.read()
        os.remove('/tmp/demo_load_file')
        time.sleep(0.5)

if __name__ == "__main__":
    print("🔥 Starting system load generation for demo...")
    
    # Start CPU load on multiple cores
    cpu_processes = []
    for i in range(min(4, cpu_count())):
        p = Process(target=cpu_load, args=(120,))
        p.start()
        cpu_processes.append(p)
    
    # Start memory load
    memory_thread = threading.Thread(target=memory_load, args=(200, 120))
    memory_thread.start()
    
    # Start disk load
    disk_thread = threading.Thread(target=disk_load, args=(120,))
    disk_thread.start()
    
    print("✅ Load generation started. Will run for 2 minutes...")
    print("📊 Monitor the dashboard to see metrics change!")
    
    # Wait for completion
    for p in cpu_processes:
        p.join()
    memory_thread.join()
    disk_thread.join()
    
    print("🏁 Load generation completed!")
EOF

chmod +x demo-scripts/load_generator.py
```

### Step 8: Create InfluxDB Integration Module

```bash
# Create InfluxDB integration
cat > cloud_ingestion/influxdb_writer.py << 'EOF'
#!/usr/bin/env python3
"""
InfluxDB Writer Module
Handles writing metrics data to InfluxDB
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import yaml

logger = logging.getLogger(__name__)

class InfluxDBWriter:
    def __init__(self, config_path: str = "influxdb_config.yaml"):
        """Initialize InfluxDB writer with configuration."""
        self.config = self._load_config(config_path)
        self.client = None
        self.write_api = None
        self._connect()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load InfluxDB configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config['influxdb']
        except Exception as e:
            logger.error(f"Failed to load InfluxDB config: {e}")
            raise

    def _connect(self):
        """Establish connection to InfluxDB."""
        try:
            self.client = InfluxDBClient(
                url=self.config['url'],
                token=self.config['token'],
                org=self.config['org'],
                timeout=self.config.get('timeout', 10) * 1000
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            logger.info("Connected to InfluxDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise

    def write_metrics(self, hostname: str, metrics: Dict[str, Any]) -> bool:
        """Write system metrics to InfluxDB."""
        try:
            points = []
            timestamp = datetime.fromisoformat(metrics['timestamp'].replace('Z', '+00:00'))

            # CPU metrics
            cpu_point = Point("cpu") \
                .tag("hostname", hostname) \
                .field("percent", float(metrics['cpu']['percent'])) \
                .field("count", int(metrics['cpu']['count'])) \
                .field("count_logical", int(metrics['cpu']['count_logical'])) \
                .time(timestamp)
            points.append(cpu_point)

            # Memory metrics
            memory_point = Point("memory") \
                .tag("hostname", hostname) \
                .field("total", int(metrics['memory']['total'])) \
                .field("available", int(metrics['memory']['available'])) \
                .field("percent", float(metrics['memory']['percent'])) \
                .field("used", int(metrics['memory']['used'])) \
                .field("free", int(metrics['memory']['free'])) \
                .time(timestamp)
            points.append(memory_point)

            # Swap metrics
            swap_point = Point("swap") \
                .tag("hostname", hostname) \
                .field("total", int(metrics['swap']['total'])) \
                .field("used", int(metrics['swap']['used'])) \
                .field("free", int(metrics['swap']['free'])) \
                .field("percent", float(metrics['swap']['percent'])) \
                .time(timestamp)
            points.append(swap_point)

            # Disk metrics
            for disk in metrics['disk']:
                disk_point = Point("disk") \
                    .tag("hostname", hostname) \
                    .tag("device", disk['device']) \
                    .tag("mountpoint", disk['mountpoint']) \
                    .tag("fstype", disk['fstype']) \
                    .field("total", int(disk['total'])) \
                    .field("used", int(disk['used'])) \
                    .field("free", int(disk['free'])) \
                    .field("percent", float(disk['percent'])) \
                    .time(timestamp)
                points.append(disk_point)

            # Network metrics (if available)
            if metrics.get('network'):
                network_point = Point("network") \
                    .tag("hostname", hostname) \
                    .field("bytes_sent", int(metrics['network']['bytes_sent'])) \
                    .field("bytes_recv", int(metrics['network']['bytes_recv'])) \
                    .field("packets_sent", int(metrics['network']['packets_sent'])) \
                    .field("packets_recv", int(metrics['network']['packets_recv'])) \
                    .time(timestamp)
                points.append(network_point)

            # Write all points to InfluxDB
            self.write_api.write(
                bucket=self.config['bucket'],
                org=self.config['org'],
                record=points
            )

            logger.debug(f"Successfully wrote {len(points)} metric points to InfluxDB")
            return True

        except Exception as e:
            logger.error(f"Failed to write metrics to InfluxDB: {e}")
            return False

    def close(self):
        """Close InfluxDB connection."""
        if self.client:
            self.client.close()
            logger.info("InfluxDB connection closed")
EOF
```

### Step 9: Update Metrics Server for InfluxDB Integration

```bash
# Backup original server
cp cloud_ingestion/server.py cloud_ingestion/server_original.py

# Update server.py to include InfluxDB writing
cat >> cloud_ingestion/server.py << 'EOF'

# Add InfluxDB integration
try:
    from .influxdb_writer import InfluxDBWriter
    influxdb_writer = InfluxDBWriter()
    INFLUXDB_ENABLED = True
    logger.info("InfluxDB integration enabled")
except Exception as e:
    logger.warning(f"InfluxDB integration disabled: {e}")
    INFLUXDB_ENABLED = False

# Update the ingest endpoint to also write to InfluxDB
@app.post("/ingest")
async def ingest_metrics(
    payload: MetricsPayload,
    background_tasks: BackgroundTasks,
    db: MetricsDatabase = Depends(get_database)
):
    """Ingest metrics from collectors."""
    try:
        # Store metrics in SQLite (existing functionality)
        success = db.store_metrics(payload)

        # Also write to InfluxDB if enabled
        if INFLUXDB_ENABLED:
            try:
                influxdb_success = influxdb_writer.write_metrics(
                    payload.hostname,
                    payload.metrics.dict()
                )
                if influxdb_success:
                    logger.debug(f"Metrics written to InfluxDB for {payload.hostname}")
            except Exception as e:
                logger.error(f"Failed to write to InfluxDB: {e}")
                # Don't fail the request if InfluxDB write fails

        if success:
            logger.info(f"Received metrics from {payload.hostname}")
            return {"status": "success", "message": "Metrics stored successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to store metrics")

    except Exception as e:
        logger.error(f"Error processing metrics: {e}")
        raise HTTPException(status_code=400, detail=str(e))
EOF
```

### Step 10: Create Grafana Dashboard Configuration

```bash
# Create Grafana dashboard JSON
cat > dashboard/grafana_dashboard.json << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "System Metrics Dashboard",
    "tags": ["system", "metrics", "monitoring"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "CPU Usage",
        "type": "stat",
        "targets": [
          {
            "query": "from(bucket: \"system-metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"cpu\")\n  |> filter(fn: (r) => r[\"_field\"] == \"percent\")\n  |> last()",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100,
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 70},
                {"color": "red", "value": 90}
              ]
            }
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Memory Usage",
        "type": "stat",
        "targets": [
          {
            "query": "from(bucket: \"system-metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"memory\")\n  |> filter(fn: (r) => r[\"_field\"] == \"percent\")\n  |> last()",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100,
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 70},
                {"color": "red", "value": 90}
              ]
            }
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 6, "y": 0}
      },
      {
        "id": 3,
        "title": "Disk Usage",
        "type": "stat",
        "targets": [
          {
            "query": "from(bucket: \"system-metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"disk\")\n  |> filter(fn: (r) => r[\"_field\"] == \"percent\")\n  |> filter(fn: (r) => r[\"mountpoint\"] == \"/\")\n  |> last()",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100,
            "thresholds": {
              "steps": [
                {"color": "green", "value": null},
                {"color": "yellow", "value": 80},
                {"color": "red", "value": 95}
              ]
            }
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 0}
      },
      {
        "id": 4,
        "title": "Network I/O",
        "type": "stat",
        "targets": [
          {
            "query": "from(bucket: \"system-metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"network\")\n  |> filter(fn: (r) => r[\"_field\"] == \"bytes_sent\" or r[\"_field\"] == \"bytes_recv\")\n  |> last()",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "bytes"
          }
        },
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
      },
      {
        "id": 5,
        "title": "CPU Usage Over Time",
        "type": "timeseries",
        "targets": [
          {
            "query": "from(bucket: \"system-metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"cpu\")\n  |> filter(fn: (r) => r[\"_field\"] == \"percent\")\n  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100
          }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 6,
        "title": "Memory Usage Over Time",
        "type": "timeseries",
        "targets": [
          {
            "query": "from(bucket: \"system-metrics\")\n  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)\n  |> filter(fn: (r) => r[\"_measurement\"] == \"memory\")\n  |> filter(fn: (r) => r[\"_field\"] == \"percent\")\n  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100
          }
        },
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "5s"
  }
}
EOF
```

### Step 11: Create InfluxDB Setup Script

```bash
# Create comprehensive InfluxDB setup script
cat > dashboard/influxdb_setup.sh << 'EOF'
#!/bin/bash

# InfluxDB Setup Script for System Metrics
# This script sets up InfluxDB for the metrics collection system

set -e

# Configuration
INFLUX_ORG="metrics-org"
INFLUX_BUCKET="system-metrics"
INFLUX_USERNAME="admin"
INFLUX_RETENTION="30d"

echo "🚀 Setting up InfluxDB for System Metrics..."

# Check if InfluxDB is running
if ! curl -s http://localhost:8086/ping > /dev/null; then
    echo "❌ InfluxDB is not running. Please start it first:"
    echo "   sudo systemctl start influxdb"
    exit 1
fi

echo "✅ InfluxDB is running"

# Check if already initialized
if influx org list > /dev/null 2>&1; then
    echo "⚠️  InfluxDB appears to be already initialized"
    echo "📋 Existing organizations:"
    influx org list

    read -p "Do you want to continue and create/update the metrics setup? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled"
        exit 0
    fi
else
    # Initial setup
    echo "🔧 Initializing InfluxDB..."
    read -s -p "Enter password for admin user: " INFLUX_PASSWORD
    echo

    influx setup \
        --username "$INFLUX_USERNAME" \
        --password "$INFLUX_PASSWORD" \
        --org "$INFLUX_ORG" \
        --bucket "$INFLUX_BUCKET" \
        --retention "$INFLUX_RETENTION" \
        --force

    echo "✅ InfluxDB initialized successfully"
fi

# Create API token for metrics ingestion
echo "🔑 Creating API token for metrics ingestion..."
TOKEN=$(influx auth create \
    --org "$INFLUX_ORG" \
    --all-access \
    --description "Metrics Collector Token" \
    --json | jq -r '.token')

if [ -n "$TOKEN" ]; then
    echo "✅ API token created successfully"
    echo "📝 Token: $TOKEN"

    # Update configuration file
    cat > ../influxdb_config.yaml << EOL
influxdb:
  url: "http://localhost:8086"
  token: "$TOKEN"
  org: "$INFLUX_ORG"
  bucket: "$INFLUX_BUCKET"
  timeout: 10
EOL

    echo "✅ Configuration file updated: ../influxdb_config.yaml"
else
    echo "❌ Failed to create API token"
    exit 1
fi

echo ""
echo "🎉 InfluxDB setup completed successfully!"
echo ""
echo "📊 Next steps:"
echo "1. Start the metrics collector: python metric_collector/collector.py"
echo "2. Start the ingestion server: python cloud_ingestion/server.py"
echo "3. Configure Grafana data source with the token above"
echo "4. Import the dashboard from grafana_dashboard.json"
echo ""
echo "🔗 Access URLs:"
echo "   InfluxDB UI: http://localhost:8086"
echo "   Grafana: http://localhost:3000"
echo "   Metrics API: http://localhost:8000"
EOF

chmod +x dashboard/influxdb_setup.sh
```

## 🎬 Live Demo Execution

### Phase 1: Environment Setup (5 minutes)

```bash
# 1. Show the EC2 instance and architecture
echo "🏗️ System Architecture Overview"
echo "================================"
echo "EC2 Instance: $(curl -s http://169.254.169.254/latest/meta-data/instance-type)"
echo "Public IP: $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "OS: $(lsb_release -d | cut -f2)"
echo "CPU Cores: $(nproc)"
echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $2}')"

# 2. Show services status
echo -e "\n📊 Service Status"
echo "=================="
sudo systemctl status influxdb --no-pager -l
sudo systemctl status grafana-server --no-pager -l

# 3. Verify connectivity
echo -e "\n🔗 Service Connectivity"
echo "======================="
echo "InfluxDB: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:8086/ping)"
echo "Grafana: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health)"
```

### Phase 2: InfluxDB Configuration (3 minutes)

```bash
# Run InfluxDB setup
cd dashboard
./influxdb_setup.sh

# Show InfluxDB UI
echo "🌐 Opening InfluxDB UI..."
echo "URL: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8086"
```

### Phase 3: Start Metrics Collection (2 minutes)

```bash
# Terminal 1: Start InfluxDB-enabled ingestion server
cd /home/ubuntu/system-metrics-final
source venv/bin/activate

# Update the server to use InfluxDB
python cloud_ingestion/server.py --host 0.0.0.0 --port 8000

# Terminal 2: Start metrics collector
cd /home/ubuntu/system-metrics-final
source venv/bin/activate
python metric_collector/collector.py --config metric_collector/config.yaml --verbose

# Terminal 3: Monitor logs
tail -f logs/metrics_collector.log
```

### Phase 4: Grafana Dashboard Setup (5 minutes)

```bash
# 1. Access Grafana
echo "🌐 Opening Grafana..."
echo "URL: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):3000"
echo "Default credentials: admin/admin"

# 2. Configure InfluxDB data source in Grafana UI:
#    - Go to Configuration > Data Sources
#    - Add InfluxDB data source
#    - URL: http://localhost:8086
#    - Database: system-metrics
#    - User: admin
#    - Password: [your-password]
#    - HTTP Method: GET

# 3. Import dashboard
#    - Go to + > Import
#    - Upload grafana_dashboard.json
#    - Select InfluxDB data source
```

### Phase 5: Live Metrics Demonstration (10 minutes)

```bash
# 1. Show baseline metrics
echo "📊 Current System Metrics"
echo "========================"
echo "CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "Memory: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
echo "Disk: $(df / | tail -1 | awk '{print $5}')"

# 2. Generate system load for demonstration
echo "🔥 Starting load generation..."
python3 demo-scripts/load_generator.py &
LOAD_PID=$!

# 3. Monitor in real-time
echo "📈 Watch the dashboard update in real-time!"
echo "🌐 Dashboard: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):3000"

# 4. Show API endpoints
echo -e "\n🔗 API Endpoints:"
echo "Health: curl http://localhost:8000/health"
echo "Metrics: curl http://localhost:8000/metrics | jq"
echo "Summary: curl http://localhost:8000/metrics/summary | jq"

# 5. Demonstrate alerts (if thresholds are exceeded)
echo -e "\n🚨 Alert Monitoring:"
tail -f logs/metrics_collector.log | grep -i alert

# Wait for load generation to complete
wait $LOAD_PID
echo "✅ Load generation completed"
```

### Phase 6: Data Analysis & Queries (5 minutes)

```bash
# Show InfluxDB queries
echo "📊 InfluxDB Query Examples"
echo "========================="

# Example queries to run in InfluxDB UI or CLI
cat << 'EOF'
// Average CPU usage over last hour
from(bucket: "system-metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "cpu")
  |> filter(fn: (r) => r["_field"] == "percent")
  |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)

// Memory usage trend
from(bucket: "system-metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "memory")
  |> filter(fn: (r) => r["_field"] == "percent")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)

// Disk usage by mount point
from(bucket: "system-metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "disk")
  |> filter(fn: (r) => r["_field"] == "percent")
  |> group(columns: ["mountpoint"])
  |> last()

// Network I/O rates
from(bucket: "system-metrics")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "network")
  |> filter(fn: (r) => r["_field"] == "bytes_sent" or r["_field"] == "bytes_recv")
  |> derivative(every: 1m, nonNegative: true)
EOF
```

## 🎯 Demo Script & Talking Points

### Opening (2 minutes)
- "Today I'll demonstrate a comprehensive system metrics collection solution"
- "Architecture: EC2 → Metrics Collector → FastAPI → InfluxDB → Grafana"
- "Real-time monitoring with historical data analysis and alerting"

### Technical Highlights (8 minutes)
- **Scalability**: "Designed for production with systemd services"
- **Reliability**: "Built-in retry logic and error handling"
- **Flexibility**: "Configurable collection intervals and thresholds"
- **Performance**: "Efficient time-series storage with InfluxDB"
- **Visualization**: "Professional dashboards with Grafana"

### Live Demo Points (15 minutes)
1. **Show baseline metrics** - "Current system is running normally"
2. **Generate load** - "Let's stress test the system"
3. **Real-time updates** - "Watch metrics change in real-time"
4. **Alert demonstration** - "System automatically detects issues"
5. **Historical analysis** - "Query trends and patterns"

### Closing (5 minutes)
- **Production readiness**: "Ready for deployment with Docker/systemd"
- **Monitoring capabilities**: "Complete observability stack"
- **Extensibility**: "Easy to add new metrics and alerts"
- **Cost effectiveness**: "Open source solution on AWS"

## 🔧 Troubleshooting Guide

### Common Issues

1. **InfluxDB Connection Failed**
   ```bash
   # Check InfluxDB status
   sudo systemctl status influxdb

   # Check logs
   sudo journalctl -u influxdb -f

   # Restart if needed
   sudo systemctl restart influxdb
   ```

2. **Grafana Not Accessible**
   ```bash
   # Check Grafana status
   sudo systemctl status grafana-server

   # Check port binding
   sudo netstat -tlnp | grep :3000

   # Check security group allows port 3000
   ```

3. **Metrics Not Appearing**
   ```bash
   # Check collector logs
   tail -f logs/metrics_collector.log

   # Test API endpoint
   curl -X POST http://localhost:8000/ingest \
     -H "Content-Type: application/json" \
     -d '{"test": "data"}'

   # Check InfluxDB data
   influx query 'from(bucket:"system-metrics") |> range(start:-1h) |> limit(n:10)'
   ```

4. **High Resource Usage**
   ```bash
   # Adjust collection interval
   # Edit metric_collector/config.yaml
   interval_seconds: 60  # Increase from 30 to 60 seconds

   # Reduce metric scope
   metrics:
     include_network: false
     include_processes: false
   ```

## 📚 Additional Resources

- **InfluxDB Documentation**: https://docs.influxdata.com/
- **Grafana Documentation**: https://grafana.com/docs/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **AWS EC2 Documentation**: https://docs.aws.amazon.com/ec2/

## 🎉 Demo Success Checklist

- [ ] EC2 instance running and accessible
- [ ] InfluxDB installed and configured
- [ ] Grafana installed and accessible
- [ ] Metrics collector running and sending data
- [ ] Dashboard showing real-time metrics
- [ ] Load generation demonstrates system response
- [ ] Alerts working when thresholds exceeded
- [ ] Historical data queries functional
- [ ] All services stable and performant

---

**🚀 Ready for your live demo! This comprehensive setup showcases a production-ready monitoring solution with modern time-series database and visualization tools.**
