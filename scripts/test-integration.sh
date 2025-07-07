#!/bin/bash

# Integration Test Script for Metrics Collector
# This script runs comprehensive integration tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Test configuration
TEST_INGESTION_PORT=8001
TEST_DASHBOARD_PORT=8081
TEST_TIMEOUT=60

# Process tracking
INGESTION_PID=""
DASHBOARD_PID=""

# Cleanup function
cleanup() {
    log_info "Cleaning up test processes..."
    
    if [[ -n "$INGESTION_PID" ]]; then
        kill $INGESTION_PID 2>/dev/null || true
        wait $INGESTION_PID 2>/dev/null || true
    fi
    
    if [[ -n "$DASHBOARD_PID" ]]; then
        kill $DASHBOARD_PID 2>/dev/null || true
        wait $DASHBOARD_PID 2>/dev/null || true
    fi
    
    # Kill any remaining test processes
    pkill -f "server.py.*--port $TEST_INGESTION_PORT" 2>/dev/null || true
    pkill -f "app.py.*--port $TEST_DASHBOARD_PORT" 2>/dev/null || true
}

# Set up cleanup trap
trap cleanup EXIT

# Check dependencies
check_dependencies() {
    log_header "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [[ ! -d "$PROJECT_ROOT/venv" ]]; then
        log_warn "Virtual environment not found, creating one..."
        cd "$PROJECT_ROOT"
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r metric_collector/requirements.txt
        pip install -r cloud_ingestion/requirements.txt
        pip install -r dashboard/requirements.txt
        pip install -r tests/requirements.txt
    else
        source "$PROJECT_ROOT/venv/bin/activate"
    fi
    
    # Check required ports are available
    if netstat -tuln 2>/dev/null | grep -q ":$TEST_INGESTION_PORT "; then
        log_error "Port $TEST_INGESTION_PORT is already in use"
        exit 1
    fi
    
    if netstat -tuln 2>/dev/null | grep -q ":$TEST_DASHBOARD_PORT "; then
        log_error "Port $TEST_DASHBOARD_PORT is already in use"
        exit 1
    fi
}

# Start ingestion service
start_ingestion_service() {
    log_info "Starting ingestion service on port $TEST_INGESTION_PORT..."
    
    cd "$PROJECT_ROOT/cloud_ingestion"
    python server.py --host 127.0.0.1 --port $TEST_INGESTION_PORT &
    INGESTION_PID=$!
    
    # Wait for service to start
    log_info "Waiting for ingestion service to start..."
    for i in {1..30}; do
        if curl -s "http://localhost:$TEST_INGESTION_PORT/health" > /dev/null 2>&1; then
            log_info "Ingestion service started successfully"
            return 0
        fi
        sleep 1
    done
    
    log_error "Ingestion service failed to start within $TEST_TIMEOUT seconds"
    return 1
}

# Start dashboard service
start_dashboard_service() {
    log_info "Starting dashboard service on port $TEST_DASHBOARD_PORT..."
    
    cd "$PROJECT_ROOT/dashboard"
    python app.py --host 127.0.0.1 --port $TEST_DASHBOARD_PORT --metrics-url "http://localhost:$TEST_INGESTION_PORT" &
    DASHBOARD_PID=$!
    
    # Wait for service to start
    log_info "Waiting for dashboard service to start..."
    for i in {1..30}; do
        if curl -s "http://localhost:$TEST_DASHBOARD_PORT/api/health" > /dev/null 2>&1; then
            log_info "Dashboard service started successfully"
            return 0
        fi
        sleep 1
    done
    
    log_error "Dashboard service failed to start within $TEST_TIMEOUT seconds"
    return 1
}

