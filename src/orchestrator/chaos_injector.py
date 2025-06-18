from flask import Flask, jsonify, Response, send_from_directory, render_template
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Gauge
import random
import psutil
import threading
import time
import os
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our custom modules
try:
    from utils.security import SecurityManager, validate_chaos_input, sanitize_log_data
    from models.database import db, init_database, ChaosExperiment, SystemMetrics
    from ai_models.nlp_log_analysis import NLPLogAnalyzer
except ImportError as e:
    print(f"Warning: Some modules not available: {e}")
    # Fallback for development
    class SecurityManager:
        def require_api_key(self, f): return f
        def rate_limit(self, requests_per_minute=60): return lambda f: f
    
    def validate_chaos_input(data): return True, "Valid"

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '../static'), static_url_path='/static')

# Configure Flask app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key_2025')

# Initialize security
security = SecurityManager()

# Initialize database
try:
    init_database(app)
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")

# Initialize AI analyzer
ai_analyzer = NLPLogAnalyzer()

# Prometheus metrics - unique names to avoid conflicts
CPU_USAGE = Gauge('system_cpu_percent', 'Current CPU usage percentage')
MEMORY_USAGE = Gauge('system_memory_percent', 'Current memory usage percentage')
CHAOS_REQUESTS_COUNT = Counter('chaos_orchestrator_requests_total', 'Total number of requests to the chaos orchestrator')
CHAOS_INJECTIONS_COUNT = Counter('chaos_injections_total', 'Total number of chaos injections performed')
CHAOS_SCENARIOS_COUNT = Counter('chaos_scenarios_total', 'Total number of scenarios executed', ['scenario_type'])

def update_system_metrics():
    """Background thread to update system metrics"""
    while True:
        try:
            CPU_USAGE.set(psutil.cpu_percent(interval=1))
            MEMORY_USAGE.set(psutil.virtual_memory().percent)
        except Exception as e:
            print(f"Error updating metrics: {e}")
        time.sleep(5)

# Start metrics collection thread
metrics_thread = threading.Thread(target=update_system_metrics, daemon=True)
metrics_thread.start()

# Humorous root endpoint
@app.route("/")
def home():
    # Redirect to the UI
    return send_from_directory(app.static_folder, "index.html")

# UI route (for direct /ui access)
@app.route("/ui")
def ui():
    return send_from_directory(app.static_folder, "index.html")


# Chaos injection endpoint
from flask import request

@app.route("/inject", methods=["POST"])
@security.require_api_key
@security.rate_limit(requests_per_minute=30)
def inject():
    data = request.get_json(force=True)
    
    # Validate input
    is_valid, error_message = validate_chaos_input(data)
    if not is_valid:
        logger.warning(f"Invalid chaos input: {error_message}")
        return jsonify({'error': error_message}), 400
    
    scenario = data.get("scenario", "cpu_spike")
    duration = int(data.get("duration", 10))
    intensity = data.get("intensity", "medium")
    
    # Create experiment record
    experiment = None
    try:
        # Get current metrics before chaos
        current_metrics = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent
        }
        
        experiment = ChaosExperiment(
            scenario=scenario,
            duration=duration,
            intensity=intensity,
            metrics_before=json.dumps(current_metrics),
            user_agent=request.headers.get('User-Agent', ''),
            client_ip=request.remote_addr
        )
        db.session.add(experiment)
        db.session.commit()
        
        logger.info(f"Starting chaos experiment {experiment.id}: {scenario} ({intensity}) for {duration}s")
    except Exception as e:
        logger.error(f"Failed to create experiment record: {e}")
    
    # Increment chaos injection counter
    CHAOS_INJECTIONS_COUNT.inc()
    CHAOS_SCENARIOS_COUNT.labels(scenario_type=scenario).inc()
    
    result = {}
    
    if scenario == "cpu_spike":
        def cpu_stress():
            end_time = time.time() + duration
            thread_count = {"low": 2, "medium": 4, "high": 8}[intensity]
            def burn():
                while time.time() < end_time:
                    pass
            threads = [threading.Thread(target=burn) for _ in range(thread_count)]
            for t in threads: t.start()
            for t in threads: t.join()
        threading.Thread(target=cpu_stress).start()
        result = {"result": f"CPU spike ({intensity}) injected for {duration}s", "scenario": scenario}
    
    elif scenario == "memory_leak":
        def mem_stress():
            multiplier = {"low": 5000, "medium": 10000, "high": 20000}[intensity]
            leaker = []
            for i in range(duration * multiplier):
                leaker.append(' ' * 1024)
                time.sleep(0.001)
            time.sleep(duration)
            del leaker
        threading.Thread(target=mem_stress).start()
        result = {"result": f"Memory leak ({intensity}) injected for {duration}s", "scenario": scenario}
    
    elif scenario == "disk_fill":
        def disk_stress():
            try:
                size_mb = {"low": 50, "medium": 100, "high": 200}[intensity]
                temp_files = []
                for i in range(size_mb):
                    filename = f"/tmp/chaos_disk_{i}.tmp"
                    with open(filename, 'w') as f:
                        f.write('x' * (1024 * 1024))  # 1MB file
                    temp_files.append(filename)
                time.sleep(duration)
                # Cleanup
                for f in temp_files:
                    try:
                        import os
                        os.remove(f)
                    except:
                        pass
            except Exception as e:
                print(f"Disk fill error: {e}")
        threading.Thread(target=disk_stress).start()
        result = {"result": f"Disk fill ({intensity}) injected for {duration}s", "scenario": scenario}
    
    elif scenario == "network_latency":
        # Simulate network latency by adding delays to responses
        def network_delay():
            import time
            delay_ms = {"low": 100, "medium": 500, "high": 1000}[intensity]
            # Store original response time
            end_time = time.time() + duration
            while time.time() < end_time:
                time.sleep(delay_ms / 1000)
        threading.Thread(target=network_delay).start()
        result = {"result": f"Network latency ({intensity}) injected for {duration}s", "scenario": scenario}
    
    elif scenario == "api_timeout":
        def timeout_simulation():
            timeout_duration = {"low": 5, "medium": 10, "high": 30}[intensity]
            time.sleep(min(timeout_duration, duration))
        threading.Thread(target=timeout_simulation).start()
        result = {"result": f"API timeout ({intensity}) simulated for {duration}s", "scenario": scenario}
    
    elif scenario == "process_kill":
        # Simulate process instability
        def process_chaos():
            # This is a safe simulation - just sleeps
            kill_delay = {"low": 30, "medium": 15, "high": 5}[intensity]
            time.sleep(min(kill_delay, duration))
        threading.Thread(target=process_chaos).start()
        result = {"result": f"Process instability ({intensity}) simulated for {duration}s", "scenario": scenario}
    
    elif scenario == "database_slowdown":
        def db_slowdown():
            # Simulate database connection delays
            query_delay = {"low": 0.1, "medium": 0.5, "high": 2.0}[intensity]
            end_time = time.time() + duration
            while time.time() < end_time:
                time.sleep(query_delay)
        threading.Thread(target=db_slowdown).start()
        result = {"result": f"Database slowdown ({intensity}) injected for {duration}s", "scenario": scenario}
    
    else:
        # For unimplemented scenarios, provide realistic simulation
        simulation_scenarios = {
            "network_partition": "Network partition simulation",
            "container_restart": "Container restart simulation", 
            "ssl_certificate_expired": "SSL certificate expiry simulation",
            "dns_failure": "DNS resolution failure simulation",
            "storage_corruption": "Storage corruption simulation",
            "kubernetes_pod_eviction": "Kubernetes pod eviction simulation",
            "service_discovery_failure": "Service discovery failure simulation",
            "load_balancer_failure": "Load balancer failure simulation"
        }
        
        scenario_name = simulation_scenarios.get(scenario, scenario)
        
        def generic_chaos():
            # Generic chaos simulation with variable intensity
            impact_duration = {"low": duration * 0.5, "medium": duration * 0.75, "high": duration}[intensity]
            time.sleep(impact_duration)
        
        threading.Thread(target=generic_chaos).start()
        result = {"result": f"{scenario_name} ({intensity}) executed for {duration}s", "scenario": scenario}
    
    return jsonify(result)


