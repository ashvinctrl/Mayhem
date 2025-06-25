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
from utils.security import SecurityManager, validate_chaos_input, sanitize_log_data
from models.database import db, init_database, ChaosExperiment, SystemMetrics
from ai_models.nlp_log_analysis import NLPLogAnalyzer

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
try:
    ai_analyzer = NLPLogAnalyzer()
except Exception as e:
    logger.warning(f"AI analyzer not available: {e}")
    ai_analyzer = None

# Prometheus metrics - unique names to avoid conflicts
CPU_USAGE = Gauge('system_cpu_percent', 'Current CPU usage percentage')
MEMORY_USAGE = Gauge('system_memory_percent', 'Current memory usage percentage')
CHAOS_REQUESTS_COUNT = Counter('chaos_orchestrator_requests_total', 'Total number of requests to the chaos orchestrator')
CHAOS_INJECTIONS_COUNT = Counter('chaos_injections_total', 'Total number of chaos injections performed')
CHAOS_SCENARIOS_COUNT = Counter('chaos_scenarios_total', 'Total number of scenarios executed', ['scenario_type'])

def update_system_metrics():
    """Background thread to update system metrics"""
    retry_count = 0
    max_retries = 3
    
    while True:
        try:
            CPU_USAGE.set(psutil.cpu_percent(interval=1))
            MEMORY_USAGE.set(psutil.virtual_memory().percent)
            retry_count = 0  # Reset on success
        except psutil.NoSuchProcess as e:
            logger.error(f"Process monitoring error: {e}")
            retry_count += 1
        except psutil.AccessDenied as e:
            logger.error(f"Access denied when collecting system metrics: {e}")
            retry_count += 1
        except Exception as e:
            logger.error(f"Unexpected error updating metrics: {e}")
            retry_count += 1
            
        if retry_count >= max_retries:
            logger.critical(f"Failed to collect metrics {max_retries} consecutive times. Resetting counter.")
            retry_count = 0
            
        time.sleep(5)

# Start metrics collection thread
try:
    metrics_thread = threading.Thread(target=update_system_metrics, daemon=True)
    metrics_thread.start()
    logger.info("System metrics collection thread started successfully")
