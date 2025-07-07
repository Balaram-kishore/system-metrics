# Linux Metrics Collector

A comprehensive, lightweight Linux resource-monitoring service that periodically collects system metrics (CPU, memory, disk, network), sends them to a cloud-based ingestion endpoint, provides a web dashboard for visualization, and triggers alerts when thresholds are exceeded.

## 🚀 Features

- **Real-time Metrics Collection**: CPU, memory, disk, swap, and network statistics
- **Cloud Ingestion**: RESTful API for metrics storage with SQLite backend
- **Web Dashboard**: Interactive charts and real-time visualization
- **Alert System**: Multi-channel notifications (Slack, email, webhooks)
- **Systemd Integration**: Proper Linux service management
- **Configurable Thresholds**: Customizable alert conditions
- **Automatic Cleanup**: Data retention management
- **Security Hardened**: Runs with minimal privileges

## 📋 Architecture

```
┌─────────────────┐    HTTP POST    ┌─────────────────┐    SQLite    ┌─────────────────┐
│  Metric         │ ──────────────> │  Cloud          │ ──────────> │  Database       │
│  Collector      │                 │  Ingestion      │             │  Storage        │
└─────────────────┘                 └─────────────────┘             └─────────────────┘
         │                                   │
         │ Alerts                           │ API
         ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│  Alert          │                 │  Web            │
│  Manager        │                 │  Dashboard      │
└─────────────────┘                 └─────────────────┘
```

## 🛠️ Components

### 1. Metric Collector (`metric_collector/`)
- Collects system metrics using `psutil`
- Configurable collection intervals
- Built-in alert threshold checking
- Graceful shutdown handling
- Comprehensive error handling and logging

### 2. Cloud Ingestion Service (`cloud_ingestion/`)
- FastAPI-based REST API
- SQLite database for metrics storage
- Data validation with Pydantic models
- Automatic data cleanup
- Health monitoring endpoints

### 3. Web Dashboard (`dashboard/`)
- Real-time metrics visualization
- Interactive charts with Chart.js
- Multi-host support
- Responsive design
- Historical data analysis

### 4. Alert System (`alerts/`)
- Multi-channel notifications
- Configurable cooldown periods
- Slack, email, and webhook support
- Alert history tracking

## 📦 Installation

### Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/metrics-collector-linux.git
cd metrics-collector-linux

# Run the installation script (requires root)
sudo ./scripts/install.sh
```

### Manual Installation

1. **Install Dependencies**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install python3 python3-pip python3-venv sqlite3

   # CentOS/RHEL
   sudo yum install python3 python3-pip sqlite
   ```

2. **Create Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python Dependencies**:
   ```bash
   pip install -r metric_collector/requirements.txt
   pip install -r cloud_ingestion/requirements.txt
   pip install -r dashboard/requirements.txt
   pip install -r alerts/requirements.txt
   ```

## ⚙️ Configuration

### Metric Collector Configuration (`metric_collector/config.yaml`)

```yaml
# Cloud endpoint configuration
endpoint:
  url: "http://localhost:8000/ingest"
  timeout: 10
  max_retries: 3
  retry_delay: 5

# Collection interval
interval_seconds: 30

# Metrics to collect
metrics:
  include_network: true
  include_processes: false
  disk_usage_only: true

# Alert thresholds
thresholds:
  cpu: 80      # Alert if CPU > 80%
  memory: 85   # Alert if memory > 85%
  disk: 90     # Alert if any disk > 90%
  swap: 50     # Alert if swap > 50%

# Alert configuration
alerts:
  enabled: true
  cooldown_minutes: 5
  channels:
    - log
    # - slack
    # - email
```

### Alert Configuration (`alerts/alert_config.yaml`)

```yaml
# Notification channels
channels:
  - log
  # - slack
  # - email

# Slack configuration
# slack_webhook_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

# Email configuration
email:
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  username: "your-email@gmail.com"
  password: "your-app-password"
  to_addresses:
    - "admin@yourcompany.com"
```

## 🚀 Usage

### Starting Services

```bash
# Start all services
sudo ./scripts/manage-services.sh start

# Or start individual services
sudo systemctl start metric-collector
sudo systemctl start metrics-ingestion
sudo systemctl start metrics-dashboard
```

### Accessing the Dashboard

Open your web browser and navigate to:
- **Dashboard**: http://localhost:8080
- **API Documentation**: http://localhost:8000/docs

### Managing Services

```bash
# Check service status
./scripts/manage-services.sh status

# View logs
./scripts/manage-services.sh logs

# Follow logs in real-time
./scripts/manage-services.sh logs -f

# Health check
./scripts/manage-services.sh health

# Restart services
sudo ./scripts/manage-services.sh restart
```

