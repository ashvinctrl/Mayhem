from flask import Flask, jsonify, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter

app = Flask(__name__)

# Example metric
REQUEST_COUNT = Counter('chaos_requests_total', 'Total number of requests to the chaos orchestrator')

@app.route("/")
def home():
    return jsonify({"status": "Chaos Orchestrator is running!"})

# You can add more routes here for chaos injection endpoints

# Health check endpoint
@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

@app.route("/metrics")
def metrics():
    REQUEST_COUNT.inc()
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)