# Available chaos scenarios endpoint
@app.route("/scenarios")
def scenarios():
    # Comprehensive list of real-world chaos scenarios
    available = [
        "cpu_spike",
        "memory_leak", 
        "disk_fill",
        "network_latency",
        "network_partition",
        "process_kill",
        "container_restart",
        "database_slowdown",
        "api_timeout",
        "ssl_certificate_expired",
        "dns_failure",
        "storage_corruption",
        "kubernetes_pod_eviction",
        "service_discovery_failure",
        "load_balancer_failure"
    ]
    return jsonify({"scenarios": available})


# Humorous health check endpoint
@app.route("/health")
def health():
    health_states = [
        "healthy (for now)",
        "alive and causing trouble",
        "operational, but plotting chaos",
        "all systems nominal (but not for long)",
        "fit as a fiddle in a tornado"
    ]
    return jsonify({"status": random.choice(health_states)}), 200


# Humorous metrics endpoint
@app.route("/metrics")
def metrics():
    CHAOS_REQUESTS_COUNT.inc()
    # Easter egg: Occasionally return a joke metric
    if random.randint(1, 20) == 10:
        return Response("# HELP mayhem_joke_metric Number of times chaos made us laugh\n# TYPE mayhem_joke_metric counter\nmayhem_joke_metric 42\n", mimetype=CONTENT_TYPE_LATEST)
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route("/system-status")
def system_status():
    """Comprehensive system status endpoint"""
    try:
        # Get detailed system information
        cpu_info = {
            "usage_percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        }
        
        memory_info = psutil.virtual_memory()._asdict()
        disk_info = psutil.disk_usage('/')._asdict()
        
        # Network statistics
        network_info = psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
        
        # Process information
        process_info = {
            "running_processes": len(psutil.pids()),
            "current_process": {
                "cpu_percent": psutil.Process().cpu_percent(),
                "memory_percent": psutil.Process().memory_percent(),
                "num_threads": psutil.Process().num_threads()
            }
        }
        
        return jsonify({
            "timestamp": time.time(),
            "status": "healthy",
            "cpu": cpu_info,
            "memory": memory_info,
            "disk": disk_info,
            "network": network_info,
            "processes": process_info,
            "uptime": time.time() - psutil.boot_time()
        })
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500

@app.route("/chaos-history")
def chaos_history():
    """Return history of chaos injections"""
    # In a real implementation, this would come from a database
    # For now, return mock data
    history = [
        {
            "timestamp": time.time() - 3600,
            "scenario": "cpu_spike",
            "duration": 30,
            "intensity": "medium",
            "status": "completed",
            "impact_score": 7.5
        },
        {
            "timestamp": time.time() - 1800,
            "scenario": "memory_leak", 
            "duration": 60,
            "intensity": "high",
            "status": "completed",
            "impact_score": 8.9
        }
    ]
    return jsonify({"history": history})

if __name__ == "__main__":
    print("\n[Mayhem] Starting the orchestrator... Hold on to your packets!\n")
    app.run(host="0.0.0.0", port=5000)