### Testing the Collector

```bash
# Run a single metrics collection test
cd metric_collector
python collector.py --test

# Test with verbose output
python collector.py --test --verbose
```

## 📊 API Endpoints

### Metrics Ingestion Service (Port 8000)

- `POST /ingest` - Receive metrics from collectors
- `GET /metrics` - Retrieve stored metrics
- `GET /metrics/summary` - Get summary statistics
- `GET /health` - Health check
- `POST /cleanup` - Manual data cleanup

### Dashboard API (Port 8080)

- `GET /` - Main dashboard interface
- `GET /api/metrics` - Get metrics for charts
- `GET /api/summary` - Get summary statistics
- `GET /api/hosts` - List available hosts
- `GET /api/health` - Health check

## 🔧 Development

### Running in Development Mode

```bash
# Start ingestion service with auto-reload
cd cloud_ingestion
python server.py --reload

# Start dashboard with auto-reload
cd dashboard
python app.py --reload

# Run collector in test mode
cd metric_collector
python collector.py --test --verbose
```

### Project Structure

```
metrics-collector-linux/
├── metric_collector/          # Core metrics collection
│   ├── collector.py          # Main collector logic
│   ├── config.yaml           # Configuration
│   ├── requirements.txt      # Python dependencies
│   └── systemd/              # Service files
├── cloud_ingestion/          # API and data storage
│   ├── server.py             # FastAPI application
│   ├── requirements.txt      # Python dependencies
│   └── systemd/              # Service files
├── dashboard/                # Web dashboard
│   ├── app.py                # Dashboard application
│   ├── templates/            # HTML templates
│   ├── static/               # CSS/JS files
│   ├── requirements.txt      # Python dependencies
│   └── systemd/              # Service files
├── alerts/                   # Alert management
│   ├── slack_webhook.py      # Alert manager
│   ├── alert_config.yaml     # Alert configuration
│   └── requirements.txt      # Python dependencies
└── scripts/                  # Installation and management
    ├── install.sh            # Installation script
    └── manage-services.sh     # Service management
```

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=metric_collector --cov=cloud_ingestion --cov=dashboard

# Run specific test file
python -m pytest tests/test_collector.py -v
```

### Integration Tests

```bash
# Test the complete pipeline
./scripts/test-integration.sh

# Test individual components
python -m pytest tests/test_integration.py::test_end_to_end
```

## 🔒 Security Considerations

- Services run with minimal privileges (non-root user)
- Systemd security hardening enabled
- Input validation on all API endpoints
- Rate limiting and timeout configurations
- Secure file permissions
- No sensitive data in logs

## 📈 Performance

- **Memory Usage**: ~50-100MB per service
- **CPU Usage**: <5% on modern systems
- **Disk Usage**: ~1MB per day of metrics data
- **Network**: Minimal bandwidth usage

## 🔍 Troubleshooting

### Common Issues

1. **Service won't start**:
   ```bash
   # Check service status
   systemctl status metric-collector

   # Check logs
   journalctl -u metric-collector -f
   ```

2. **Dashboard not accessible**:
   ```bash
   # Check if ingestion service is running
   curl http://localhost:8000/health

   # Check dashboard service
   systemctl status metrics-dashboard
   ```

3. **No metrics data**:
   ```bash
   # Test collector manually
   cd metric_collector
   python collector.py --test

   # Check ingestion endpoint
   curl -X POST http://localhost:8000/ingest \
        -H "Content-Type: application/json" \
        -d '{"hostname":"test","metrics":{"timestamp":"2024-01-01T00:00:00","cpu":{"percent":50},"memory":{"percent":60},"swap":{"percent":0},"disk":[]}}'
   ```

4. **Alerts not working**:
   ```bash
   # Check alert configuration
   cat /etc/metrics-collector/alert_config.yaml

   # Test alert manually
   cd alerts
   python slack_webhook.py
   ```

### Log Locations

- **Collector**: `/var/log/metrics-collector/metrics_collector.log`
- **Ingestion**: `journalctl -u metrics-ingestion`
- **Dashboard**: `journalctl -u metrics-dashboard`
- **System**: `journalctl -u metric-collector`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [psutil](https://github.com/giampaolo/psutil) for system metrics collection
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Chart.js](https://www.chartjs.org/) for dashboard visualizations
- [Bootstrap](https://getbootstrap.com/) for responsive UI components

## 📞 Support

For support, please:
1. Check the [troubleshooting section](#-troubleshooting)
2. Search existing [issues](https://github.com/your-org/metrics-collector-linux/issues)
3. Create a new issue with detailed information

---

**Made with ❤️ for Linux system monitoring**
