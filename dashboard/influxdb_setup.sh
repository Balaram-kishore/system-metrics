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