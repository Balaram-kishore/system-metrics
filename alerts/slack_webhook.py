import requests
import smtplib
import logging
import json
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

class AlertManager:
    """Comprehensive alert management system with multiple notification channels."""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path) if config_path else {}
        self.alert_history = {}  # Track alert history for cooldown

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load alert configuration from file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load alert config: {e}")
            return {}

    def send_alert(self,
                   alert_type: str,
                   message: str,
                   hostname: str,
                   value: Optional[float] = None,
                   threshold: Optional[float] = None,
                   severity: str = "warning") -> bool:
        """Send alert through configured channels with cooldown management."""

        # Check cooldown
        if self._is_in_cooldown(alert_type, hostname):
            logger.debug(f"Alert {alert_type} for {hostname} is in cooldown, skipping")
            return False

        # Update alert history
        self._update_alert_history(alert_type, hostname)

        # Prepare alert data
        alert_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "hostname": hostname,
            "alert_type": alert_type,
            "message": message,
            "value": value,
            "threshold": threshold,
            "severity": severity
        }

        # Send through configured channels
        success = True
        channels = self.config.get('channels', ['log'])

        for channel in channels:
            try:
                if channel == 'slack':
                    self._send_slack_alert(alert_data)
                elif channel == 'email':
                    self._send_email_alert(alert_data)
                elif channel == 'webhook':
                    self._send_webhook_alert(alert_data)
                elif channel == 'log':
                    self._log_alert(alert_data)
                else:
                    logger.warning(f"Unknown alert channel: {channel}")
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}")
                success = False

        return success

    def _is_in_cooldown(self, alert_type: str, hostname: str) -> bool:
        """Check if alert is in cooldown period."""
        key = f"{hostname}:{alert_type}"
        cooldown_minutes = self.config.get('cooldown_minutes', 5)

        if key in self.alert_history:
            time_diff = datetime.utcnow() - self.alert_history[key]
            return time_diff.total_seconds() < (cooldown_minutes * 60)

        return False

    def _update_alert_history(self, alert_type: str, hostname: str):
        """Update alert history for cooldown tracking."""
        key = f"{hostname}:{alert_type}"
        self.alert_history[key] = datetime.utcnow()

    def _log_alert(self, alert_data: Dict[str, Any]):
        """Log alert to file and console."""
        severity_map = {
            'critical': logging.CRITICAL,
            'error': logging.ERROR,
            'warning': logging.WARNING,
            'info': logging.INFO
        }

        level = severity_map.get(alert_data['severity'], logging.WARNING)
        message = (f"ALERT [{alert_data['severity'].upper()}] "
                  f"{alert_data['hostname']}: {alert_data['message']}")

        if alert_data.get('value') is not None and alert_data.get('threshold') is not None:
            message += f" (Value: {alert_data['value']}, Threshold: {alert_data['threshold']})"

        logger.log(level, message)

    def _send_slack_alert(self, alert_data: Dict[str, Any]):
        """Send alert to Slack webhook."""
        webhook_url = self.config.get('slack_webhook_url')
        if not webhook_url:
            raise ValueError("Slack webhook URL not configured")

        # Choose emoji based on severity
        emoji_map = {
            'critical': '🔥',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        emoji = emoji_map.get(alert_data['severity'], '⚠️')

        # Format message
        text = f"{emoji} *{alert_data['severity'].upper()} ALERT*\n"
        text += f"*Host:* {alert_data['hostname']}\n"
        text += f"*Message:* {alert_data['message']}\n"
        text += f"*Time:* {alert_data['timestamp']}\n"

        if alert_data.get('value') is not None and alert_data.get('threshold') is not None:
            text += f"*Value:* {alert_data['value']}\n"
            text += f"*Threshold:* {alert_data['threshold']}\n"

        payload = {
            "text": text,
            "username": "MetricsCollector",
            "icon_emoji": emoji,
            "attachments": [{
                "color": self._get_color_for_severity(alert_data['severity']),
                "fields": [
                    {"title": "Alert Type", "value": alert_data['alert_type'], "short": True},
                    {"title": "Hostname", "value": alert_data['hostname'], "short": True}
                ],
                "footer": "Metrics Collector",
                "ts": int(datetime.utcnow().timestamp())
            }]
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Slack alert sent successfully for {alert_data['hostname']}")

    def _send_email_alert(self, alert_data: Dict[str, Any]):
        """Send alert via email."""
        email_config = self.config.get('email', {})

        if not all(key in email_config for key in ['smtp_server', 'smtp_port', 'username', 'password', 'to_addresses']):
            raise ValueError("Email configuration incomplete")

        # Create message
        msg = MimeMultipart()
        msg['From'] = email_config['username']
        msg['To'] = ', '.join(email_config['to_addresses'])
        msg['Subject'] = f"[{alert_data['severity'].upper()}] Alert from {alert_data['hostname']}"

        # Email body
        body = f"""
        Alert Details:

        Hostname: {alert_data['hostname']}
        Alert Type: {alert_data['alert_type']}
        Severity: {alert_data['severity'].upper()}
        Message: {alert_data['message']}
        Timestamp: {alert_data['timestamp']}
        """

        if alert_data.get('value') is not None and alert_data.get('threshold') is not None:
            body += f"\nValue: {alert_data['value']}\nThreshold: {alert_data['threshold']}"

        msg.attach(MimeText(body, 'plain'))

        # Send email
        with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
            if email_config.get('use_tls', True):
                server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)

        logger.info(f"Email alert sent successfully for {alert_data['hostname']}")

    def _send_webhook_alert(self, alert_data: Dict[str, Any]):
        """Send alert to custom webhook."""
        webhook_url = self.config.get('webhook_url')
        if not webhook_url:
            raise ValueError("Webhook URL not configured")

        headers = self.config.get('webhook_headers', {'Content-Type': 'application/json'})

        response = requests.post(webhook_url, json=alert_data, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Webhook alert sent successfully for {alert_data['hostname']}")

    def _get_color_for_severity(self, severity: str) -> str:
        """Get color code for Slack attachment based on severity."""
        color_map = {
            'critical': '#FF0000',  # Red
            'error': '#FF6600',     # Orange
            'warning': '#FFCC00',   # Yellow
            'info': '#0099CC'       # Blue
        }
        return color_map.get(severity, '#FFCC00')

# Legacy function for backward compatibility
def send_slack_alert(message: str, webhook_url: str = None):
    """Legacy function for sending simple Slack alerts."""
    if not webhook_url:
        webhook_url = "YOUR_SLACK_WEBHOOK_URL"

    payload = {"text": f"🚨 ALERT: {message}"}
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {e}")

# Example usage and testing
if __name__ == "__main__":
    # Test the alert manager
    alert_manager = AlertManager()

    # Test log alert
    alert_manager.send_alert(
        alert_type="cpu_high",
        message="CPU usage is critically high",
        hostname="test-server",
        value=95.5,
        threshold=80.0,
        severity="critical"
    )