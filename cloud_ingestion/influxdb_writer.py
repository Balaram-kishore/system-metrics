#!/usr/bin/env python3
"""
InfluxDB Writer Module
Handles writing metrics data to InfluxDB
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import yaml
import os

logger = logging.getLogger(__name__)

class InfluxDBWriter:
    def __init__(self, config_path: str = "influxdb_config.yaml"):
        """Initialize InfluxDB writer with configuration."""
        self.config = self._load_config(config_path)
        self.client = None
        self.write_api = None
        self._connect()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load InfluxDB configuration from YAML file."""
        try:
            # Try relative to current directory first
            if os.path.exists(config_path):
                config_file = config_path
            else:
                # Try relative to script directory
                script_dir = os.path.dirname(os.path.abspath(__file__))
                config_file = os.path.join(script_dir, "..", config_path)
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            return config['influxdb']
        except Exception as e:
            logger.error(f"Failed to load InfluxDB config: {e}")
            raise
    
    def _connect(self):
        """Establish connection to InfluxDB."""
        try:
            self.client = InfluxDBClient(
                url=self.config['url'],
                token=self.config['token'],
                org=self.config['org'],
                timeout=self.config.get('timeout', 10) * 1000
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            logger.info("Connected to InfluxDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise
    
    def write_metrics(self, hostname: str, metrics: Dict[str, Any]) -> bool:
        """Write system metrics to InfluxDB."""
        try:
            points = []
            timestamp = datetime.fromisoformat(metrics['timestamp'].replace('Z', '+00:00'))
            
            # CPU metrics
            cpu_point = Point("cpu") \
                .tag("hostname", hostname) \
                .field("percent", float(metrics['cpu']['percent'])) \
                .field("count", int(metrics['cpu']['count'])) \
                .field("count_logical", int(metrics['cpu']['count_logical'])) \
                .time(timestamp)
            points.append(cpu_point)
            
            # Add load average if available
            if metrics['cpu'].get('load_avg'):
                load_avg = metrics['cpu']['load_avg']
                if len(load_avg) >= 3:
                    load_point = Point("load_avg") \
                        .tag("hostname", hostname) \
                        .field("load_1m", float(load_avg[0])) \
                        .field("load_5m", float(load_avg[1])) \
                        .field("load_15m", float(load_avg[2])) \
                        .time(timestamp)
                    points.append(load_point)
            
            # Memory metrics
            memory_point = Point("memory") \
                .tag("hostname", hostname) \
                .field("total", int(metrics['memory']['total'])) \
                .field("available", int(metrics['memory']['available'])) \
                .field("percent", float(metrics['memory']['percent'])) \
                .field("used", int(metrics['memory']['used'])) \
                .field("free", int(metrics['memory']['free'])) \
                .time(timestamp)
            
            # Add optional memory fields
            if 'buffers' in metrics['memory']:
                memory_point = memory_point.field("buffers", int(metrics['memory']['buffers']))
            if 'cached' in metrics['memory']:
                memory_point = memory_point.field("cached", int(metrics['memory']['cached']))
            
            points.append(memory_point)
            
            # Swap metrics
            swap_point = Point("swap") \
                .tag("hostname", hostname) \
                .field("total", int(metrics['swap']['total'])) \
                .field("used", int(metrics['swap']['used'])) \
                .field("free", int(metrics['swap']['free'])) \
                .field("percent", float(metrics['swap']['percent'])) \
                .time(timestamp)
            points.append(swap_point)
            
            # Disk metrics
            for disk in metrics['disk']:
                disk_point = Point("disk") \
                    .tag("hostname", hostname) \
                    .tag("device", disk['device']) \
                    .tag("mountpoint", disk['mountpoint']) \
                    .tag("fstype", disk['fstype']) \
                    .field("total", int(disk['total'])) \
                    .field("used", int(disk['used'])) \
                    .field("free", int(disk['free'])) \
                    .field("percent", float(disk['percent'])) \
                    .time(timestamp)
                points.append(disk_point)
            
            # Network metrics (if available)
            if metrics.get('network'):
                network_point = Point("network") \
                    .tag("hostname", hostname) \
                    .field("bytes_sent", int(metrics['network']['bytes_sent'])) \
                    .field("bytes_recv", int(metrics['network']['bytes_recv'])) \
                    .field("packets_sent", int(metrics['network']['packets_sent'])) \
                    .field("packets_recv", int(metrics['network']['packets_recv'])) \
                    .time(timestamp)
                
                # Add optional network error fields
                if 'errin' in metrics['network']:
                    network_point = network_point.field("errin", int(metrics['network']['errin']))
                if 'errout' in metrics['network']:
                    network_point = network_point.field("errout", int(metrics['network']['errout']))
                if 'dropin' in metrics['network']:
                    network_point = network_point.field("dropin", int(metrics['network']['dropin']))
                if 'dropout' in metrics['network']:
                    network_point = network_point.field("dropout", int(metrics['network']['dropout']))
                
                points.append(network_point)
            
            # Process metrics (if available)
            if metrics.get('top_processes'):
                for process in metrics['top_processes']:
                    process_point = Point("process") \
                        .tag("hostname", hostname) \
                        .tag("pid", str(process['pid'])) \
                        .tag("name", process['name']) \
                        .field("cpu_percent", float(process['cpu_percent'])) \
                        .field("memory_percent", float(process['memory_percent'])) \
                        .time(timestamp)
                    points.append(process_point)
            
            # Write all points to InfluxDB
            self.write_api.write(
                bucket=self.config['bucket'],
                org=self.config['org'],
                record=points
            )
            
            logger.debug(f"Successfully wrote {len(points)} metric points to InfluxDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write metrics to InfluxDB: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test InfluxDB connection."""
        try:
            # Try to ping the InfluxDB instance
            health = self.client.health()
            if health.status == "pass":
                logger.info("InfluxDB connection test successful")
                return True
            else:
                logger.error(f"InfluxDB health check failed: {health.status}")
                return False
        except Exception as e:
            logger.error(f"InfluxDB connection test failed: {e}")
            return False
    
    def close(self):
        """Close InfluxDB connection."""
        if self.client:
            self.client.close()
            logger.info("InfluxDB connection closed")

# Test function for standalone usage
if __name__ == "__main__":
    import json
    
    # Test configuration
    test_config = {
        'influxdb': {
            'url': 'http://localhost:8086',
            'token': 'your-token-here',
            'org': 'metrics-org',
            'bucket': 'system-metrics',
            'timeout': 10
        }
    }
    
    # Save test config
    with open('test_influxdb_config.yaml', 'w') as f:
        yaml.dump(test_config, f)
    
    try:
        # Initialize writer
        writer = InfluxDBWriter('test_influxdb_config.yaml')
        
        # Test connection
        if writer.test_connection():
            print("✅ InfluxDB connection successful")
        else:
            print("❌ InfluxDB connection failed")
        
        # Clean up
        writer.close()
        os.remove('test_influxdb_config.yaml')
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        if os.path.exists('test_influxdb_config.yaml'):
            os.remove('test_influxdb_config.yaml')
