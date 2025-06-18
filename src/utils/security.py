import os
import logging
from functools import wraps
from flask import request, jsonify
import hashlib
import hmac
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('CHAOS_API_KEY', 'default_dev_key')
        self.rate_limit_storage = {}
        
    def require_api_key(self, f):
        """Decorator to require API key authentication"""
        @wraps(f)
        def decorated(*args, **kwargs):
            provided_key = request.headers.get('X-API-Key') or request.args.get('api_key')
            
            if not provided_key:
                logger.warning(f"API key missing for {request.endpoint} from {request.remote_addr}")
                return jsonify({'error': 'API key required'}), 401
                
            if not self._verify_api_key(provided_key):
                logger.warning(f"Invalid API key for {request.endpoint} from {request.remote_addr}")
                return jsonify({'error': 'Invalid API key'}), 401
                
            return f(*args, **kwargs)
        return decorated
    
    def rate_limit(self, requests_per_minute=60):
        """Decorator to apply rate limiting"""
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                client_ip = request.remote_addr
                current_time = datetime.now()
                
                # Clean old entries
                self._cleanup_rate_limit_storage(current_time)
                
                # Check rate limit
                if not self._check_rate_limit(client_ip, current_time, requests_per_minute):
                    logger.warning(f"Rate limit exceeded for {client_ip} on {request.endpoint}")
                    return jsonify({'error': 'Rate limit exceeded'}), 429
                
                return f(*args, **kwargs)
            return decorated
        return decorator
    
    def _verify_api_key(self, provided_key):
        """Verify API key using secure comparison"""
        return hmac.compare_digest(self.api_key, provided_key)
    
    def _check_rate_limit(self, client_ip, current_time, requests_per_minute):
        """Check if client has exceeded rate limit"""
        if client_ip not in self.rate_limit_storage:
            self.rate_limit_storage[client_ip] = []
        
        # Add current request
        self.rate_limit_storage[client_ip].append(current_time)
        
        # Count requests in last minute
        minute_ago = current_time - timedelta(minutes=1)
        recent_requests = [
            req_time for req_time in self.rate_limit_storage[client_ip]
            if req_time > minute_ago
        ]
        
        self.rate_limit_storage[client_ip] = recent_requests
        return len(recent_requests) <= requests_per_minute
    
    def _cleanup_rate_limit_storage(self, current_time):
        """Clean up old rate limit entries"""
        hour_ago = current_time - timedelta(hours=1)
        for client_ip in list(self.rate_limit_storage.keys()):
            self.rate_limit_storage[client_ip] = [
                req_time for req_time in self.rate_limit_storage[client_ip]
                if req_time > hour_ago
            ]
            if not self.rate_limit_storage[client_ip]:
                del self.rate_limit_storage[client_ip]

# Input validation utilities
def validate_chaos_input(data):
    """Validate chaos injection input"""
    if not isinstance(data, dict):
        return False, "Invalid JSON data"
    
    scenario = data.get('scenario', '')
    duration = data.get('duration', 0)
    intensity = data.get('intensity', '')
    
    # Validate scenario
    valid_scenarios = [
        'cpu_spike', 'memory_leak', 'disk_fill', 'network_latency',
        'network_partition', 'process_kill', 'container_restart',
        'database_slowdown', 'api_timeout', 'ssl_certificate_expired',
        'dns_failure', 'storage_corruption', 'kubernetes_pod_eviction',
        'service_discovery_failure', 'load_balancer_failure'
    ]
    
    if scenario not in valid_scenarios:
        return False, f"Invalid scenario. Must be one of: {', '.join(valid_scenarios)}"
    
    # Validate duration
    try:
        duration = int(duration)
        if duration < 1 or duration > 300:
            return False, "Duration must be between 1 and 300 seconds"
    except (ValueError, TypeError):
        return False, "Duration must be a valid integer"
    
    # Validate intensity
    if intensity not in ['low', 'medium', 'high']:
        return False, "Intensity must be 'low', 'medium', or 'high'"
    
    return True, "Valid input"

def sanitize_log_data(data):
    """Sanitize data for logging to prevent log injection"""
    if isinstance(data, str):
        # Remove or escape potential log injection characters
        return data.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return str(data)
