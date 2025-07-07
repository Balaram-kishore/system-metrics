# Metrics Collector Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help install install-dev test test-unit test-integration clean start stop restart status logs health setup-venv lint format check-deps

# Default target
help:
	@echo "Metrics Collector - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  setup-venv     - Create and setup Python virtual environment"
	@echo "  install-dev    - Install development dependencies"
	@echo "  lint          - Run code linting with flake8"
	@echo "  format        - Format code with black"
	@echo "  check-deps    - Check for dependency vulnerabilities"
	@echo ""
	@echo "Testing:"
	@echo "  test          - Run all tests"
	@echo "  test-unit     - Run unit tests only"
	@echo "  test-integration - Run integration tests"
	@echo ""
	@echo "Deployment:"
	@echo "  install       - Install system-wide (requires sudo)"
	@echo "  start         - Start all services"
	@echo "  stop          - Stop all services"
	@echo "  restart       - Restart all services"
	@echo "  status        - Show service status"
	@echo "  logs          - Show service logs"
	@echo "  health        - Check service health"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean         - Clean temporary files and caches"

# Virtual environment setup
setup-venv:
	@echo "Setting up Python virtual environment..."
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r metric_collector/requirements.txt
	./venv/bin/pip install -r cloud_ingestion/requirements.txt
	./venv/bin/pip install -r dashboard/requirements.txt
	./venv/bin/pip install -r alerts/requirements.txt
	./venv/bin/pip install -r tests/requirements.txt
	@echo "Virtual environment setup complete!"

# Development dependencies
install-dev: setup-venv
	@echo "Installing development dependencies..."
	./venv/bin/pip install black flake8 safety bandit
	@echo "Development dependencies installed!"

# Code linting
lint:
	@echo "Running code linting..."
	./venv/bin/flake8 metric_collector/ cloud_ingestion/ dashboard/ alerts/ --max-line-length=100 --ignore=E203,W503
	@echo "Linting complete!"

# Code formatting
format:
	@echo "Formatting code with black..."
	./venv/bin/black metric_collector/ cloud_ingestion/ dashboard/ alerts/ tests/ --line-length=100
	@echo "Code formatting complete!"

# Security and dependency checks
check-deps:
	@echo "Checking dependencies for security vulnerabilities..."
	./venv/bin/safety check
	./venv/bin/bandit -r metric_collector/ cloud_ingestion/ dashboard/ alerts/
	@echo "Dependency check complete!"

# Testing
test: test-unit test-integration

test-unit:
	@echo "Running unit tests..."
	./venv/bin/python -m pytest tests/test_collector.py tests/test_ingestion.py -v --cov=metric_collector --cov=cloud_ingestion

test-integration:
	@echo "Running integration tests..."
	chmod +x scripts/test-integration.sh
	./scripts/test-integration.sh

# System installation
install:
	@echo "Installing Metrics Collector system-wide..."
	@if [ "$$EUID" -ne 0 ]; then \
		echo "Please run with sudo: sudo make install"; \
		exit 1; \
	fi
	chmod +x scripts/install.sh
	./scripts/install.sh

# Service management
start:
	@echo "Starting all services..."
	chmod +x scripts/manage-services.sh
	sudo ./scripts/manage-services.sh start

stop:
	@echo "Stopping all services..."
	chmod +x scripts/manage-services.sh
	sudo ./scripts/manage-services.sh stop

restart:
	@echo "Restarting all services..."
	chmod +x scripts/manage-services.sh
	sudo ./scripts/manage-services.sh restart

status:
	@echo "Checking service status..."
	chmod +x scripts/manage-services.sh
	./scripts/manage-services.sh status

logs:
	@echo "Showing service logs..."
	chmod +x scripts/manage-services.sh
	./scripts/manage-services.sh logs

health:
	@echo "Checking service health..."
	chmod +x scripts/manage-services.sh
	./scripts/manage-services.sh health

# Cleanup
clean:
	@echo "Cleaning temporary files and caches..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f *.db
	rm -f /tmp/test_config.yaml
	@echo "Cleanup complete!"

# Development server targets
dev-ingestion:
	@echo "Starting ingestion service in development mode..."
	cd cloud_ingestion && ../venv/bin/python server.py --reload

dev-dashboard:
	@echo "Starting dashboard in development mode..."
	cd dashboard && ../venv/bin/python app.py --reload

dev-collector:
	@echo "Running collector in test mode..."
	cd metric_collector && ../venv/bin/python collector.py --test --verbose

# Quick development setup
dev-setup: setup-venv install-dev
	@echo "Development environment setup complete!"
	@echo "You can now run:"
	@echo "  make dev-ingestion  (in one terminal)"
	@echo "  make dev-dashboard  (in another terminal)"
	@echo "  make dev-collector  (to test collector)"

# Production deployment check
deploy-check:
	@echo "Running pre-deployment checks..."
	make lint
	make check-deps
	make test
	@echo "All checks passed! Ready for deployment."
