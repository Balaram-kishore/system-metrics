import unittest
import subprocess
import time
import requests
import tempfile
import os
import yaml
import signal
import sys
import pathlib
from threading import Thread

# Add the project root to the Python path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete metrics collection pipeline."""

    @classmethod
    def setUpClass(cls):
        """Set up integration test environment."""
        cls.ingestion_process = None
        cls.dashboard_process = None
        cls.temp_config = None
        
        # Create temporary configuration
        test_config = {
            'endpoint': {
                'url': 'http://localhost:8001/ingest',  # Use different port for testing
                'timeout': 10,
                'max_retries': 3,
                'retry_delay': 1
            },
            'interval_seconds': 5,  # Faster for testing
            'thresholds': {
                'cpu': 80,
                'memory': 85,
                'disk': 90,
                'swap': 50
            },
            'alerts': {
                'enabled': True,
                'cooldown_minutes': 1,  # Shorter for testing
                'channels': ['log']
            },
            'metrics': {
                'include_network': True,
                'include_processes': False,
                'disk_usage_only': True
            },
            'log_level': 'INFO'
        }
        
        cls.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(test_config, cls.temp_config)
        cls.temp_config.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up integration test environment."""
        if cls.ingestion_process:
            cls.ingestion_process.terminate()
            cls.ingestion_process.wait()
        
        if cls.dashboard_process:
            cls.dashboard_process.terminate()
            cls.dashboard_process.wait()
        
        if cls.temp_config:
            os.unlink(cls.temp_config.name)

    def start_ingestion_service(self):
        """Start the ingestion service for testing."""
        try:
            self.ingestion_process = subprocess.Popen([
                sys.executable, 
                str(project_root / "cloud_ingestion" / "server.py"),
                "--host", "127.0.0.1",
                "--port", "8001"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for service to start
            for _ in range(30):  # Wait up to 30 seconds
                try:
                    response = requests.get("http://localhost:8001/health", timeout=1)
                    if response.status_code == 200:
                        return True
                except:
                    time.sleep(1)
            
            return False
        except Exception as e:
            print(f"Failed to start ingestion service: {e}")
            return False

    def start_dashboard_service(self):
        """Start the dashboard service for testing."""
        try:
            self.dashboard_process = subprocess.Popen([
                sys.executable,
                str(project_root / "dashboard" / "app.py"),
                "--host", "127.0.0.1",
                "--port", "8081",
                "--metrics-url", "http://localhost:8001"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for service to start
            for _ in range(30):  # Wait up to 30 seconds
                try:
                    response = requests.get("http://localhost:8081/api/health", timeout=1)
                    if response.status_code == 200:
                        return True
                except:
                    time.sleep(1)
            
            return False
        except Exception as e:
            print(f"Failed to start dashboard service: {e}")
            return False

    def test_ingestion_service_startup(self):
        """Test that the ingestion service starts correctly."""
        success = self.start_ingestion_service()
        self.assertTrue(success, "Ingestion service failed to start")
        
        # Test health endpoint
        response = requests.get("http://localhost:8001/health")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "healthy")

    def test_dashboard_service_startup(self):
        """Test that the dashboard service starts correctly."""
        # Start ingestion service first
        if not self.ingestion_process:
            self.start_ingestion_service()
        
        success = self.start_dashboard_service()
        self.assertTrue(success, "Dashboard service failed to start")
        
        # Test health endpoint
        response = requests.get("http://localhost:8081/api/health")
        self.assertEqual(response.status_code, 200)

    def test_metrics_ingestion_flow(self):
        """Test the complete metrics ingestion flow."""
        # Start ingestion service
        if not self.ingestion_process:
            self.start_ingestion_service()
        
        # Create test metrics payload
        test_payload = {
            "hostname": "integration-test-host",
            "metrics": {
                "timestamp": "2024-01-01T12:00:00",
                "hostname": "integration-test-host",
                "cpu": {"percent": 45.5, "count": 4, "count_logical": 8},
                "memory": {
                    "total": 8589934592,
                    "available": 4294967296,
                    "percent": 50.0,
                    "used": 4294967296,
                    "free": 4294967296
                },
                "swap": {"total": 2147483648, "used": 0, "free": 2147483648, "percent": 0.0},
                "disk": [{
                    "device": "/dev/sda1",
                    "mountpoint": "/",
                    "fstype": "ext4",
                    "total": 107374182400,
                    "used": 53687091200,
                    "free": 53687091200,
                    "percent": 50.0
                }]
            }
        }
        
        # Send metrics to ingestion endpoint
        response = requests.post("http://localhost:8001/ingest", json=test_payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "success")
        
        # Verify metrics can be retrieved
        response = requests.get("http://localhost:8001/metrics")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["count"], 0)

    def test_collector_to_ingestion(self):
        """Test collector sending metrics to ingestion service."""
        # Start ingestion service
        if not self.ingestion_process:
            self.start_ingestion_service()
        
        # Run collector in test mode
        try:
            result = subprocess.run([
                sys.executable,
                str(project_root / "metric_collector" / "collector.py"),
                "--config", self.temp_config.name,
                "--test"
            ], capture_output=True, text=True, timeout=30)
            
            self.assertEqual(result.returncode, 0, f"Collector test failed: {result.stderr}")
            
        except subprocess.TimeoutExpired:
            self.fail("Collector test timed out")

    def test_dashboard_data_retrieval(self):
        """Test dashboard retrieving data from ingestion service."""
        # Start both services
        if not self.ingestion_process:
            self.start_ingestion_service()
        
        if not self.dashboard_process:
            self.start_dashboard_service()
        
        # Send test data to ingestion
        test_payload = {
            "hostname": "dashboard-test-host",
            "metrics": {
                "timestamp": "2024-01-01T12:00:00",
                "hostname": "dashboard-test-host",
                "cpu": {"percent": 65.0, "count": 4, "count_logical": 8},
                "memory": {
                    "total": 8589934592,
                    "available": 4294967296,
                    "percent": 75.0,
                    "used": 4294967296,
                    "free": 4294967296
                },
                "swap": {"total": 2147483648, "used": 0, "free": 2147483648, "percent": 0.0},
                "disk": []
            }
        }
        
        requests.post("http://localhost:8001/ingest", json=test_payload)
        
        # Test dashboard API endpoints
        response = requests.get("http://localhost:8081/api/metrics")
        self.assertEqual(response.status_code, 200)
        
        response = requests.get("http://localhost:8081/api/summary")
        self.assertEqual(response.status_code, 200)
        
        response = requests.get("http://localhost:8081/api/hosts")
        self.assertEqual(response.status_code, 200)

    def test_end_to_end_pipeline(self):
        """Test the complete end-to-end pipeline."""
        # Start all services
        if not self.ingestion_process:
            self.assertTrue(self.start_ingestion_service(), "Failed to start ingestion service")
        
        if not self.dashboard_process:
            self.assertTrue(self.start_dashboard_service(), "Failed to start dashboard service")
        
        # Run collector once to generate and send metrics
        try:
            result = subprocess.run([
                sys.executable,
                str(project_root / "metric_collector" / "collector.py"),
                "--config", self.temp_config.name,
                "--test"
            ], capture_output=True, text=True, timeout=30)
            
            self.assertEqual(result.returncode, 0, f"Collector failed: {result.stderr}")
            
        except subprocess.TimeoutExpired:
            self.fail("Collector timed out")
        
        # Wait a moment for data to be processed
        time.sleep(2)
        
        # Verify data is available through dashboard
        response = requests.get("http://localhost:8081/api/metrics")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "success")
        
        # Verify summary statistics
        response = requests.get("http://localhost:8081/api/summary")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("summary", data)


if __name__ == '__main__':
    # Run integration tests
    unittest.main(verbosity=2)
