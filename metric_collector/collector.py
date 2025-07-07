import psutil
import requests
import yaml
import logging
import time
import json
import os
import signal
import sys
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

class MetricCollector:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.running = True
        self.alert_cooldown = {}  # Track alert cooldowns to prevent spam

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def _load_config(self, path):
        """Load configuration with error handling and validation."""
        try:
            config_path = Path(path)
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {path}")

            with open(config_path) as f:
                config = yaml.safe_load(f)

            # Validate required configuration sections
            required_sections = ['endpoint', 'interval_seconds', 'thresholds']
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"Missing required configuration section: {section}")

            # Set default values for optional configurations
            config.setdefault('alerts', {
                'enabled': True,
                'cooldown_minutes': 5,
                'channels': ['log']
            })
            config.setdefault('metrics', {
                'include_network': True,
                'include_processes': False,
                'disk_usage_only': True
            })

            return config
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)

    def _setup_logging(self):
        """Setup structured logging with file and console output."""
        log_level = getattr(logging, self.config.get('log_level', 'INFO').upper())
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_dir / 'metrics_collector.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger(__name__)

    def _get_hostname(self):
        try:
            return psutil.os.uname().nodename
        except (AttributeError, OSError):
            return platform.node()

    def collect_metrics(self) -> Dict[str, Any]:
        """Gather comprehensive system metrics using psutil."""
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            hostname = self._get_hostname()

            # CPU metrics
            cpu_data = {
                "percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True),
                "load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else None
            }

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_data = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free,
                "buffers": getattr(memory, 'buffers', 0),
                "cached": getattr(memory, 'cached', 0)
            }

            # Swap memory
            swap = psutil.swap_memory()
            swap_data = {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent
            }

            # Disk metrics
            disk_data = []
            if self.config['metrics'].get('disk_usage_only', True):
                # Only collect disk usage for mounted filesystems
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disk_data.append({
                            "device": partition.device,
                            "mountpoint": partition.mountpoint,
                            "fstype": partition.fstype,
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": (usage.used / usage.total) * 100 if usage.total > 0 else 0
                        })
                    except (PermissionError, OSError):
                        # Skip inaccessible partitions
                        continue
            else:
                # Include partition information
                disk_data = [dict(part._asdict()) for part in psutil.disk_partitions()]

            metrics = {
                "timestamp": timestamp,
                "hostname": hostname,
                "cpu": cpu_data,
                "memory": memory_data,
                "swap": swap_data,
                "disk": disk_data
            }

            # Optional network metrics
            if self.config['metrics'].get('include_network', True):
                net_io = psutil.net_io_counters()
                metrics["network"] = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                    "dropin": net_io.dropin,
                    "dropout": net_io.dropout
                }

            # Optional process metrics (top processes by CPU/memory)
            if self.config['metrics'].get('include_processes', False):
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                # Sort by CPU usage and take top 10
                processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
                metrics["top_processes"] = processes[:10]

            return metrics
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hostname": self._get_hostname(),
                "error": str(e)
            }

    def check_alerts(self, metrics: Dict[str, Any]) -> None:
        """Check metrics against thresholds and trigger alerts."""
        if not self.config.get('alerts', {}).get('enabled', True):
            return

        thresholds = self.config.get('thresholds', {})
        alerts_triggered = []

        # Check CPU threshold
        if 'cpu' in thresholds and 'cpu' in metrics:
            cpu_percent = metrics['cpu'].get('percent', 0)
            if cpu_percent > thresholds['cpu']:
                alerts_triggered.append(f"High CPU usage: {cpu_percent:.1f}% (threshold: {thresholds['cpu']}%)")

        # Check memory threshold
        if 'memory' in thresholds and 'memory' in metrics:
            memory_percent = metrics['memory'].get('percent', 0)
            if memory_percent > thresholds['memory']:
                alerts_triggered.append(f"High memory usage: {memory_percent:.1f}% (threshold: {thresholds['memory']}%)")

        # Check disk threshold
        if 'disk' in thresholds and 'disk' in metrics:
            disk_threshold = thresholds['disk']
            for disk in metrics['disk']:
                if isinstance(disk, dict) and 'percent' in disk:
                    if disk['percent'] > disk_threshold:
                        alerts_triggered.append(
                            f"High disk usage on {disk.get('mountpoint', 'unknown')}: "
                            f"{disk['percent']:.1f}% (threshold: {disk_threshold}%)"
                        )

        # Check swap threshold
        if 'swap' in thresholds and 'swap' in metrics:
            swap_percent = metrics['swap'].get('percent', 0)
            if swap_percent > thresholds['swap']:
                alerts_triggered.append(f"High swap usage: {swap_percent:.1f}% (threshold: {thresholds['swap']}%)")

        # Send alerts if any were triggered
        for alert_message in alerts_triggered:
            self._send_alert(alert_message)

    def _send_alert(self, message: str) -> None:
        """Send alert through configured channels with cooldown."""
        # Check cooldown to prevent alert spam
        cooldown_key = hash(message)
        cooldown_minutes = self.config.get('alerts', {}).get('cooldown_minutes', 5)
        current_time = datetime.utcnow()

        if cooldown_key in self.alert_cooldown:
            time_diff = (current_time - self.alert_cooldown[cooldown_key]).total_seconds() / 60
            if time_diff < cooldown_minutes:
                return  # Still in cooldown period

        self.alert_cooldown[cooldown_key] = current_time

        # Log alert
        self.logger.warning(f"ALERT: {message}")

        # Send to configured channels
        alert_channels = self.config.get('alerts', {}).get('channels', ['log'])

        for channel in alert_channels:
            try:
                if channel == 'slack':
                    self._send_slack_alert(message)
                elif channel == 'email':
                    self._send_email_alert(message)
                # 'log' channel is already handled above
            except Exception as e:
                self.logger.error(f"Failed to send alert via {channel}: {e}")

    def _send_slack_alert(self, message: str) -> None:
        """Send alert to Slack webhook."""
        webhook_url = self.config.get('alerts', {}).get('slack_webhook_url')
        if not webhook_url:
            self.logger.error("Slack webhook URL not configured")
            return

        payload = {
            "text": f"🚨 ALERT from {self._get_hostname()}: {message}",
            "username": "MetricsCollector",
            "icon_emoji": ":warning:"
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

    def _send_email_alert(self, message: str) -> None:
        """Send alert via email (placeholder for future implementation)."""
        # This would require SMTP configuration
        self.logger.info(f"Email alert (not implemented): {message}")

    def send_metrics(self) -> bool:
        """Send metrics to the cloud endpoint with retry logic."""
        max_retries = self.config.get('endpoint', {}).get('max_retries', 3)
        retry_delay = self.config.get('endpoint', {}).get('retry_delay', 5)

        for attempt in range(max_retries):
            try:
                metrics = self.collect_metrics()

                # Check for alerts before sending
                self.check_alerts(metrics)

                # Prepare payload
                payload = {
                    "hostname": metrics.get("hostname", self._get_hostname()),
                    "metrics": metrics
                }

                # Send to endpoint
                response = requests.post(
                    self.config["endpoint"]["url"],
                    json=payload,
                    timeout=self.config.get('endpoint', {}).get('timeout', 10),
                    headers={'Content-Type': 'application/json'}
                )
                response.raise_for_status()

                self.logger.info(f"Metrics sent successfully (attempt {attempt + 1})")
                self.logger.debug(f"Metrics payload: {json.dumps(payload, indent=2)}")
                return True

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Network error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to send metrics after {max_retries} attempts")

            except Exception as e:
                self.logger.error(f"Unexpected error sending metrics: {e}")
                break

        return False

    def run(self) -> None:
        """Main execution loop with graceful shutdown handling."""
        self.logger.info("Starting Metrics Collector service...")
        self.logger.info(f"Collection interval: {self.config['interval_seconds']} seconds")
        self.logger.info(f"Endpoint: {self.config['endpoint']['url']}")

        while self.running:
            try:
                start_time = time.time()

                # Send metrics
                success = self.send_metrics()

                # Calculate sleep time to maintain consistent intervals
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.config["interval_seconds"] - elapsed_time)

                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(f"Metrics collection took {elapsed_time:.2f}s, "
                                      f"longer than interval of {self.config['interval_seconds']}s")

            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(5)  # Brief pause before retrying

        self.logger.info("Metrics Collector service stopped.")

def main():
    """Entry point for the metrics collector service."""
    import argparse

    parser = argparse.ArgumentParser(description='Linux Metrics Collector Service')
    parser.add_argument('--config', '-c', default='config.yaml',
                       help='Path to configuration file (default: config.yaml)')
    parser.add_argument('--test', '-t', action='store_true',
                       help='Run a single metrics collection test and exit')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()

    try:
        collector = MetricCollector(config_path=args.config)

        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        if args.test:
            print("Running metrics collection test...")
            metrics = collector.collect_metrics()
            print(json.dumps(metrics, indent=2))
            collector.check_alerts(metrics)
            print("Test completed successfully!")
        else:
            collector.run()

    except Exception as e:
        print(f"Failed to start metrics collector: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()