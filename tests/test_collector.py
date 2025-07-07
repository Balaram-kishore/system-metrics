import unittest
import tempfile
import os
import yaml
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys
import pathlib

# Add the project root to the Python path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from metric_collector.collector import MetricCollector


class TestMetricCollector(unittest.TestCase):
    """Test cases for the MetricCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_config = {
            'endpoint': {
                'url': 'http://localhost:8000/ingest',
                'timeout': 10,
                'max_retries': 3,
                'retry_delay': 1
            },
            'interval_seconds': 30,
            'thresholds': {
                'cpu': 80,
                'memory': 85,
                'disk': 90,
                'swap': 50
            },
            'alerts': {
                'enabled': True,
                'cooldown_minutes': 5,
                'channels': ['log']
            },
            'metrics': {
                'include_network': True,
                'include_processes': False,
                'disk_usage_only': True
            },
            'log_level': 'INFO'
        }
        
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(self.test_config, self.temp_config)
        self.temp_config.close()

    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_config.name)

    def test_config_loading(self):
        """Test configuration loading."""
        collector = MetricCollector(config_path=self.temp_config.name)
        
        self.assertEqual(collector.config['endpoint']['url'], 'http://localhost:8000/ingest')
        self.assertEqual(collector.config['interval_seconds'], 30)
        self.assertEqual(collector.config['thresholds']['cpu'], 80)

    def test_config_validation(self):
        """Test configuration validation."""
        # Test missing required sections
        invalid_config = {'endpoint': {'url': 'test'}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(invalid_config, f)
            f.flush()
            
            with self.assertRaises(SystemExit):
                MetricCollector(config_path=f.name)
            
            os.unlink(f.name)

    @patch('metric_collector.collector.psutil')
    def test_collect_metrics(self, mock_psutil):
        """Test metrics collection."""
        # Mock psutil functions
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.os.getloadavg.return_value = [1.0, 1.5, 2.0]
        
        # Mock memory
        mock_memory = MagicMock()
        mock_memory.total = 8589934592  # 8GB
        mock_memory.available = 4294967296  # 4GB
        mock_memory.percent = 50.0
        mock_memory.used = 4294967296
        mock_memory.free = 4294967296
        mock_memory.buffers = 0
        mock_memory.cached = 0
        mock_psutil.virtual_memory.return_value = mock_memory
        
        # Mock swap
        mock_swap = MagicMock()
        mock_swap.total = 2147483648  # 2GB
        mock_swap.used = 0
        mock_swap.free = 2147483648
        mock_swap.percent = 0.0
        mock_psutil.swap_memory.return_value = mock_swap
        
        # Mock disk
        mock_partition = MagicMock()
        mock_partition.device = '/dev/sda1'
        mock_partition.mountpoint = '/'
        mock_partition.fstype = 'ext4'
        mock_psutil.disk_partitions.return_value = [mock_partition]
        
        mock_usage = MagicMock()
        mock_usage.total = 107374182400  # 100GB
        mock_usage.used = 53687091200   # 50GB
        mock_usage.free = 53687091200   # 50GB
        mock_psutil.disk_usage.return_value = mock_usage
        
        # Mock network
        mock_net = MagicMock()
        mock_net.bytes_sent = 1000000
        mock_net.bytes_recv = 2000000
        mock_net.packets_sent = 1000
        mock_net.packets_recv = 2000
        mock_net.errin = 0
        mock_net.errout = 0
        mock_net.dropin = 0
        mock_net.dropout = 0
        mock_psutil.net_io_counters.return_value = mock_net
        
        # Mock hostname
        mock_uname = MagicMock()
        mock_uname.nodename = 'test-host'
        mock_psutil.os.uname.return_value = mock_uname
        
        collector = MetricCollector(config_path=self.temp_config.name)
        metrics = collector.collect_metrics()
        
        # Verify metrics structure
        self.assertIn('timestamp', metrics)
        self.assertIn('hostname', metrics)
        self.assertIn('cpu', metrics)
        self.assertIn('memory', metrics)
        self.assertIn('swap', metrics)
        self.assertIn('disk', metrics)
        self.assertIn('network', metrics)
        
        # Verify CPU metrics
        self.assertEqual(metrics['cpu']['percent'], 45.5)
        self.assertEqual(metrics['cpu']['count'], 4)
        
        # Verify memory metrics
        self.assertEqual(metrics['memory']['percent'], 50.0)
        self.assertEqual(metrics['memory']['total'], 8589934592)
        
        # Verify disk metrics
        self.assertEqual(len(metrics['disk']), 1)
        self.assertEqual(metrics['disk'][0]['device'], '/dev/sda1')
        self.assertEqual(metrics['disk'][0]['percent'], 50.0)

    def test_alert_checking(self):
        """Test alert threshold checking."""
        collector = MetricCollector(config_path=self.temp_config.name)
        
        # Test metrics that should trigger alerts
        test_metrics = {
            'cpu': {'percent': 85.0},  # Above 80% threshold
            'memory': {'percent': 90.0},  # Above 85% threshold
            'swap': {'percent': 60.0},  # Above 50% threshold
            'disk': [{'percent': 95.0, 'mountpoint': '/'}]  # Above 90% threshold
        }
        
        with patch.object(collector, '_send_alert') as mock_send_alert:
            collector.check_alerts(test_metrics)
            
            # Should have called _send_alert for each threshold violation
            self.assertEqual(mock_send_alert.call_count, 4)

    def test_alert_cooldown(self):
        """Test alert cooldown functionality."""
        collector = MetricCollector(config_path=self.temp_config.name)
        
        test_metrics = {
            'cpu': {'percent': 85.0}  # Above threshold
        }
        
        with patch.object(collector, 'logger') as mock_logger:
            # First alert should be sent
            collector.check_alerts(test_metrics)
            mock_logger.warning.assert_called()
            
            # Reset mock
            mock_logger.reset_mock()
            
            # Second alert immediately should be blocked by cooldown
            collector.check_alerts(test_metrics)
            mock_logger.warning.assert_not_called()

    @patch('metric_collector.collector.requests')
    def test_send_metrics_success(self, mock_requests):
        """Test successful metrics sending."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_requests.post.return_value = mock_response
        
        collector = MetricCollector(config_path=self.temp_config.name)
        
        with patch.object(collector, 'collect_metrics') as mock_collect:
            mock_collect.return_value = {'test': 'data'}
            
            result = collector.send_metrics()
            
            self.assertTrue(result)
            mock_requests.post.assert_called_once()

    @patch('metric_collector.collector.requests')
    def test_send_metrics_retry(self, mock_requests):
        """Test metrics sending with retry logic."""
        # First two calls fail, third succeeds
        mock_requests.post.side_effect = [
            Exception("Network error"),
            Exception("Network error"),
            MagicMock()
        ]
        
        collector = MetricCollector(config_path=self.temp_config.name)
        
        with patch.object(collector, 'collect_metrics') as mock_collect:
            mock_collect.return_value = {'test': 'data'}
            
            result = collector.send_metrics()
            
            self.assertTrue(result)
            self.assertEqual(mock_requests.post.call_count, 3)

    def test_signal_handling(self):
        """Test graceful shutdown signal handling."""
        collector = MetricCollector(config_path=self.temp_config.name)
        
        # Test signal handler
        collector._signal_handler(15, None)  # SIGTERM
        
        self.assertFalse(collector.running)


if __name__ == '__main__':
    unittest.main()
