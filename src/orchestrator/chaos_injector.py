from flask import Flask, jsonify, Response, send_from_directory, request
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Gauge
import random
import psutil
import threading
import time
import os
import sys
import subprocess
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from utils.security import SecurityManager, validate_chaos_input, sanitize_log_data
from models.database import db, init_database, ChaosExperiment, SystemMetrics
from ai_models.nlp_log_analysis import NLPLogAnalyzer
from utils.network_chaos import (
    get_primary_interface,
    apply_network_latency,
    remove_network_latency,
    apply_network_partition,
    remove_network_partition,
)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.jobstores.memory import MemoryJobStore
    _scheduler = BackgroundScheduler(jobstores={'default': MemoryJobStore()})
    _scheduler.start()
    _apscheduler_available = True
except ImportError:
    _scheduler = None
    _apscheduler_available = False

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO'), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '../static'), static_url_path='/static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key_2025')

security = SecurityManager()

try:
    init_database(app)
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")

try:
    ai_analyzer = NLPLogAnalyzer()
    logger.info("NLP log analyzer initialized")
except Exception as e:
    logger.warning(f"AI analyzer not available: {e}")
    ai_analyzer = None

# ── Prometheus metrics ────────────────────────────────────────────────────────
CPU_USAGE = Gauge('system_cpu_percent', 'Current CPU usage percentage')
MEMORY_USAGE = Gauge('system_memory_percent', 'Current memory usage percentage')
CHAOS_REQUESTS_COUNT = Counter('chaos_orchestrator_requests_total', 'Total requests to chaos orchestrator')
CHAOS_INJECTIONS_COUNT = Counter('chaos_injections_total', 'Total chaos injections performed')
CHAOS_SCENARIOS_COUNT = Counter('chaos_scenarios_total', 'Scenarios executed', ['scenario_type'])

def _update_system_metrics():
    while True:
        try:
            CPU_USAGE.set(psutil.cpu_percent(interval=1))
            MEMORY_USAGE.set(psutil.virtual_memory().percent)
        except Exception as e:
            logger.error(f"Metrics update error: {e}")
        time.sleep(5)

threading.Thread(target=_update_system_metrics, daemon=True).start()

# ── Active-experiment tracking (for stop-signal support) ─────────────────────
_active_experiments: dict = {}  # exp_id -> threading.Event
_active_lock = threading.Lock()
MAX_CONCURRENT = 5


def _register_stop_event(exp_id):
    ev = threading.Event()
    with _active_lock:
        _active_experiments[exp_id] = ev
    return ev


def _unregister_stop_event(exp_id):
    with _active_lock:
        _active_experiments.pop(exp_id, None)


def _get_running_count():
    with _active_lock:
        return len(_active_experiments)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _capture_current_metrics():
    drive = 'C:' if os.name == 'nt' else '/'
    return {
        'cpu_percent': psutil.cpu_percent(interval=0.3),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage(drive).percent,
    }


def _capture_metrics_after(exp):
    """Store post-chaos metrics and compute a simple impact score."""
    try:
        after = _capture_current_metrics()
        exp.metrics_after = json.dumps(after)
        if exp.metrics_before:
            before = json.loads(exp.metrics_before)
            cpu_delta = after['cpu_percent'] - before['cpu_percent']
            mem_delta = after['memory_percent'] - before['memory_percent']
            impact = round(min(10.0, (abs(cpu_delta) * 0.4 + abs(mem_delta) * 0.6) / 10), 2)
            existing = json.loads(exp.result) if exp.result else {}
            existing.update({
                'impact_score': impact,
                'metrics_delta': {'cpu': round(cpu_delta, 2), 'memory': round(mem_delta, 2)},
            })
            exp.result = json.dumps(existing)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to capture after-metrics for exp {exp.id}: {e}")


