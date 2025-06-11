
from flask import Flask, jsonify, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter
import random

app = Flask(__name__)

# Example metric
REQUEST_COUNT = Counter('chaos_requests_total', 'Total number of requests to the chaos orchestrator')


# Humorous root endpoint
@app.route("/")
def home():
    quotes = [
        "Welcome to Project Mayhem! Don't worry, we only break things on purpose.",
        "Chaos is our middle name. Actually, it's our first name, too.",
        "Injecting chaos, one microservice at a time.",
        "If you can read this, the orchestrator hasn't crashed... yet.",
        "May the faults be with you!"
    ]
    return jsonify({
        "status": "Chaos Orchestrator is running!",
        "message": random.choice(quotes)
    })

# You can add more routes here for chaos injection endpoints


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