#!/bin/bash

# Metrics Collector Installation Script
# This script installs and configures the metrics collector system

set -e

# Configuration
INSTALL_DIR="/opt/metrics-collector"
CONFIG_DIR="/etc/metrics-collector"
LOG_DIR="/var/log/metrics-collector"
DATA_DIR="/var/lib/metrics-collector"
SERVICE_USER="metrics"
SERVICE_GROUP="metrics"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y python3 python3-pip python3-venv sqlite3 curl
    elif command -v yum &> /dev/null; then
        yum update -y
        yum install -y python3 python3-pip sqlite curl
    elif command -v dnf &> /dev/null; then
        dnf update -y
        dnf install -y python3 python3-pip sqlite curl
    else
        log_error "Unsupported package manager. Please install Python 3, pip, and sqlite manually."
        exit 1
    fi
}

# Create system user and group
create_user() {
    log_info "Creating system user and group..."
    
    if ! getent group "$SERVICE_GROUP" > /dev/null 2>&1; then
        groupadd --system "$SERVICE_GROUP"
    fi
    
    if ! getent passwd "$SERVICE_USER" > /dev/null 2>&1; then
        useradd --system --gid "$SERVICE_GROUP" --home-dir "$INSTALL_DIR" \
                --shell /bin/false --comment "Metrics Collector Service" "$SERVICE_USER"
    fi
}

# Create directories
create_directories() {
    log_info "Creating directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DATA_DIR"
    
    # Set permissions
    chmod 755 "$INSTALL_DIR"
    chmod 755 "$CONFIG_DIR"
    chmod 755 "$LOG_DIR"
    chmod 755 "$DATA_DIR"
}

# Copy application files
copy_files() {
    log_info "Copying application files..."
    
    # Copy source code
    cp -r metric_collector "$INSTALL_DIR/"
    cp -r cloud_ingestion "$INSTALL_DIR/"
    cp -r dashboard "$INSTALL_DIR/"
    cp -r alerts "$INSTALL_DIR/"
    
    # Copy configuration files
    cp metric_collector/config.yaml "$CONFIG_DIR/"
    cp alerts/alert_config.yaml "$CONFIG_DIR/"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    chown -R root:root "$CONFIG_DIR"
    chmod 644 "$CONFIG_DIR"/*.yaml
}

# Setup Python virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."
    
    cd "$INSTALL_DIR"
    python3 -m venv venv
    
    # Install dependencies
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r metric_collector/requirements.txt
    ./venv/bin/pip install -r cloud_ingestion/requirements.txt
    ./venv/bin/pip install -r dashboard/requirements.txt
    ./venv/bin/pip install -r alerts/requirements.txt
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR/venv"
}

# Install systemd services
install_services() {
    log_info "Installing systemd services..."
    
    # Copy service files
    cp metric_collector/systemd/metric-collector.service /etc/systemd/system/
    cp cloud_ingestion/systemd/metrics-ingestion.service /etc/systemd/system/
    cp dashboard/systemd/metrics-dashboard.service /etc/systemd/system/
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable metric-collector.service
    systemctl enable metrics-ingestion.service
    systemctl enable metrics-dashboard.service
}

# Configure logrotate
setup_logrotate() {
    log_info "Setting up log rotation..."
    
    cat > /etc/logrotate.d/metrics-collector << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_GROUP
    postrotate
        systemctl reload metric-collector.service || true
        systemctl reload metrics-ingestion.service || true
        systemctl reload metrics-dashboard.service || true
    endscript
}
EOF
}

# Main installation function
main() {
    log_info "Starting Metrics Collector installation..."
    
    check_root
    install_dependencies
    create_user
    create_directories
    copy_files
    setup_venv
    install_services
    setup_logrotate
    
    log_info "Installation completed successfully!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Edit configuration files in $CONFIG_DIR"
    log_info "2. Start services: systemctl start metric-collector metrics-ingestion metrics-dashboard"
    log_info "3. Check status: systemctl status metric-collector"
    log_info "4. View logs: journalctl -u metric-collector -f"
    log_info "5. Access dashboard: http://localhost:8080"
}

# Run main function
main "$@"