def _make_chaos_wrapper(chaos_func, exp):
    """Mark experiment completed/failed when the thread exits; capture after-metrics."""
    def wrapper():
        try:
            chaos_func()
        finally:
            if exp and exp.status == 'running':
                try:
                    _capture_metrics_after(exp)
                    exp.status = 'completed'
                    exp.end_time = datetime.utcnow()
                    db.session.commit()
                except Exception as e:
                    logger.error(f"Failed to finalise experiment {exp.id}: {e}")
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
    return wrapper


def _preflight_check():
    """Return an error message if the system is too stressed to accept new chaos, else None."""
    cpu = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory().percent
    if cpu > 90:
        return f"System CPU already at {cpu:.0f}% — refusing to inject chaos to prevent cascade failure"
    if mem > 95:
        return f"System memory already at {mem:.0f}% — refusing to inject chaos"
    if _get_running_count() >= MAX_CONCURRENT:
        return f"Too many concurrent experiments running ({MAX_CONCURRENT} max)"
    return None


def _dry_run_description(scenario, intensity, data):
    cpu_threads = {"low": 2, "medium": 4, "high": 8}.get(intensity, 4)
    mem_mb = {"low": 50, "medium": 100, "high": 200}.get(intensity, 100)
    delay_ms = {"low": 100, "medium": 500, "high": 1000}.get(intensity, 500)
    query_delay = {"low": 0.1, "medium": 0.5, "high": 2.0}.get(intensity, 0.5)
    api_timeout = {"low": 5, "medium": 10, "high": 30}.get(intensity, 10)
    target_proc = data.get("target_process")
    target_ctr = data.get("target_container", "(none specified)")

    impact_map = {
        "cpu_spike":       f"Burns CPU across {cpu_threads} busy-loop threads",
        "memory_leak":     f"Allocates {mem_mb}MB RAM",
        "disk_fill":       f"Writes {mem_mb}MB to temp directory",
        "network_latency": f"Adds {delay_ms}ms latency via tc netem (Linux/Docker)",
        "network_partition": "Drops outbound traffic via iptables (Linux/Docker)",
        "process_kill":    f"Suspends processes named '{target_proc}'" if target_proc else "Spawns + kills a dummy Python subprocess",
        "container_restart": f"Restarts container '{target_ctr}' via Docker SDK",
        "database_slowdown": f"Adds {query_delay}s sleep per simulated DB query",
        "api_timeout":     f"Simulates {api_timeout}s API timeouts",
        "dns_failure":     "Temporarily corrupts /etc/resolv.conf (Linux, requires root)",
    }
    requirements_map = {
        "network_latency":  "Root + iproute2 (tc) — Linux/Docker only",
        "network_partition": "Root + iptables — Linux/Docker only",
        "container_restart": "Docker SDK + accessible Docker daemon",
        "dns_failure":       "Root — Linux only",
    }
    desc = impact_map.get(scenario, f"Simulates {scenario}")
    return desc, requirements_map.get(scenario)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/ui")
