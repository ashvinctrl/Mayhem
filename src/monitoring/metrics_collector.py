class MetricsCollector:
    def __init__(self):
        self.metrics = {}


    def collect_metrics(self):
        # Dummy metrics for testing
        return {'cpu_usage': 50, 'memory_usage': 256}

    def send_to_prometheus(self, metrics):
        # Dummy send logic for testing
        if 'cpu_usage' in metrics and 'memory_usage' in metrics:
            return True
        return False