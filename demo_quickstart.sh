#!/bin/bash

# Quick Start Demo Script for System Metrics Collection
# This script sets up and runs the complete demo environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# Check if running as root for system installations
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root. This is required for system package installation."
    fi
}

# Check prerequisites
check_prerequisites() {
    print_header "🔍 Checking Prerequisites..."
    
    # Check if Python 3 is installed
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8 or later."
        exit 1
    fi
    
    # Check if pip is installed
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed. Please install pip3."
        exit 1
    fi
    
    # Check if curl is installed
    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed. Please install curl."
        exit 1
    fi
    
    print_status "✅ Prerequisites check passed"
}

# Install system dependencies
install_dependencies() {
    print_header "📦 Installing System Dependencies..."
    
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        sudo apt-get update
        sudo apt-get install -y python3-venv python3-pip curl wget jq
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        sudo yum install -y python3-venv python3-pip curl wget jq
    else
        print_warning "Unknown package manager. Please install python3-venv, curl, wget, and jq manually."
    fi
}

# Setup Python environment
setup_python_env() {
    print_header "🐍 Setting up Python Environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_status "Created Python virtual environment"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install project dependencies
    print_status "Installing project dependencies..."
    pip install -r metric_collector/requirements.txt
    pip install -r cloud_ingestion/requirements.txt
    pip install influxdb-client pyyaml
    
    print_status "✅ Python environment setup complete"
}

# Check if InfluxDB is running
check_influxdb() {
    print_header "🔍 Checking InfluxDB..."
    
    if curl -s http://localhost:8086/ping > /dev/null; then
        print_status "✅ InfluxDB is running"
        return 0
    else
        print_warning "InfluxDB is not running or not installed"
        return 1
    fi
}

# Check if Grafana is running
check_grafana() {
    print_header "🔍 Checking Grafana..."
    
    if curl -s http://localhost:3000/api/health > /dev/null; then
        print_status "✅ Grafana is running"
        return 0
    else
        print_warning "Grafana is not running or not installed"
        return 1
    fi
}

# Start metrics ingestion server
start_ingestion_server() {
    print_header "🚀 Starting Metrics Ingestion Server..."
    
    # Check if already running
    if curl -s http://localhost:8000/health > /dev/null; then
        print_status "Metrics ingestion server is already running"
        return 0
    fi
    
    # Start server in background
    source venv/bin/activate
    nohup python cloud_ingestion/server.py --host 0.0.0.0 --port 8000 > logs/ingestion.log 2>&1 &
    INGESTION_PID=$!
    echo $INGESTION_PID > .ingestion.pid
    
    # Wait for server to start
    print_status "Waiting for ingestion server to start..."
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null; then
            print_status "✅ Metrics ingestion server started (PID: $INGESTION_PID)"
            return 0
        fi
        sleep 1
    done
    
    print_error "Failed to start metrics ingestion server"
    return 1
}

# Start metrics collector
start_collector() {
    print_header "📊 Starting Metrics Collector..."
    
    # Create logs directory
    mkdir -p logs
    
    # Start collector in background
    source venv/bin/activate
    nohup python metric_collector/collector.py --config metric_collector/config.yaml > logs/collector.log 2>&1 &
    COLLECTOR_PID=$!
    echo $COLLECTOR_PID > .collector.pid
    
    print_status "✅ Metrics collector started (PID: $COLLECTOR_PID)"
    print_status "Logs: tail -f logs/collector.log"
}

# Show status
show_status() {
    print_header "📊 System Status"
    echo "=================="
    
    # Check services
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✅ Metrics API: http://localhost:8000"
    else
        echo "❌ Metrics API: Not running"
    fi
    
    if check_influxdb; then
        echo "✅ InfluxDB: http://localhost:8086"
    else
        echo "❌ InfluxDB: Not running"
    fi
    
    if check_grafana; then
        echo "✅ Grafana: http://localhost:3000"
    else
        echo "❌ Grafana: Not running"
    fi
    
    echo ""
    echo "📁 Log files:"
    echo "   Ingestion: logs/ingestion.log"
    echo "   Collector: logs/collector.log"
    echo ""
    echo "🎮 Demo commands:"
    echo "   Generate load: python3 demo-scripts/load_generator.py"
    echo "   View metrics: curl http://localhost:8000/metrics | jq"
    echo "   Stop services: ./demo_quickstart.sh stop"
}

# Stop services
stop_services() {
    print_header "🛑 Stopping Services..."
    
    # Stop collector
    if [ -f .collector.pid ]; then
        COLLECTOR_PID=$(cat .collector.pid)
        if kill -0 $COLLECTOR_PID 2>/dev/null; then
            kill $COLLECTOR_PID
            print_status "Stopped metrics collector (PID: $COLLECTOR_PID)"
        fi
        rm -f .collector.pid
    fi
    
    # Stop ingestion server
    if [ -f .ingestion.pid ]; then
        INGESTION_PID=$(cat .ingestion.pid)
        if kill -0 $INGESTION_PID 2>/dev/null; then
            kill $INGESTION_PID
            print_status "Stopped ingestion server (PID: $INGESTION_PID)"
        fi
        rm -f .ingestion.pid
    fi
    
    print_status "✅ Services stopped"
}

# Main function
main() {
    case "${1:-start}" in
        "start")
            print_header "🚀 Starting System Metrics Demo"
            check_prerequisites
            setup_python_env
            start_ingestion_server
            sleep 2
            start_collector
            sleep 2
            show_status
            
            echo ""
            print_header "🎉 Demo Setup Complete!"
            echo ""
            echo "Next steps:"
            echo "1. Set up InfluxDB: ./dashboard/influxdb_setup.sh"
            echo "2. Configure Grafana data source"
            echo "3. Import dashboard: dashboard/grafana_dashboard.json"
            echo "4. Generate load: python3 demo-scripts/load_generator.py"
            ;;
        "stop")
            stop_services
            ;;
        "status")
            show_status
            ;;
        "restart")
            stop_services
            sleep 2
            main start
            ;;
        *)
            echo "Usage: $0 {start|stop|status|restart}"
            echo ""
            echo "Commands:"
            echo "  start   - Start all services"
            echo "  stop    - Stop all services"
            echo "  status  - Show service status"
            echo "  restart - Restart all services"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