# Test ingestion API
test_ingestion_api() {
    log_header "Testing ingestion API..."
    
    # Test health endpoint
    log_info "Testing health endpoint..."
    response=$(curl -s -w "%{http_code}" "http://localhost:$TEST_INGESTION_PORT/health")
    http_code="${response: -3}"
    
    if [[ "$http_code" != "200" ]]; then
        log_error "Health endpoint returned HTTP $http_code"
        return 1
    fi
    
    log_info "Health endpoint test passed"
    
    # Test metrics ingestion
    log_info "Testing metrics ingestion..."
    test_payload='{
        "hostname": "integration-test",
        "metrics": {
            "timestamp": "2024-01-01T12:00:00",
            "hostname": "integration-test",
            "cpu": {"percent": 50.0, "count": 4, "count_logical": 8},
            "memory": {
                "total": 8589934592,
                "available": 4294967296,
                "percent": 50.0,
                "used": 4294967296,
                "free": 4294967296
            },
            "swap": {"total": 2147483648, "used": 0, "free": 2147483648, "percent": 0.0},
            "disk": []
        }
    }'
    
    response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$test_payload" \
        "http://localhost:$TEST_INGESTION_PORT/ingest")
    
    http_code="${response: -3}"
    
    if [[ "$http_code" != "200" ]]; then
        log_error "Metrics ingestion returned HTTP $http_code"
        return 1
    fi
    
    log_info "Metrics ingestion test passed"
    
    # Test metrics retrieval
    log_info "Testing metrics retrieval..."
    response=$(curl -s -w "%{http_code}" "http://localhost:$TEST_INGESTION_PORT/metrics")
    http_code="${response: -3}"
    
    if [[ "$http_code" != "200" ]]; then
        log_error "Metrics retrieval returned HTTP $http_code"
        return 1
    fi
    
    log_info "Metrics retrieval test passed"
}

# Test dashboard API
test_dashboard_api() {
    log_header "Testing dashboard API..."
    
    # Test health endpoint
    log_info "Testing dashboard health endpoint..."
    response=$(curl -s -w "%{http_code}" "http://localhost:$TEST_DASHBOARD_PORT/api/health")
    http_code="${response: -3}"
    
    if [[ "$http_code" != "200" ]]; then
        log_error "Dashboard health endpoint returned HTTP $http_code"
        return 1
    fi
    
    log_info "Dashboard health endpoint test passed"
    
    # Test metrics API
    log_info "Testing dashboard metrics API..."
    response=$(curl -s -w "%{http_code}" "http://localhost:$TEST_DASHBOARD_PORT/api/metrics")
    http_code="${response: -3}"
    
    if [[ "$http_code" != "200" ]]; then
        log_error "Dashboard metrics API returned HTTP $http_code"
        return 1
    fi
    
    log_info "Dashboard metrics API test passed"
}

# Test collector
test_collector() {
    log_header "Testing metrics collector..."
    
    # Create test configuration
    cat > /tmp/test_config.yaml << EOF
endpoint:
  url: "http://localhost:$TEST_INGESTION_PORT/ingest"
  timeout: 10
  max_retries: 3
  retry_delay: 1

interval_seconds: 30

thresholds:
  cpu: 80
  memory: 85
  disk: 90
  swap: 50

alerts:
  enabled: true
  cooldown_minutes: 5
  channels:
    - log

metrics:
  include_network: true
  include_processes: false
  disk_usage_only: true

log_level: INFO
EOF
    
    # Run collector in test mode
    log_info "Running collector test..."
    cd "$PROJECT_ROOT/metric_collector"
    
    if python collector.py --config /tmp/test_config.yaml --test; then
        log_info "Collector test passed"
    else
        log_error "Collector test failed"
        return 1
    fi
    
    # Clean up test config
    rm -f /tmp/test_config.yaml
}

# Run unit tests
run_unit_tests() {
    log_header "Running unit tests..."
    
    cd "$PROJECT_ROOT"
    
    if python -m pytest tests/test_collector.py tests/test_ingestion.py -v; then
        log_info "Unit tests passed"
    else
        log_error "Unit tests failed"
        return 1
    fi
}

# Main test function
main() {
    log_header "Starting integration tests for Metrics Collector..."
    
    # Check dependencies
    check_dependencies
    
    # Start services
    start_ingestion_service || exit 1
    start_dashboard_service || exit 1
    
    # Run tests
    test_ingestion_api || exit 1
    test_dashboard_api || exit 1
    test_collector || exit 1
    
    # Run unit tests
    run_unit_tests || exit 1
    
    log_header "All integration tests passed successfully! ✅"
}

# Run main function
main "$@"
