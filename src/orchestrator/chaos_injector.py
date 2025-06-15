from flask import Flask, jsonify, Response, send_from_directory, render_template
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Gauge
import random
import psutil
import threading
import time

import os
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), '../static'), static_url_path='/static')

# Prometheus metrics
REQUEST_COUNT = Counter('chaos_requests_total', 'Total number of requests to the chaos orchestrator')
CPU_USAGE = Gauge('system_cpu_percent', 'Current CPU usage percentage')
MEMORY_USAGE = Gauge('system_memory_percent', 'Current memory usage percentage')
CHAOS_INJECTIONS = Counter('chaos_injections_total', 'Total number of chaos injections', ['scenario'])

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

# Example metric
REQUEST_COUNT = Counter('chaos_requests_total', 'Total number of requests to the chaos orchestrator')



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
def inject():
    data = request.get_json(force=True)
    scenario = data.get("scenario", "cpu_spike")
    duration = int(data.get("duration", 10))
    
    # Increment chaos injection counter
    CHAOS_INJECTIONS.labels(scenario=scenario).inc()
    
    result = {}
    if scenario == "cpu_spike":
        def cpu_stress():
            end_time = time.time() + duration
            def burn():
                while time.time() < end_time:
                    pass
            threads = [threading.Thread(target=burn) for _ in range(4)]
            for t in threads: t.start()
            for t in threads: t.join()
        threading.Thread(target=cpu_stress).start()
        result = {"result": f"CPU spike injected for {duration} seconds", "scenario": scenario}
    elif scenario == "memory_leak":
        def mem_stress():
            leaker = []
            for i in range(duration * 10000):
                leaker.append(' ' * 1024)
                time.sleep(0.001)
            # Keep reference for duration
            time.sleep(duration)
            del leaker
        threading.Thread(target=mem_stress).start()
        result = {"result": f"Memory leak injected for {duration} seconds", "scenario": scenario}
    else:
        result = {"result": f"Scenario '{scenario}' not implemented yet", "scenario": scenario}
    return jsonify(result)


# Available chaos scenarios endpoint
@app.route("/scenarios")
def scenarios():
    # Example static list; replace with dynamic logic if needed
    available = ["cpu_spike", "memory_leak"]
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
    REQUEST_COUNT.inc()
    # Easter egg: Occasionally return a joke metric
    if random.randint(1, 20) == 10:
        return Response("# HELP mayhem_joke_metric Number of times chaos made us laugh\n# TYPE mayhem_joke_metric counter\nmayhem_joke_metric 42\n", mimetype=CONTENT_TYPE_LATEST)
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    print("\n[Mayhem] Starting the orchestrator... Hold on to your packets!\n")
    app.run(host="0.0.0.0", port=5000)