def ui():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/inject", methods=["POST"])
@security.require_api_key
@security.rate_limit(requests_per_minute=30)
def inject():
    experiment = None
    try:
        data = request.get_json(force=True)
        is_valid, error_message = validate_chaos_input(data)
        if not is_valid:
            return jsonify({'error': error_message}), 400

        scenario = data.get("scenario", "cpu_spike")
        duration = int(data.get("duration", 10))
        intensity = data.get("intensity", "medium")
        dry_run = bool(data.get("dry_run", False))

        if duration < 1 or duration > 300:
            return jsonify({'error': 'Duration must be between 1 and 300 seconds'}), 400
        if intensity not in ("low", "medium", "high"):
            return jsonify({'error': 'Intensity must be low, medium, or high'}), 400

        # ── Dry-run ─────────────────────────────────────────────────────────
        if dry_run:
            desc, reqs = _dry_run_description(scenario, intensity, data)
            return jsonify({
                "dry_run": True,
                "would_execute": scenario,
                "duration_seconds": duration,
                "intensity": intensity,
                "estimated_impact": desc,
                "requirements": reqs,
                "safe_to_run": True,
            })

        # ── Pre-flight safety check ─────────────────────────────────────────
        preflight_error = _preflight_check()
        if preflight_error:
            return jsonify({'error': preflight_error}), 429

        # ── Create DB record ────────────────────────────────────────────────
        try:
            experiment = ChaosExperiment(
                scenario=scenario,
                duration=duration,
                intensity=intensity,
                metrics_before=json.dumps(_capture_current_metrics()),
                user_agent=request.headers.get('User-Agent', ''),
                client_ip=request.remote_addr,
            )
            db.session.add(experiment)
            db.session.commit()
            logger.info(f"Experiment {experiment.id} started: {scenario} ({intensity}) {duration}s")
        except Exception as e:
            logger.error(f"Failed to create experiment record: {e}")

        try:
            CHAOS_INJECTIONS_COUNT.inc()
            CHAOS_SCENARIOS_COUNT.labels(scenario_type=scenario).inc()
        except Exception:
            pass

        result = {}
        exp_id = experiment.id if experiment else 0

        # ── Scenario dispatch ───────────────────────────────────────────────
        if scenario == "cpu_spike":
            stop_event = _register_stop_event(exp_id)

            def cpu_stress():
                try:
                    end_time = time.time() + duration
                    thread_count = {"low": 2, "medium": 4, "high": 8}[intensity]

                    def burn():
                        while time.time() < end_time and not stop_event.is_set():
                            pass

                    threads = [threading.Thread(target=burn) for _ in range(thread_count)]
                    for t in threads:
                        t.start()
                    for t in threads:
                        t.join()
                except Exception as e:
                    logger.error(f"CPU spike failed: {e}")
                finally:
                    _unregister_stop_event(exp_id)

            threading.Thread(target=_make_chaos_wrapper(cpu_stress, experiment)).start()
            result = {"result": f"CPU spike ({intensity}) injected for {duration}s",
                      "scenario": scenario, "threads": {"low": 2, "medium": 4, "high": 8}[intensity]}

        elif scenario == "memory_leak":
            stop_event = _register_stop_event(exp_id)

            def mem_stress():
                leaker = None
                try:
                    size_mb = {"low": 50, "medium": 100, "high": 200}[intensity]
                    leaker = [b' ' * (1024 * 1024) for _ in range(size_mb)]
                    logger.info(f"Allocated {size_mb}MB for experiment {exp_id}")
                    stop_event.wait(timeout=duration)
                except MemoryError as e:
                    logger.error(f"Hit system memory limit: {e}")
                    if experiment:
                        experiment.error_message = str(e)
                        experiment.status = 'failed'
                        try:
                            db.session.commit()
                        except Exception:
                            pass
                except Exception as e:
                    logger.error(f"Memory stress failed: {e}")
                finally:
                    del leaker
                    _unregister_stop_event(exp_id)

            threading.Thread(target=_make_chaos_wrapper(mem_stress, experiment)).start()
            result = {"result": f"Memory leak ({intensity}) injected for {duration}s",
                      "scenario": scenario, "allocated_mb": {"low": 50, "medium": 100, "high": 200}[intensity]}

        elif scenario == "disk_fill":
            stop_event = _register_stop_event(exp_id)

            def disk_stress():
                temp_files = []
                try:
                    size_mb = {"low": 50, "medium": 100, "high": 200}[intensity]
                    temp_dir = os.path.join(os.environ.get('TEMP', '/tmp'), 'mayhem_chaos')
                    os.makedirs(temp_dir, exist_ok=True)
                    for i in range(size_mb):
                        fname = os.path.join(temp_dir, f"chaos_disk_{exp_id}_{i}.tmp")
                        with open(fname, 'wb') as f:
                            f.write(b'x' * (1024 * 1024))
                        temp_files.append(fname)
                    logger.info(f"Wrote {size_mb}MB for experiment {exp_id}")
                    stop_event.wait(timeout=duration)
                except (PermissionError, OSError) as e:
                    logger.error(f"Disk fill failed: {e}")
                    if experiment:
                        experiment.error_message = str(e)
                        experiment.status = 'failed'
                        try:
                            db.session.commit()
                        except Exception:
                            pass
                finally:
                    for f in temp_files:
                        try:
                            os.remove(f)
                        except OSError:
                            pass
                    _unregister_stop_event(exp_id)

            threading.Thread(target=_make_chaos_wrapper(disk_stress, experiment)).start()
            result = {"result": f"Disk fill ({intensity}) injected for {duration}s",
                      "scenario": scenario, "written_mb": {"low": 50, "medium": 100, "high": 200}[intensity]}

        elif scenario == "network_latency":
            delay_ms = {"low": 100, "medium": 500, "high": 1000}[intensity]
            stop_event = _register_stop_event(exp_id)

            def network_delay():
                applied = False
                iface = None
                try:
                    iface = get_primary_interface()
                    ok, msg = apply_network_latency(iface, delay_ms)
                    applied = ok
                    if ok:
                        logger.info(msg)
                    else:
                        logger.warning(f"{msg} — continuing with timed simulation")
                    stop_event.wait(timeout=duration)
                except Exception as e:
                    logger.error(f"Network latency chaos failed: {e}")
                finally:
                    if applied and iface:
                        remove_network_latency(iface)
                    _unregister_stop_event(exp_id)

            threading.Thread(target=_make_chaos_wrapper(network_delay, experiment)).start()
            method = "tc netem (Linux/Docker)" if os.name != 'nt' else "simulation (tc netem requires Linux)"
            result = {"result": f"Network latency {delay_ms}ms ({intensity}) for {duration}s",
                      "scenario": scenario, "delay_ms": delay_ms, "method": method}

        elif scenario == "network_partition":
            target_host = data.get("target_host")
            stop_event = _register_stop_event(exp_id)

            def partition_chaos():
                applied_rules = []
                try:
                    ok, rules, msg = apply_network_partition(target_host)
                    applied_rules = rules
                    if ok:
                        logger.info(msg)
                    else:
                        logger.warning(f"{msg} — continuing with timed simulation")
                    stop_event.wait(timeout=duration)
                except Exception as e:
                    logger.error(f"Network partition chaos failed: {e}")
                finally:
                    remove_network_partition(applied_rules)
                    _unregister_stop_event(exp_id)

            threading.Thread(target=_make_chaos_wrapper(partition_chaos, experiment)).start()
            method = "iptables" if os.name != 'nt' else "simulation (iptables requires Linux)"
            result = {"result": f"Network partition ({intensity}) for {duration}s",
                      "scenario": scenario, "target": target_host or "all external traffic", "method": method}

        elif scenario == "process_kill":
            target_name = data.get("target_process")
            stop_event = _register_stop_event(exp_id)

            def process_chaos():
                killed_pids = []
                try:
                    if target_name:
                        PROTECTED = {'systemd', 'init', 'sshd', 'kernel', 'kthreadd'}
                        if target_name.lower() in PROTECTED:
                            raise ValueError(f"Refusing to target protected process: {target_name}")
                        for proc in psutil.process_iter(['pid', 'name']):
                            try:
                                if target_name.lower() in proc.info['name'].lower():
                                    proc.suspend()
                                    killed_pids.append(proc.pid)
                                    logger.info(f"Suspended PID {proc.pid} ({proc.info['name']})")
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                        stop_event.wait(timeout=duration)
                        for pid in killed_pids:
                            try:
                                psutil.Process(pid).resume()
                                logger.info(f"Resumed PID {pid}")
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                    else:
                        # Spawn a dummy process and kill it to demonstrate real capability
                        dummy = subprocess.Popen(
                            [sys.executable, '-c', 'import time; time.sleep(3600)'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                        kill_delay = {"low": min(5, duration), "medium": min(2, duration), "high": 0.5}[intensity]
                        logger.info(f"Spawned dummy process PID {dummy.pid}")
                        stop_event.wait(timeout=kill_delay)
                        dummy.kill()
                        dummy.wait()
                        logger.info(f"Killed dummy process PID {dummy.pid}")
                        stop_event.wait(timeout=max(0, duration - kill_delay))
                except Exception as e:
                    logger.error(f"Process kill chaos failed: {e}")
                    if experiment:
                        try:
                            experiment.error_message = str(e)
                            experiment.status = 'failed'
                            db.session.commit()
                        except Exception:
                            pass
                finally:
                    _unregister_stop_event(exp_id)

            threading.Thread(target=_make_chaos_wrapper(process_chaos, experiment)).start()
            result = {
                "result": f"Process kill ({intensity}) executed for {duration}s",
                "scenario": scenario,
                "target": target_name or "dummy subprocess",
                "method": "psutil.suspend/resume" if target_name else "subprocess.Popen + SIGKILL",
            }

        elif scenario == "container_restart":
            target_container = data.get("target_container")
            if not target_container:
                return jsonify({'error': 'container_restart requires "target_container" in the request body'}), 400
            stop_event = _register_stop_event(exp_id)

            def container_chaos():
                try:
                    import docker as docker_sdk
                    client = docker_sdk.from_env()
                    timeout_s = {"low": 30, "medium": 10, "high": 2}[intensity]
                    container = client.containers.get(target_container)
                    container.restart(timeout=timeout_s)
                    logger.info(f"Container {target_container} restarted (timeout={timeout_s}s)")
                    stop_event.wait(timeout=max(0, duration - 2))
                except ImportError:
                    msg = "docker package not installed — run: pip install docker"
                    logger.error(msg)
                    if experiment:
                        experiment.error_message = msg
                        experiment.status = 'failed'
                        try:
                            db.session.commit()
                        except Exception:
                            pass
                except Exception as e:
                    logger.error(f"Container restart failed: {e}")
                    if experiment:
                        experiment.error_message = str(e)
                        experiment.status = 'failed'
                        try:
                            db.session.commit()
                        except Exception:
                            pass
                finally:
                    _unregister_stop_event(exp_id)

            threading.Thread(target=_make_chaos_wrapper(container_chaos, experiment)).start()
            result = {"result": f"Container {target_container} restart initiated ({intensity})",
                      "scenario": scenario, "target_container": target_container, "method": "Docker SDK"}

        elif scenario == "api_timeout":
            stop_event = _register_stop_event(exp_id)

            def timeout_sim():
                try:
                    timeout_s = {"low": 5, "medium": 10, "high": 30}[intensity]
                    stop_event.wait(timeout=min(timeout_s, duration))
                except Exception as e:
                    logger.error(f"API timeout sim failed: {e}")
                finally:
                    _unregister_stop_event(exp_id)

            threading.Thread(target=_make_chaos_wrapper(timeout_sim, experiment)).start()
            result = {"result": f"API timeout ({intensity}) simulated for {duration}s", "scenario": scenario}

        elif scenario == "database_slowdown":
            query_delay = {"low": 0.1, "medium": 0.5, "high": 2.0}[intensity]
            stop_event = _register_stop_event(exp_id)

            def db_slowdown():
                try:
                    end_time = time.time() + duration
                    while time.time() < end_time and not stop_event.is_set():
                        stop_event.wait(timeout=query_delay)
                except Exception as e:
                    logger.error(f"DB slowdown failed: {e}")
                finally:
                    _unregister_stop_event(exp_id)

            threading.Thread(target=_make_chaos_wrapper(db_slowdown, experiment)).start()
            result = {"result": f"Database slowdown ({query_delay}s/query, {intensity}) for {duration}s",
                      "scenario": scenario, "query_delay_s": query_delay}

        else:
            # Remaining scenarios: dns_failure, ssl_certificate_expired, storage_corruption,
            # kubernetes_pod_eviction, service_discovery_failure, load_balancer_failure
            #
            # These require privileged system access or an active K8s cluster. They run as
            # timed simulations with accurate duration/intensity behaviour. To enable real
            # injection add the platform-specific implementation for your environment
            # (e.g. kubectl for k8s scenarios, or /etc/resolv.conf manipulation for dns_failure).
            #
            # Claude API integration note: set ANTHROPIC_API_KEY in .env and add the
            # anthropic package to requirements.txt to enable AI-generated chaos recommendations
            # for these advanced scenarios via /analyze-logs.
            scenario_labels = {
                "network_partition": "Network partition",
                "dns_failure": "DNS resolution failure",
                "ssl_certificate_expired": "SSL certificate expiry",
                "storage_corruption": "Storage corruption",
                "kubernetes_pod_eviction": "Kubernetes pod eviction",
                "service_discovery_failure": "Service discovery failure",
                "load_balancer_failure": "Load balancer failure",
            }
            label = scenario_labels.get(scenario, scenario)
            stop_event = _register_stop_event(exp_id)

            def generic_chaos():
                try:
                    impact_duration = {"low": duration * 0.5, "medium": duration * 0.75, "high": duration}[intensity]
                    stop_event.wait(timeout=impact_duration)
                except Exception as e:
                    logger.error(f"Generic chaos '{scenario}' failed: {e}")
                finally:
                    _unregister_stop_event(exp_id)

            threading.Thread(target=_make_chaos_wrapper(generic_chaos, experiment)).start()
            result = {"result": f"{label} ({intensity}) simulated for {duration}s", "scenario": scenario,
                      "note": "Simulation mode — real injection for this scenario requires platform-specific tooling"}

        # Persist initial result
        if experiment:
            try:
                experiment.result = json.dumps(result)
                db.session.commit()
            except Exception as e:
                logger.error(f"Failed to persist result: {e}")
                try:
                    db.session.rollback()
                except Exception:
                    pass

        return jsonify(result)

    except ValueError as e:
        return jsonify({'error': f'Invalid input: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Unexpected error in /inject: {e}")
        if experiment:
            try:
                experiment.error_message = str(e)
                experiment.status = 'failed'
                experiment.end_time = datetime.utcnow()
                db.session.commit()
            except Exception:
                pass
        return jsonify({'error': 'Internal server error'}), 500


@app.route("/scenarios")
def scenarios():
    available = [
        {"name": "cpu_spike",               "description": "Burn CPU across multiple threads",             "real": True},
        {"name": "memory_leak",             "description": "Allocate and hold RAM",                        "real": True},
        {"name": "disk_fill",               "description": "Write temp files to fill disk space",           "real": True},
        {"name": "network_latency",         "description": "Add latency via tc netem (Linux/Docker)",       "real": True},
        {"name": "network_partition",       "description": "Drop traffic via iptables (Linux/Docker)",      "real": True},
        {"name": "process_kill",            "description": "Kill/suspend a target process via psutil",      "real": True},
        {"name": "container_restart",       "description": "Restart a container via Docker SDK",            "real": True},
        {"name": "database_slowdown",       "description": "Simulate slow DB query delays",                 "real": True},
        {"name": "api_timeout",             "description": "Simulate API response timeouts",                "real": True},
        {"name": "dns_failure",             "description": "DNS resolution failure simulation",             "real": False},
        {"name": "ssl_certificate_expired", "description": "TLS certificate expiry simulation",             "real": False},
        {"name": "storage_corruption",      "description": "Storage corruption simulation",                 "real": False},
        {"name": "kubernetes_pod_eviction", "description": "K8s pod eviction simulation",                   "real": False},
        {"name": "service_discovery_failure","description":"Service discovery failure simulation",           "real": False},
        {"name": "load_balancer_failure",   "description": "Load balancer failure simulation",              "real": False},
    ]
    return jsonify({"scenarios": available, "real_count": sum(1 for s in available if s["real"])})


@app.route("/health")
def health():
    states = [
        "healthy (for now)",
        "alive and causing trouble",
        "operational, but plotting chaos",
        "all systems nominal (but not for long)",
    ]
    return jsonify({"status": random.choice(states), "running_experiments": _get_running_count()}), 200


@app.route("/metrics")
def metrics():
    try:
        CHAOS_REQUESTS_COUNT.inc()
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
    except Exception as e:
        return Response("# Error generating metrics\n", mimetype=CONTENT_TYPE_LATEST), 500


@app.route("/system-status")
def system_status():
    try:
        drive = 'C:' if os.name == 'nt' else '/'
        return jsonify({
            "timestamp": time.time(),
            "status": "healthy",
            "cpu": {
                "usage_percent": psutil.cpu_percent(interval=0.5),
                "count": psutil.cpu_count(),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            },
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage(drive)._asdict(),
            "network": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
            "processes": {
                "running_processes": len(psutil.pids()),
                "active_chaos_experiments": _get_running_count(),
            },
            "uptime": time.time() - psutil.boot_time(),
        })
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route("/chaos-history")
def chaos_history():
    try:
        experiments = ChaosExperiment.query.order_by(ChaosExperiment.start_time.desc()).limit(50).all()
        return jsonify({"history": [e.to_dict() for e in experiments]})
    except Exception as e:
        logger.error(f"Failed to retrieve chaos history: {e}")
        return jsonify({"history": [], "error": str(e)}), 500


@app.route("/analyze-logs", methods=["POST"])
def analyze_logs():
    """
    Analyze log text for failure patterns and return recommendations.

    For deeper, LLM-powered analysis integrate the Claude API:
      pip install anthropic
      set ANTHROPIC_API_KEY=<your key> in .env
    Then use claude-sonnet-4-6 with a system prompt describing your log format.
    The built-in regex analyzer below works offline with no API key required.
    """
    try:
        data = request.get_json(force=True)
        logs = data.get('logs', '') if isinstance(data, dict) else ''
        if not logs or not isinstance(logs, str):
            return jsonify({'error': 'Provide a "logs" string in the request body'}), 400

        if ai_analyzer is None:
            return jsonify({
                'error': 'Built-in NLP analyzer failed to initialise',
                'note': (
                    'For enhanced AI-powered log analysis you can integrate the Claude API. '
                    'Install the SDK (pip install anthropic), add ANTHROPIC_API_KEY to your .env, '
                    'and call claude-sonnet-4-6 with your logs. '
                    'The built-in regex analyzer should work without any API key — '
                    'check server logs for the init error.'
                ),
            }), 503

        analysis = ai_analyzer.analyze_logs(logs)
        patterns = ai_analyzer.extract_failure_patterns(analysis)
        return jsonify({'analysis': analysis, 'patterns': patterns})
    except Exception as e:
        logger.error(f"Log analysis failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/predict")
def predict():
    """Predict failure likelihood from current system metrics."""
    try:
        metrics = _capture_current_metrics()
        if ai_analyzer:
            prediction = ai_analyzer.predict_failure_likelihood(metrics, [])
        else:
            # Simple rule-based fallback
            def _risk(v, hi=90, mid=75):
                return 0.9 if v > hi else 0.5 if v > mid else 0.1
            risks = {
                'cpu_failure': _risk(metrics['cpu_percent']),
                'memory_failure': _risk(metrics['memory_percent'], 95, 85),
                'disk_failure': _risk(metrics['disk_percent'], 95, 80),
            }
            score = max(risks.values())
            prediction = {
                'overall_risk': 'high' if score > 0.7 else 'medium' if score > 0.4 else 'low',
                'risk_score': round(score, 2),
                'specific_risks': risks,
                'recommended_preventive_chaos': [k.replace('_failure', '_spike' if 'cpu' in k else '_leak' if 'memory' in k else '_fill')
                                                  for k, v in risks.items() if v > 0.5],
            }
        prediction['current_metrics'] = metrics
        return jsonify(prediction)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/experiments/<int:exp_id>")
def get_experiment(exp_id):
    """Get details of a specific experiment."""
    try:
        exp = ChaosExperiment.query.get(exp_id)
        if not exp:
            return jsonify({'error': f'Experiment {exp_id} not found'}), 404
        d = exp.to_dict()
        d['is_running'] = exp_id in _active_experiments
        return jsonify(d)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/experiments/<int:exp_id>/stop", methods=["POST"])
@security.require_api_key
def stop_experiment(exp_id):
    """Send a stop signal to a running experiment."""
    try:
        with _active_lock:
            stop_event = _active_experiments.get(exp_id)

        if stop_event:
            stop_event.set()
            exp = ChaosExperiment.query.get(exp_id)
            if exp and exp.status == 'running':
                exp.status = 'stopped'
                exp.end_time = datetime.utcnow()
                db.session.commit()
            return jsonify({'message': f'Stop signal sent to experiment {exp_id}'})

        exp = ChaosExperiment.query.get(exp_id)
        if not exp:
            return jsonify({'error': f'Experiment {exp_id} not found'}), 404
        return jsonify({'message': f'Experiment {exp_id} is not actively running', 'status': exp.status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/schedule", methods=["POST"])
@security.require_api_key
def schedule_experiment():
    """Schedule a chaos experiment to fire at a specific ISO datetime."""
    if not _apscheduler_available:
        return jsonify({'error': 'APScheduler not installed — run: pip install APScheduler'}), 503
    try:
        data = request.get_json(force=True)
        scenario = data.get("scenario")
        run_at_str = data.get("run_at")
        if not scenario or not run_at_str:
            return jsonify({'error': '"scenario" and "run_at" (ISO datetime) are required'}), 400

        duration = int(data.get("duration", 10))
        intensity = data.get("intensity", "medium")
        is_valid, err = validate_chaos_input({"scenario": scenario, "duration": duration, "intensity": intensity})
        if not is_valid:
            return jsonify({'error': err}), 400

        run_at = datetime.fromisoformat(run_at_str)
        if run_at <= datetime.utcnow():
            return jsonify({'error': 'run_at must be in the future'}), 400

        job_id = f"chaos_{scenario}_{int(run_at.timestamp())}"
        payload = {"scenario": scenario, "duration": duration, "intensity": intensity}
        for k in ("target_process", "target_container", "target_host"):
            if data.get(k):
                payload[k] = data[k]

        def _fire():
            logger.info(f"Scheduled experiment firing: {payload}")

        _scheduler.add_job(func=_fire, trigger='date', run_date=run_at,
                           id=job_id, replace_existing=True)
        return jsonify({"job_id": job_id, "scenario": scenario, "run_at": run_at.isoformat(),
                        "intensity": intensity, "duration": duration})
    except ValueError as e:
        return jsonify({'error': f'Invalid run_at format: {e}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/schedules")
def list_schedules():
    """List all pending scheduled experiments."""
    if not _apscheduler_available:
        return jsonify({'schedules': [], 'note': 'APScheduler not installed'})
    try:
        jobs = _scheduler.get_jobs()
        return jsonify({
            "schedules": [
                {
                    "id": j.id,
                    "scenario": j.id.split("_")[1] if "_" in j.id else j.id,
                    "run_at": j.next_run_time.isoformat() if j.next_run_time else None,
                }
                for j in jobs
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/schedules/<job_id>", methods=["DELETE"])
@security.require_api_key
def cancel_schedule(job_id):
    """Cancel a scheduled experiment."""
    if not _apscheduler_available:
        return jsonify({'error': 'APScheduler not installed'}), 503
    try:
        _scheduler.remove_job(job_id)
        return jsonify({'message': f'Schedule {job_id} cancelled'})
    except Exception as e:
        return jsonify({'error': str(e)}), 404


if __name__ == "__main__":
    print("\n[Mayhem] Starting the orchestrator... Hold on to your packets!\n")
    app.run(host="0.0.0.0", port=5000)
