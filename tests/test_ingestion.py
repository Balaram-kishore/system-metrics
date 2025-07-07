import unittest
import tempfile
import os
import json
import sqlite3
from datetime import datetime
import sys
import pathlib
from fastapi.testclient import TestClient

# Add the project root to the Python path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cloud_ingestion.server import app, MetricsDatabase, MetricsPayload, SystemMetrics


class TestMetricsDatabase(unittest.TestCase):
    """Test cases for the MetricsDatabase class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db = MetricsDatabase(db_path=self.temp_db.name)

    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_db.name)

    def test_database_initialization(self):
        """Test database initialization."""
        # Check if tables were created
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('metrics', 'alerts')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            self.assertIn('metrics', tables)
            self.assertIn('alerts', tables)

    def test_store_metrics(self):
        """Test storing metrics in the database."""
        # Create test payload
        test_metrics = {
            "timestamp": "2024-01-01T12:00:00",
            "hostname": "test-host",
            "cpu": {"percent": 50.0, "count": 4, "count_logical": 8},
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
        
        payload = MetricsPayload(
            hostname="test-host",
            metrics=SystemMetrics(**test_metrics)
        )
        
        # Store metrics
        result = self.db.store_metrics(payload)
        self.assertTrue(result)
        
        # Verify storage
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM metrics")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1)
            
            cursor = conn.execute("SELECT hostname, cpu_percent, memory_percent FROM metrics")
            row = cursor.fetchone()
            self.assertEqual(row[0], "test-host")
            self.assertEqual(row[1], 50.0)
            self.assertEqual(row[2], 50.0)

    def test_get_recent_metrics(self):
        """Test retrieving recent metrics."""
        # Store test data first
        test_metrics = {
            "timestamp": "2024-01-01T12:00:00",
            "hostname": "test-host",
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
        
        payload = MetricsPayload(
            hostname="test-host",
            metrics=SystemMetrics(**test_metrics)
        )
        
        self.db.store_metrics(payload)
        
        # Retrieve metrics
        metrics = self.db.get_recent_metrics(hostname="test-host", hours=24)
        
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]['hostname'], "test-host")

    def test_get_summary_stats(self):
        """Test getting summary statistics."""
        # Store multiple test records
        for i in range(3):
            test_metrics = {
                "timestamp": f"2024-01-01T{12+i:02d}:00:00",
                "hostname": "test-host",
                "cpu": {"percent": 50.0 + i * 10, "count": 4, "count_logical": 8},
                "memory": {
                    "total": 8589934592,
                    "available": 4294967296,
                    "percent": 60.0 + i * 5,
                    "used": 4294967296,
                    "free": 4294967296
                },
                "swap": {"total": 2147483648, "used": 0, "free": 2147483648, "percent": 0.0},
                "disk": []
            }
            
            payload = MetricsPayload(
                hostname="test-host",
                metrics=SystemMetrics(**test_metrics)
            )
            
            self.db.store_metrics(payload)
        
        # Get summary
        summary = self.db.get_summary_stats(hostname="test-host", hours=24)
        
        self.assertEqual(summary['total_records'], 3)
        self.assertAlmostEqual(summary['avg_cpu'], 60.0, places=1)  # (50+60+70)/3
        self.assertAlmostEqual(summary['avg_memory'], 67.5, places=1)  # (60+65+70)/3

    def test_cleanup_old_data(self):
        """Test data cleanup functionality."""
        # Store test data
        test_metrics = {
            "timestamp": "2024-01-01T12:00:00",
            "hostname": "test-host",
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
        
        payload = MetricsPayload(
            hostname="test-host",
            metrics=SystemMetrics(**test_metrics)
        )
        
        self.db.store_metrics(payload)
        
        # Cleanup with 0 days (should delete everything)
        deleted_count = self.db.cleanup_old_data(days_to_keep=0)
        
        self.assertEqual(deleted_count, 1)
        
        # Verify deletion
        with sqlite3.connect(self.temp_db.name) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM metrics")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 0)


class TestIngestionAPI(unittest.TestCase):
    """Test cases for the ingestion API endpoints."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("timestamp", data)

    def test_ingest_endpoint_valid_data(self):
        """Test ingesting valid metrics data."""
        test_payload = {
            "hostname": "test-host",
            "metrics": {
                "timestamp": "2024-01-01T12:00:00",
                "hostname": "test-host",
                "cpu": {"percent": 50.0, "count": 4, "count_logical": 8},
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
        
        response = self.client.post("/ingest", json=test_payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")

    def test_ingest_endpoint_invalid_data(self):
        """Test ingesting invalid metrics data."""
        test_payload = {
            "hostname": "test-host",
            "metrics": {
                "timestamp": "invalid-timestamp",
                "hostname": "test-host",
                "cpu": {"percent": "invalid"},  # Should be float
                "memory": {},  # Missing required fields
                "swap": {},  # Missing required fields
                "disk": []
            }
        }
        
        response = self.client.post("/ingest", json=test_payload)
        
        self.assertEqual(response.status_code, 422)  # Validation error

    def test_metrics_endpoint(self):
        """Test retrieving metrics."""
        # First ingest some data
        test_payload = {
            "hostname": "test-host",
            "metrics": {
                "timestamp": "2024-01-01T12:00:00",
                "hostname": "test-host",
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
        }
        
        self.client.post("/ingest", json=test_payload)
        
        # Now retrieve metrics
        response = self.client.get("/metrics")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["count"], 1)

    def test_summary_endpoint(self):
        """Test summary statistics endpoint."""
        response = self.client.get("/metrics/summary")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("summary", data)


if __name__ == '__main__':
    unittest.main()
