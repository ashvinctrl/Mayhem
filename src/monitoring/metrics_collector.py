import logging
import time
import requests
import psutil
import json
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MetricsCollector:
    """Production-ready metrics collector with comprehensive error handling"""
    
    def __init__(self, prometheus_url: Optional[str] = None):
        self.metrics = {}
        self.prometheus_url = prometheus_url or "http://localhost:9090"
        self.last_collection_time = None
        self.collection_errors = 0
        self.max_collection_errors = 5
        
        logger.info("MetricsCollector initialized")
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system metrics with error handling"""
        metrics = {}
        
        try:
            # CPU metrics
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count()
                cpu_freq = psutil.cpu_freq()
                
                metrics['cpu'] = {
                    'usage_percent': cpu_percent,
                    'count': cpu_count,
                    'frequency': cpu_freq._asdict() if cpu_freq else None
                }
            except (psutil.Error, AttributeError) as e:
                logger.warning(f"Failed to collect CPU metrics: {e}")
                metrics['cpu'] = {'error': str(e)}
            
            # Memory metrics
            try:
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                metrics['memory'] = {
                    'total': memory.total,
                    'available': memory.available,
                    'percent': memory.percent,
                    'used': memory.used,
                    'free': memory.free
                }
                metrics['swap'] = {
                    'total': swap.total,
                    'used': swap.used,
                    'free': swap.free,
                    'percent': swap.percent
                }
            except (psutil.Error, AttributeError) as e:
                logger.warning(f"Failed to collect memory metrics: {e}")
                metrics['memory'] = {'error': str(e)}
                metrics['swap'] = {'error': str(e)}
            
            # Disk metrics
            try:
                import os
                disk_path = 'C:' if os.name == 'nt' else '/'
                disk = psutil.disk_usage(disk_path)
                disk_io = psutil.disk_io_counters()
                
                metrics['disk'] = {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100 if disk.total > 0 else 0
                }
                
                if disk_io:
                    metrics['disk_io'] = {
                        'read_count': disk_io.read_count,
                        'write_count': disk_io.write_count,
                        'read_bytes': disk_io.read_bytes,
                        'write_bytes': disk_io.write_bytes
                    }
            except (psutil.Error, FileNotFoundError, PermissionError) as e:
                logger.warning(f"Failed to collect disk metrics: {e}")
                metrics['disk'] = {'error': str(e)}
            
            # Network metrics
            try:
                net_io = psutil.net_io_counters()
                net_connections = len(psutil.net_connections())
                
                if net_io:
                    metrics['network'] = {
                        'bytes_sent': net_io.bytes_sent,
                        'bytes_recv': net_io.bytes_recv,
                        'packets_sent': net_io.packets_sent,
                        'packets_recv': net_io.packets_recv,
                        'connections': net_connections
                    }
            except (psutil.Error, psutil.AccessDenied) as e:
                logger.warning(f"Failed to collect network metrics: {e}")
                metrics['network'] = {'error': str(e)}
            
            # Process metrics
            try:
                processes = list(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']))
                metrics['processes'] = {
                    'total_count': len(processes),
                    'running_count': len([p for p in processes if p.info['cpu_percent'] > 0]),
                    'high_cpu_processes': [
                        {'pid': p.info['pid'], 'name': p.info['name'], 'cpu_percent': p.info['cpu_percent']}
                        for p in processes 
                        if p.info.get('cpu_percent', 0) > 10
                    ][:5]  # Top 5 CPU consumers
                }
            except (psutil.Error, psutil.AccessDenied) as e:
                logger.warning(f"Failed to collect process metrics: {e}")
                metrics['processes'] = {'error': str(e)}
            
            # System load
            try:
                if hasattr(psutil, 'getloadavg'):
                    load_avg = psutil.getloadavg()
                    metrics['load_average'] = {
                        '1min': load_avg[0],
                        '5min': load_avg[1],
                        '15min': load_avg[2]
                    }
            except (psutil.Error, AttributeError) as e:
                logger.debug(f"Load average not available: {e}")
            
            # Boot time and uptime
            try:
                boot_time = psutil.boot_time()
                uptime = time.time() - boot_time
                metrics['system'] = {
                    'boot_time': boot_time,
                    'uptime_seconds': uptime,
                    'uptime_hours': uptime / 3600
                }
            except psutil.Error as e:
                logger.warning(f"Failed to collect system metrics: {e}")
                metrics['system'] = {'error': str(e)}
            
            # Add collection metadata
            metrics['collection'] = {
                'timestamp': datetime.utcnow().isoformat(),
                'collection_time': time.time(),
                'errors': self.collection_errors
            }
            
            self.last_collection_time = time.time()
            self.collection_errors = 0  # Reset on successful collection
            self.metrics = metrics
            
            logger.debug("Metrics collection completed successfully")
            return metrics
            
        except Exception as e:
            self.collection_errors += 1
            logger.error(f"Critical error during metrics collection: {e}")
            
            if self.collection_errors >= self.max_collection_errors:
                logger.critical(f"Metrics collection failed {self.max_collection_errors} consecutive times")
            
            # Return minimal fallback metrics
            return {
                'cpu': {'usage_percent': 0, 'error': 'Collection failed'},
                'memory': {'usage_percent': 0, 'error': 'Collection failed'},
                'collection': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'errors': self.collection_errors,
                    'error_message': str(e)
                }
            }
    
    def send_to_prometheus(self, metrics: Dict[str, Any]) -> bool:
        """Send metrics to Prometheus with error handling and retries"""
        if not metrics:
            logger.warning("No metrics to send to Prometheus")
            return False
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Convert metrics to Prometheus format
                prometheus_data = self._format_for_prometheus(metrics)
                
                # Send to Prometheus pushgateway (if configured)
                if self.prometheus_url and 'pushgateway' in self.prometheus_url:
                    response = requests.post(
                        f"{self.prometheus_url}/metrics/job/chaos_platform",
                        data=prometheus_data,
                        headers={'Content-Type': 'text/plain'},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        logger.debug("Metrics successfully sent to Prometheus")
                        return True
                    else:
                        logger.warning(f"Prometheus returned status {response.status_code}: {response.text}")
                        
                else:
                    # If no pushgateway, just validate format and return success
                    if self._validate_metrics(metrics):
                        logger.debug("Metrics validated successfully")
                        return True
                    else:
                        logger.warning("Metrics validation failed")
                        return False
                        
            except requests.exceptions.RequestException as e:
                retry_count += 1
                logger.warning(f"Network error sending metrics to Prometheus (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    time.sleep(2 ** retry_count)  # Exponential backoff
            except Exception as e:
                logger.error(f"Unexpected error sending metrics to Prometheus: {e}")
                break
        
        logger.error(f"Failed to send metrics to Prometheus after {max_retries} attempts")
        return False
    
    def _format_for_prometheus(self, metrics: Dict[str, Any]) -> str:
        """Format metrics for Prometheus exposition format"""
        try:
            lines = []
            timestamp = int(time.time() * 1000)  # Prometheus expects milliseconds
            
            # CPU metrics
            if 'cpu' in metrics and 'usage_percent' in metrics['cpu']:
                lines.append(f"chaos_platform_cpu_usage_percent {metrics['cpu']['usage_percent']} {timestamp}")
            
            # Memory metrics
            if 'memory' in metrics and 'percent' in metrics['memory']:
                lines.append(f"chaos_platform_memory_usage_percent {metrics['memory']['percent']} {timestamp}")
                lines.append(f"chaos_platform_memory_total_bytes {metrics['memory']['total']} {timestamp}")
                lines.append(f"chaos_platform_memory_available_bytes {metrics['memory']['available']} {timestamp}")
            
            # Disk metrics
            if 'disk' in metrics and 'percent' in metrics['disk']:
                lines.append(f"chaos_platform_disk_usage_percent {metrics['disk']['percent']} {timestamp}")
                lines.append(f"chaos_platform_disk_total_bytes {metrics['disk']['total']} {timestamp}")
                lines.append(f"chaos_platform_disk_free_bytes {metrics['disk']['free']} {timestamp}")
            
            # Network metrics
            if 'network' in metrics and 'bytes_sent' in metrics['network']:
                lines.append(f"chaos_platform_network_bytes_sent_total {metrics['network']['bytes_sent']} {timestamp}")
                lines.append(f"chaos_platform_network_bytes_recv_total {metrics['network']['bytes_recv']} {timestamp}")
            
            # Process metrics
            if 'processes' in metrics and 'total_count' in metrics['processes']:
                lines.append(f"chaos_platform_processes_total {metrics['processes']['total_count']} {timestamp}")
            
            # Collection errors
            if 'collection' in metrics and 'errors' in metrics['collection']:
                lines.append(f"chaos_platform_collection_errors_total {metrics['collection']['errors']} {timestamp}")
            
            return '\n'.join(lines) + '\n'
            
        except Exception as e:
            logger.error(f"Failed to format metrics for Prometheus: {e}")
            return ""
    
    def _validate_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Validate that metrics contain expected structure"""
        try:
            required_sections = ['cpu', 'memory', 'collection']
            
            for section in required_sections:
                if section not in metrics:
                    logger.warning(f"Missing required metrics section: {section}")
                    return False
            
            # Validate that we have either valid data or error information
            for section_name, section_data in metrics.items():
                if isinstance(section_data, dict):
                    if not section_data:  # Empty dict
                        logger.warning(f"Empty metrics section: {section_name}")
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Metrics validation failed: {e}")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the metrics collector"""
        return {
            'status': 'healthy' if self.collection_errors < self.max_collection_errors else 'degraded',
            'last_collection_time': self.last_collection_time,
            'collection_errors': self.collection_errors,
            'max_collection_errors': self.max_collection_errors,
            'prometheus_url': self.prometheus_url
        }