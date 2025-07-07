#!/bin/bash

# Metrics Collector Service Management Script
# This script provides easy management of all metrics collector services

set -e

# Service names
SERVICES=("metric-collector" "metrics-ingestion" "metrics-dashboard")

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

# Check if running as root for service operations
check_permissions() {
    if [[ $EUID -ne 0 ]] && [[ "$1" != "status" ]] && [[ "$1" != "logs" ]]; then
        log_error "This operation requires root privileges"
        exit 1
    fi
}

# Start all services
start_services() {
    log_header "Starting all metrics collector services..."
    
    for service in "${SERVICES[@]}"; do
        log_info "Starting $service..."
        if systemctl start "$service"; then
            log_info "$service started successfully"
        else
            log_error "Failed to start $service"
        fi
    done
}

# Stop all services
stop_services() {
    log_header "Stopping all metrics collector services..."
    
    # Stop in reverse order to handle dependencies
    for ((i=${#SERVICES[@]}-1; i>=0; i--)); do
        service="${SERVICES[$i]}"
        log_info "Stopping $service..."
        if systemctl stop "$service"; then
            log_info "$service stopped successfully"
        else
            log_error "Failed to stop $service"
        fi
    done
}

# Restart all services
restart_services() {
    log_header "Restarting all metrics collector services..."
    stop_services
    sleep 2
    start_services
}

# Reload all services
reload_services() {
    log_header "Reloading all metrics collector services..."
    
    for service in "${SERVICES[@]}"; do
        log_info "Reloading $service..."
        if systemctl reload "$service" 2>/dev/null; then
            log_info "$service reloaded successfully"
        else
            log_warn "$service does not support reload, restarting instead..."
            systemctl restart "$service"
        fi
    done
}

# Show status of all services
show_status() {
    log_header "Status of all metrics collector services:"
    echo
    
    for service in "${SERVICES[@]}"; do
        echo -e "${BLUE}=== $service ===${NC}"
        systemctl status "$service" --no-pager -l
        echo
    done
}

# Show logs for all services
show_logs() {
    local follow_flag=""
    if [[ "$2" == "-f" ]] || [[ "$2" == "--follow" ]]; then
        follow_flag="-f"
    fi
    
    log_header "Showing logs for all metrics collector services..."
    
    if [[ -n "$follow_flag" ]]; then
        # Follow logs for all services
        journalctl -u metric-collector -u metrics-ingestion -u metrics-dashboard $follow_flag
    else
        # Show recent logs for each service
        for service in "${SERVICES[@]}"; do
            echo -e "${BLUE}=== Recent logs for $service ===${NC}"
            journalctl -u "$service" --no-pager -n 20
            echo
        done
    fi
}

# Enable all services
enable_services() {
    log_header "Enabling all metrics collector services..."
    
    for service in "${SERVICES[@]}"; do
        log_info "Enabling $service..."
        if systemctl enable "$service"; then
            log_info "$service enabled successfully"
        else
            log_error "Failed to enable $service"
        fi
    done
}

# Disable all services
disable_services() {
    log_header "Disabling all metrics collector services..."
    
    for service in "${SERVICES[@]}"; do
        log_info "Disabling $service..."
        if systemctl disable "$service"; then
            log_info "$service disabled successfully"
        else
            log_error "Failed to disable $service"
        fi
    done
}

# Show service health
show_health() {
    log_header "Health check for metrics collector services:"
    echo
    
    # Check systemd service status
    for service in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$service"; then
            echo -e "${GREEN}✓${NC} $service is running"
        else
            echo -e "${RED}✗${NC} $service is not running"
        fi
    done
    
    echo
    
    # Check API endpoints
    log_info "Checking API endpoints..."
    
    # Check ingestion service
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Metrics ingestion API is responding"
    else
        echo -e "${RED}✗${NC} Metrics ingestion API is not responding"
    fi
    
    # Check dashboard
    if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Dashboard API is responding"
    else
        echo -e "${RED}✗${NC} Dashboard API is not responding"
    fi
}

# Show usage information
show_usage() {
    echo "Usage: $0 {start|stop|restart|reload|status|logs|enable|disable|health}"
    echo
    echo "Commands:"
    echo "  start    - Start all metrics collector services"
    echo "  stop     - Stop all metrics collector services"
    echo "  restart  - Restart all metrics collector services"
    echo "  reload   - Reload all metrics collector services"
    echo "  status   - Show status of all services"
    echo "  logs     - Show recent logs (use -f to follow)"
    echo "  enable   - Enable all services for automatic startup"
    echo "  disable  - Disable all services"
    echo "  health   - Show health status of all services"
    echo
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs -f"
    echo "  $0 health"
}

# Main function
main() {
    case "$1" in
        start)
            check_permissions "$1"
            start_services
            ;;
        stop)
            check_permissions "$1"
            stop_services
            ;;
        restart)
            check_permissions "$1"
            restart_services
            ;;
        reload)
            check_permissions "$1"
            reload_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$@"
            ;;
        enable)
            check_permissions "$1"
            enable_services
            ;;
        disable)
            check_permissions "$1"
            disable_services
            ;;
        health)
            show_health
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