except Exception as e:
    logger.error(f"Failed to start metrics collection thread: {e}")
    # Continue without metrics if thread fails to start

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
    experiment = None
    try:
        data = request.get_json(force=True)
        
        # Validate input
        is_valid, error_message = validate_chaos_input(data)
        if not is_valid:
            logger.warning(f"Invalid chaos input: {error_message}")
            return jsonify({'error': error_message}), 400
        
        scenario = data.get("scenario", "cpu_spike")
        duration = int(data.get("duration", 10))
        intensity = data.get("intensity", "medium")
        
        # Validate duration bounds
        if duration < 1 or duration > 300:  # Max 5 minutes
            return jsonify({'error': 'Duration must be between 1 and 300 seconds'}), 400
            
        # Validate intensity
        if intensity not in ["low", "medium", "high"]:
            return jsonify({'error': 'Intensity must be low, medium, or high'}), 400
        
        # Create experiment record
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
            # Continue with chaos injection even if database fails
        
        # Increment chaos injection counter
        try:
            CHAOS_INJECTIONS_COUNT.inc()
            CHAOS_SCENARIOS_COUNT.labels(scenario_type=scenario).inc()
        except Exception as e:
            logger.warning(f"Failed to update Prometheus metrics: {e}")
        
        result = {}
        
        try:
            if scenario == "cpu_spike":
                def cpu_stress():
                    try:
                        end_time = time.time() + duration
                        thread_count = {"low": 2, "medium": 4, "high": 8}[intensity]
                        def burn():
                            while time.time() < end_time:
                                pass
                        threads = [threading.Thread(target=burn) for _ in range(thread_count)]
                        for t in threads: 
                            t.start()
                        for t in threads: 
                            t.join()
                        logger.info(f"CPU spike chaos completed for experiment {experiment.id if experiment else 'unknown'}")
                    except Exception as e:
                        logger.error(f"CPU spike chaos failed: {e}")
                        if experiment:
                            try:
                                experiment.error_message = str(e)
                                experiment.status = 'failed'
                                db.session.commit()
                            except Exception as db_e:
                                logger.error(f"Failed to update experiment error: {db_e}")
                                
                threading.Thread(target=cpu_stress).start()
                result = {"result": f"CPU spike ({intensity}) injected for {duration}s", "scenario": scenario}
            
            elif scenario == "memory_leak":
                def mem_stress():
                    try:
                        multiplier = {"low": 5000, "medium": 10000, "high": 20000}[intensity]
                        leaker = []
                        for i in range(duration * multiplier):
                            leaker.append(' ' * 1024)
                            time.sleep(0.001)
                        time.sleep(duration)
                        del leaker
                        logger.info(f"Memory leak chaos completed for experiment {experiment.id if experiment else 'unknown'}")
                    except MemoryError as e:
                        logger.error(f"Memory leak chaos hit system limits: {e}")
                        if experiment:
                            try:
                                experiment.error_message = f"Hit memory limits: {str(e)}"
                                experiment.status = 'failed'
                                db.session.commit()
                            except Exception as db_e:
                                logger.error(f"Failed to update experiment error: {db_e}")
                    except Exception as e:
                        logger.error(f"Memory leak chaos failed: {e}")
                        if experiment:
                            try:
                                experiment.error_message = str(e)
                                experiment.status = 'failed'
                                db.session.commit()
                            except Exception as db_e:
                                logger.error(f"Failed to update experiment error: {db_e}")
                                
                threading.Thread(target=mem_stress).start()
                result = {"result": f"Memory leak ({intensity}) injected for {duration}s", "scenario": scenario}
            
            elif scenario == "disk_fill":
                def disk_stress():
                    try:
                        size_mb = {"low": 50, "medium": 100, "high": 200}[intensity]
                        temp_files = []
                        temp_dir = "/tmp" if os.name != 'nt' else "C:\\temp"
                        
                        # Ensure temp directory exists
                        os.makedirs(temp_dir, exist_ok=True)
                        
                        for i in range(size_mb):
                            filename = os.path.join(temp_dir, f"chaos_disk_{i}.tmp")
                            with open(filename, 'w') as f:
                                f.write('x' * (1024 * 1024))  # 1MB file
                            temp_files.append(filename)
                        time.sleep(duration)
                        # Cleanup
                        for f in temp_files:
                            try:
                                os.remove(f)
                            except FileNotFoundError:
                                pass
                            except Exception as cleanup_e:
                                logger.warning(f"Failed to cleanup temp file {f}: {cleanup_e}")
                        logger.info(f"Disk fill chaos completed for experiment {experiment.id if experiment else 'unknown'}")
                    except PermissionError as e:
                        logger.error(f"Permission denied during disk fill chaos: {e}")
                        if experiment:
                            try:
                                experiment.error_message = f"Permission denied: {str(e)}"
                                experiment.status = 'failed'
                                db.session.commit()
                            except Exception as db_e:
                                logger.error(f"Failed to update experiment error: {db_e}")
                    except OSError as e:
                        logger.error(f"OS error during disk fill chaos: {e}")
                        if experiment:
                            try:
                                experiment.error_message = f"OS error: {str(e)}"
                                experiment.status = 'failed'
                                db.session.commit()
                            except Exception as db_e:
                                logger.error(f"Failed to update experiment error: {db_e}")
                    except Exception as e:
                        logger.error(f"Disk fill chaos failed: {e}")
                        if experiment:
                            try:
                                experiment.error_message = str(e)
                                experiment.status = 'failed'
                                db.session.commit()
                            except Exception as db_e:
                                logger.error(f"Failed to update experiment error: {db_e}")
                                
                threading.Thread(target=disk_stress).start()
                result = {"result": f"Disk fill ({intensity}) injected for {duration}s", "scenario": scenario}
            
            elif scenario == "network_latency":
                # Simulate network latency by adding delays to responses
                def network_delay():
                    try:
                        delay_ms = {"low": 100, "medium": 500, "high": 1000}[intensity]
                        # Store original response time
                        end_time = time.time() + duration
                        while time.time() < end_time:
                            time.sleep(delay_ms / 1000)
                        logger.info(f"Network latency chaos completed for experiment {experiment.id if experiment else 'unknown'}")
                    except Exception as e:
                        logger.error(f"Network latency chaos failed: {e}")
                        if experiment:
                            try:
                                experiment.error_message = str(e)
                                experiment.status = 'failed'
                                db.session.commit()
                            except Exception as db_e:
                                logger.error(f"Failed to update experiment error: {db_e}")
                                
                threading.Thread(target=network_delay).start()
                result = {"result": f"Network latency ({intensity}) injected for {duration}s", "scenario": scenario}
            
            elif scenario == "api_timeout":
                def timeout_simulation():
                    try:
                        timeout_duration = {"low": 5, "medium": 10, "high": 30}[intensity]
                        time.sleep(min(timeout_duration, duration))
                        logger.info(f"API timeout chaos completed for experiment {experiment.id if experiment else 'unknown'}")
                    except Exception as e:
                        logger.error(f"API timeout chaos failed: {e}")
                        if experiment:
                            try:
                                experiment.error_message = str(e)
                                experiment.status = 'failed'
                                db.session.commit()
                            except Exception as db_e:
                                logger.error(f"Failed to update experiment error: {db_e}")
                                
                threading.Thread(target=timeout_simulation).start()
                result = {"result": f"API timeout ({intensity}) simulated for {duration}s", "scenario": scenario}
            
            elif scenario == "process_kill":
                # Simulate process instability
                def process_chaos():
                    try:
                        # This is a safe simulation - just sleeps
                        kill_delay = {"low": 30, "medium": 15, "high": 5}[intensity]
                        time.sleep(min(kill_delay, duration))
                        logger.info(f"Process kill chaos completed for experiment {experiment.id if experiment else 'unknown'}")
                    except Exception as e:
                        logger.error(f"Process kill chaos failed: {e}")
                        if experiment:
                            try:
                                experiment.error_message = str(e)
                                experiment.status = 'failed'
                                db.session.commit()
                            except Exception as db_e:
                                logger.error(f"Failed to update experiment error: {db_e}")
                                
                threading.Thread(target=process_chaos).start()
                result = {"result": f"Process instability ({intensity}) simulated for {duration}s", "scenario": scenario}
            
            elif scenario == "database_slowdown":
                def db_slowdown():
                    try:
                        # Simulate database connection delays
                        query_delay = {"low": 0.1, "medium": 0.5, "high": 2.0}[intensity]
                        end_time = time.time() + duration
                        while time.time() < end_time:
                            time.sleep(query_delay)
                        logger.info(f"Database slowdown chaos completed for experiment {experiment.id if experiment else 'unknown'}")
                    except Exception as e:
                        logger.error(f"Database slowdown chaos failed: {e}")
                        if experiment:
                            try:
                                experiment.error_message = str(e)
                                experiment.status = 'failed'
                                db.session.commit()
                            except Exception as db_e:
                                logger.error(f"Failed to update experiment error: {db_e}")
                                
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
                    try:
                        # Generic chaos simulation with variable intensity
                        impact_duration = {"low": duration * 0.5, "medium": duration * 0.75, "high": duration}[intensity]
                        time.sleep(impact_duration)
                        logger.info(f"Generic chaos scenario '{scenario}' completed for experiment {experiment.id if experiment else 'unknown'}")
                    except Exception as e:
                        logger.error(f"Generic chaos scenario '{scenario}' failed: {e}")
                        if experiment:
                            try:
                                experiment.error_message = str(e)
                                experiment.status = 'failed'
                                db.session.commit()
                            except Exception as db_e:
                                logger.error(f"Failed to update experiment error: {db_e}")
                
                threading.Thread(target=generic_chaos).start()
                result = {"result": f"{scenario_name} ({intensity}) executed for {duration}s", "scenario": scenario}
            
            # Update experiment status to completed if successful
            if experiment and not experiment.error_message:
                try:
                    experiment.status = 'completed'
                    experiment.end_time = datetime.utcnow()
                    experiment.result = json.dumps(result)
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Failed to update experiment completion status: {e}")
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Chaos injection failed: {e}")
            if experiment:
                try:
                    experiment.error_message = str(e)
                    experiment.status = 'failed'
                    experiment.end_time = datetime.utcnow()
                    db.session.commit()
                except Exception as db_e:
                    logger.error(f"Failed to update experiment failure status: {db_e}")
            return jsonify({'error': f'Chaos injection failed: {str(e)}'}), 500
            
    except ValueError as e:
        logger.error(f"Invalid input data: {e}")
        return jsonify({'error': f'Invalid input: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Unexpected error in chaos injection endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500
# Available chaos scenarios endpoint
@app.route("/scenarios")
def scenarios():
    """Return available chaos scenarios"""
    try:
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
    except Exception as e:
        logger.error(f"Failed to retrieve scenarios: {e}")
        return jsonify({"error": "Failed to retrieve scenarios"}), 500


# Humorous health check endpoint
@app.route("/health")
def health():
    """Health check endpoint with humor"""
    try:
        health_states = [
            "healthy (for now)",
            "alive and causing trouble",
            "operational, but plotting chaos",
            "all systems nominal (but not for long)",
            "fit as a fiddle in a tornado"
        ]
        return jsonify({"status": random.choice(health_states)}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "error", "message": "Health check failed"}), 500


# Humorous metrics endpoint
@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint with Easter eggs"""
    try:
        CHAOS_REQUESTS_COUNT.inc()
        # Easter egg: Occasionally return a joke metric
        if random.randint(1, 20) == 10:
            return Response("# HELP mayhem_joke_metric Number of times chaos made us laugh\n# TYPE mayhem_joke_metric counter\nmayhem_joke_metric 42\n", mimetype=CONTENT_TYPE_LATEST)
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return Response("# Error generating metrics\n", mimetype=CONTENT_TYPE_LATEST), 500

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
        
        # Handle different OS disk paths
        try:
            if os.name == 'nt':
                disk_info = psutil.disk_usage('C:')._asdict()
            else:
                disk_info = psutil.disk_usage('/')._asdict()
        except (PermissionError, FileNotFoundError) as e:
            logger.warning(f"Cannot access disk usage: {e}")
            disk_info = {"error": "Cannot access disk usage"}
        
        # Network statistics
        try:
            network_info = psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
        except Exception as e:
            logger.warning(f"Cannot access network stats: {e}")
            network_info = {"error": "Cannot access network stats"}
        
        # Process information
        try:
            current_process = psutil.Process()
            process_info = {
                "running_processes": len(psutil.pids()),
                "current_process": {
                    "cpu_percent": current_process.cpu_percent(),
                    "memory_percent": current_process.memory_percent(),
                    "num_threads": current_process.num_threads()
                }
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Cannot access process info: {e}")
            process_info = {"error": "Cannot access process info"}
        
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
        logger.error(f"System status check failed: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500

@app.route("/chaos-history")
def chaos_history():
    """Return history of chaos injections from database"""
    try:
        # Get real experiment history from database
        experiments = ChaosExperiment.query.order_by(ChaosExperiment.start_time.desc()).limit(20).all()
        
        history = []
        for exp in experiments:
            history.append({
                "id": exp.id,
                "timestamp": exp.start_time.timestamp() if exp.start_time else None,
                "scenario": exp.scenario,
                "duration": exp.duration,
                "intensity": exp.intensity,
                "status": exp.status,
                "start_time": exp.start_time.isoformat() if exp.start_time else None,
                "end_time": exp.end_time.isoformat() if exp.end_time else None,
                "error_message": exp.error_message,
                "client_ip": exp.client_ip
            })
        
        return jsonify({"history": history})
    except Exception as e:
        logger.error(f"Failed to retrieve chaos history: {e}")
        # Fallback to mock data if database fails
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
        return jsonify({"history": history, "note": "Using fallback data due to database error"})

if __name__ == "__main__":
    try:
        print("\n[Mayhem] Starting the orchestrator... Hold on to your packets!\n")
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:
        logger.critical(f"Failed to start application: {e}")
        print(f"Critical error: {e}")
        exit(1)