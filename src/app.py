from orchestrator.chaos_injector import app

if __name__ == "__main__":
    # Dev entry point for a containerized service: binding all interfaces
    # inside the container is intended.
    app.run(host="0.0.0.0", port=5000)  # nosec B104
