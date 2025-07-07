// Dashboard JavaScript

class MetricsDashboard {
    constructor() {
        this.charts = {};
        this.refreshInterval = null;
        this.currentHost = '';
        this.currentTimeRange = 24;
        
        this.initializeCharts();
        this.setupEventListeners();
        this.loadHosts();
        this.loadData();
        this.startAutoRefresh();
    }

    initializeCharts() {
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        displayFormats: {
                            minute: 'HH:mm',
                            hour: 'HH:mm',
                            day: 'MM/DD HH:mm'
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 100
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        };

        // CPU Chart
        this.charts.cpu = new Chart(document.getElementById('cpuChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Usage (%)',
                    data: [],
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: chartOptions
        });

        // Memory Chart
        this.charts.memory = new Chart(document.getElementById('memoryChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Memory Usage (%)',
                    data: [],
                    borderColor: '#ffc107',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: chartOptions
        });

        // Disk Chart
        this.charts.disk = new Chart(document.getElementById('diskChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Disk Usage (%)',
                    data: [],
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: chartOptions
        });

        // Network Chart
        const networkOptions = { ...chartOptions };
        networkOptions.scales.y = {
            beginAtZero: true,
            ticks: {
                callback: function(value) {
                    return formatBytes(value);
                }
            }
        };

        this.charts.network = new Chart(document.getElementById('networkChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Bytes Sent',
                        data: [],
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        fill: false,
                        tension: 0.4
                    },
                    {
                        label: 'Bytes Received',
                        data: [],
                        borderColor: '#17a2b8',
                        backgroundColor: 'rgba(23, 162, 184, 0.1)',
                        fill: false,
                        tension: 0.4
                    }
                ]
            },
            options: networkOptions
        });
    }

    setupEventListeners() {
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadData();
        });

        document.getElementById('hostSelect').addEventListener('change', (e) => {
            this.currentHost = e.target.value;
            this.loadData();
        });

        document.getElementById('timeRange').addEventListener('change', (e) => {
            this.currentTimeRange = parseInt(e.target.value);
            this.loadData();
        });
    }

    async loadHosts() {
        try {
            const response = await fetch('/api/hosts');
            const data = await response.json();
            
            const hostSelect = document.getElementById('hostSelect');
            hostSelect.innerHTML = '<option value="">All Hosts</option>';
            
            data.hosts.forEach(host => {
                const option = document.createElement('option');
                option.value = host;
                option.textContent = host;
                hostSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading hosts:', error);
        }
    }

    async loadData() {
        this.showLoading(true);
        this.hideError();

        try {
            // Load metrics data
            const params = new URLSearchParams({
                hours: this.currentTimeRange.toString()
            });
            
            if (this.currentHost) {
                params.append('hostname', this.currentHost);
            }

            const [metricsResponse, summaryResponse, healthResponse] = await Promise.all([
                fetch(`/api/metrics?${params}`),
                fetch(`/api/summary?${params}`),
                fetch('/api/health')
            ]);

            const metricsData = await metricsResponse.json();
            const summaryData = await summaryResponse.json();
            const healthData = await healthResponse.json();

            if (metricsData.status === 'success') {
                this.updateCharts(metricsData.data);
                this.updateSummaryCards(summaryData.summary, metricsData.count);
            } else {
                throw new Error('Failed to load metrics data');
            }

            this.updateHealthStatus(healthData);

        } catch (error) {
            console.error('Error loading data:', error);
            this.showError(`Failed to load data: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    updateCharts(data) {
        const timestamps = data.timestamps.map(ts => new Date(ts));

        // Update CPU chart
        this.charts.cpu.data.labels = timestamps;
        this.charts.cpu.data.datasets[0].data = data.cpu_data;
        this.charts.cpu.update('none');

        // Update Memory chart
        this.charts.memory.data.labels = timestamps;
        this.charts.memory.data.datasets[0].data = data.memory_data;
        this.charts.memory.update('none');

        // Update Disk chart
        this.charts.disk.data.labels = timestamps;
        this.charts.disk.data.datasets[0].data = data.disk_data;
        this.charts.disk.update('none');

        // Update Network chart
        this.charts.network.data.labels = timestamps;
        this.charts.network.data.datasets[0].data = data.network_data.sent;
        this.charts.network.data.datasets[1].data = data.network_data.received;
        this.charts.network.update('none');
    }

    updateSummaryCards(summary, dataPoints) {
        document.getElementById('avgCpu').textContent = 
            summary.avg_cpu ? `${summary.avg_cpu.toFixed(1)}%` : '--%';
        
        document.getElementById('avgMemory').textContent = 
            summary.avg_memory ? `${summary.avg_memory.toFixed(1)}%` : '--%';
        
        document.getElementById('dataPoints').textContent = dataPoints || '--';
    }

    updateHealthStatus(healthData) {
        const statusElement = document.getElementById('serviceStatus');
        const metricsHealth = healthData.metrics_service;
        
        if (metricsHealth.status === 'healthy') {
            statusElement.textContent = '✅ Online';
            statusElement.parentElement.parentElement.className = 'card bg-success text-white';
        } else {
            statusElement.textContent = '❌ Offline';
            statusElement.parentElement.parentElement.className = 'card bg-danger text-white';
        }
    }

    showLoading(show) {
        document.getElementById('loadingIndicator').style.display = show ? 'block' : 'none';
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorAlert').style.display = 'block';
    }

    hideError() {
        document.getElementById('errorAlert').style.display = 'none';
    }

    startAutoRefresh() {
        // Refresh every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadData();
        }, 30000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
}

// Utility function to format bytes
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new MetricsDashboard();
});
