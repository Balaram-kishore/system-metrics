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
cd system-metrics

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




### Step 7: Create InfluxDB Setup Script

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

#Execution

### Phase 1: Environment Setup (5 minutes)


echo "CPU Cores: $(nproc)"
echo "Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "Disk: $(df -h / | tail -1 | awk '{print $2}')"

# 2. Show services status

sudo systemctl status influxdb --no-pager -l
sudo systemctl status grafana-server --no-pager -l

# 3. Verify connectivity

echo "InfluxDB: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:8086/ping)"
echo "Grafana: $(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health)"


### Phase 2: InfluxDB Configuration (3 minutes)

```bash
# Run InfluxDB setup
cd dashboard
./influxdb_setup.sh

### Phase 3: Start Metrics Collection (2 minutes)

```bash
# Terminal 1: Start InfluxDB-enabled ingestion server
cd /home/ubuntu/system-metrics
source venv/bin/activate

# Update the server to use InfluxDB
python cloud_ingestion/server.py --host 0.0.0.0 --port 8000

# Terminal 2: Start metrics collector
cd /home/ubuntu/system-metrics
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


