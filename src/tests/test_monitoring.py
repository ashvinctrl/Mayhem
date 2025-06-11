import unittest
from src.monitoring.metrics_collector import MetricsCollector

class TestMetricsCollector(unittest.TestCase):

    def setUp(self):
        self.collector = MetricsCollector()

    def test_collect_metrics(self):
        metrics = self.collector.collect_metrics()
        self.assertIsNotNone(metrics)
        self.assertIn('cpu_usage', metrics)
        self.assertIn('memory_usage', metrics)

    def test_send_to_prometheus(self):
        metrics = {'cpu_usage': 50, 'memory_usage': 256}
        response = self.collector.send_to_prometheus(metrics)
        self.assertTrue(response)

if __name__ == '__main__':
    unittest.main()