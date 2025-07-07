from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Metrics Dashboard", description="Real-time system metrics visualization")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configuration
METRICS_API_URL = "http://localhost:8000"  # URL of the metrics ingestion service

class MetricsClient:
    """Client for fetching metrics from the ingestion service."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
    
    def get_recent_metrics(self, hostname: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """Fetch recent metrics from the API."""
        try:
            params = {"hours": hours}
            if hostname:
                params["hostname"] = hostname
            
            response = requests.get(f"{self.base_url}/metrics", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            return {"status": "error", "metrics": [], "count": 0}
    
    def get_summary_stats(self, hostname: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """Fetch summary statistics from the API."""
        try:
            params = {"hours": hours}
            if hostname:
                params["hostname"] = hostname
            
            response = requests.get(f"{self.base_url}/metrics/summary", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching summary: {e}")
            return {"status": "error", "summary": {}}
    
    def get_health(self) -> Dict[str, Any]:
        """Check health of the metrics service."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            return {"status": "unhealthy", "error": str(e)}

# Global metrics client
metrics_client = MetricsClient(METRICS_API_URL)

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/metrics")
async def api_get_metrics(hostname: Optional[str] = None, hours: int = 24):
    """API endpoint to get metrics data for the dashboard."""
    try:
        data = metrics_client.get_recent_metrics(hostname=hostname, hours=hours)
        
        if data["status"] != "success":
            raise HTTPException(status_code=500, detail="Failed to fetch metrics")
        
        # Process metrics for chart display
        processed_data = process_metrics_for_charts(data["metrics"])
        
        return {
            "status": "success",
            "data": processed_data,
            "count": data["count"],
            "hostname": hostname,
            "hours": hours
        }
    except Exception as e:
        logger.error(f"Error in API metrics endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/summary")
async def api_get_summary(hostname: Optional[str] = None, hours: int = 24):
    """API endpoint to get summary statistics."""
    try:
        data = metrics_client.get_summary_stats(hostname=hostname, hours=hours)
        
        if data["status"] != "success":
            raise HTTPException(status_code=500, detail="Failed to fetch summary")
        
        return data
    except Exception as e:
        logger.error(f"Error in API summary endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/hosts")
async def api_get_hosts():
    """Get list of available hosts."""
    try:
        # Get recent metrics to extract hostnames
        data = metrics_client.get_recent_metrics(hours=24)
        
        if data["status"] != "success":
            return {"hosts": []}
        
        # Extract unique hostnames
        hostnames = set()
        for metric in data["metrics"]:
            if "hostname" in metric:
                hostnames.add(metric["hostname"])
        
        return {"hosts": sorted(list(hostnames))}
    except Exception as e:
        logger.error(f"Error getting hosts: {e}")
        return {"hosts": []}

@app.get("/api/health")
async def api_health():
    """Health check for the dashboard and metrics service."""
    dashboard_health = {
        "service": "dashboard",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    metrics_health = metrics_client.get_health()
    
    return {
        "dashboard": dashboard_health,
        "metrics_service": metrics_health
    }

def process_metrics_for_charts(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process raw metrics data for chart visualization."""
    if not metrics:
        return {
            "timestamps": [],
            "cpu_data": [],
            "memory_data": [],
            "disk_data": [],
            "network_data": []
        }
    
    # Sort metrics by timestamp
    sorted_metrics = sorted(metrics, key=lambda x: x.get("timestamp", ""))
    
    timestamps = []
    cpu_data = []
    memory_data = []
    disk_data = []
    network_sent = []
    network_recv = []
    
    for metric in sorted_metrics:
        try:
            # Parse timestamp
            timestamp = metric.get("timestamp", "")
            timestamps.append(timestamp)
            
            # CPU data
            cpu_data.append(metric.get("cpu_percent", 0))
            
            # Memory data
            memory_data.append(metric.get("memory_percent", 0))
            
            # Disk data (average across all disks)
            disk_info = metric.get("disk_data")
            if disk_info:
                try:
                    disk_list = json.loads(disk_info) if isinstance(disk_info, str) else disk_info
                    if disk_list:
                        avg_disk = sum(disk.get("percent", 0) for disk in disk_list) / len(disk_list)
                        disk_data.append(avg_disk)
                    else:
                        disk_data.append(0)
                except:
                    disk_data.append(0)
            else:
                disk_data.append(0)
            
            # Network data
            network_info = metric.get("network_data")
            if network_info:
                try:
                    network = json.loads(network_info) if isinstance(network_info, str) else network_info
                    network_sent.append(network.get("bytes_sent", 0))
                    network_recv.append(network.get("bytes_recv", 0))
                except:
                    network_sent.append(0)
                    network_recv.append(0)
            else:
                network_sent.append(0)
                network_recv.append(0)
                
        except Exception as e:
            logger.warning(f"Error processing metric: {e}")
            continue
    
    return {
        "timestamps": timestamps,
        "cpu_data": cpu_data,
        "memory_data": memory_data,
        "disk_data": disk_data,
        "network_data": {
            "sent": network_sent,
            "received": network_recv
        }
    }

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description='Metrics Dashboard')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--metrics-url', default='http://localhost:8000', 
                       help='URL of the metrics ingestion service')
    
    args = parser.parse_args()
    
    # Update metrics client URL
    global metrics_client
    metrics_client = MetricsClient(args.metrics_url)
    
    uvicorn.run(app, host=args.host, port=args.port)
