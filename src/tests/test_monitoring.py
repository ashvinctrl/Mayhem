import unittest
import time
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from monitoring.metrics_collector import MetricsCollector

class TestMetricsCollector(unittest.TestCase):
    """Enhanced tests for MetricsCollector with error handling scenarios"""

    def setUp(self):
        self.collector = MetricsCollector()

    def test_collect_metrics_success(self):
        """Test successful metrics collection"""
        metrics = self.collector.collect_metrics()
        self.assertIsNotNone(metrics)
        self.assertIsInstance(metrics, dict)
        self.assertIn('cpu', metrics)
        self.assertIn('memory', metrics)
        self.assertIn('collection', metrics)

    def test_collect_metrics_with_psutil_errors(self):
        """Test metrics collection with psutil errors"""
        with patch('psutil.cpu_percent') as mock_cpu:
            mock_cpu.side_effect = Exception("Access denied")
            
            metrics = self.collector.collect_metrics()
            
            # Should still return metrics dict with error information
            self.assertIsInstance(metrics, dict)
            self.assertIn('cpu', metrics)
            self.assertIn('error', metrics['cpu'])

    def test_collect_metrics_memory_error(self):
        """Test metrics collection with memory access errors"""
        with patch('psutil.virtual_memory') as mock_memory:
            mock_memory.side_effect = PermissionError("Memory access denied")
            
            metrics = self.collector.collect_metrics()
            
            # Should handle gracefully
            self.assertIsInstance(metrics, dict)
            self.assertIn('memory', metrics)

    def test_collect_metrics_disk_error(self):
        """Test metrics collection with disk access errors"""
        with patch('psutil.disk_usage') as mock_disk:
            mock_disk.side_effect = FileNotFoundError("Disk not found")
            
            metrics = self.collector.collect_metrics()
            
            # Should handle gracefully
            self.assertIsInstance(metrics, dict)
            self.assertIn('disk', metrics)

    def test_collect_metrics_network_error(self):
        """Test metrics collection with network access errors"""
        with patch('psutil.net_io_counters') as mock_net:
            mock_net.side_effect = Exception("Network interface error")
            
            metrics = self.collector.collect_metrics()
            
            # Should handle gracefully
            self.assertIsInstance(metrics, dict)
            self.assertIn('network', metrics)

    def test_send_to_prometheus_success(self):
        """Test successful Prometheus sending"""
        metrics = {'cpu': {'usage_percent': 50}, 'memory': {'percent': 60}}
        
        # Mock successful network response
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            result = self.collector.send_to_prometheus(metrics)
            
            # Should return True for successful send
            self.assertTrue(result)

    def test_send_to_prometheus_network_error(self):
        """Test Prometheus sending with network errors"""
        metrics = {'cpu': {'usage_percent': 50}}
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Network error")
            
            result = self.collector.send_to_prometheus(metrics)
            
            # Should handle network error gracefully
            self.assertFalse(result)

    def test_send_to_prometheus_invalid_metrics(self):
        """Test Prometheus sending with invalid metrics"""
        invalid_metrics = [
            None,
            {},
            {"invalid": "data"},
            "not a dict"
        ]
        
        for metrics in invalid_metrics:
            with self.subTest(metrics=metrics):
                result = self.collector.send_to_prometheus(metrics)
                
                # Should handle invalid metrics gracefully
                self.assertIsInstance(result, bool)

    def test_send_to_prometheus_server_error(self):
        """Test Prometheus sending with server errors"""
        metrics = {'cpu': {'usage_percent': 50}}
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal server error"
            mock_post.return_value = mock_response
            
            result = self.collector.send_to_prometheus(metrics)
            
            # Should handle server error gracefully
            self.assertFalse(result)

    def test_prometheus_format_error(self):
        """Test Prometheus formatting with invalid data"""
        # Test with data that might cause formatting errors
        problematic_metrics = {
            'cpu': {'usage_percent': float('inf')},
            'memory': {'percent': float('nan')},
            'disk': {'total': None}
        }
        
        formatted = self.collector._format_for_prometheus(problematic_metrics)
        
        # Should handle gracefully, even with problematic values
        self.assertIsInstance(formatted, str)

    def test_metrics_validation_error(self):
        """Test metrics validation with various inputs"""
        test_cases = [
            {},  # Empty dict
            {'cpu': {}},  # Missing required fields
            {'invalid_section': 'data'},  # Invalid section
            None  # None input
        ]
        
        for metrics in test_cases:
            with self.subTest(metrics=metrics):
                try:
                    result = self.collector._validate_metrics(metrics)
                    self.assertIsInstance(result, bool)
                except Exception:
                    # Should not raise exceptions
                    self.fail("_validate_metrics raised an exception")

    def test_concurrent_collection(self):
        """Test concurrent metrics collection"""
        import threading
        
        results = []
        errors = []
        
        def collect_metrics():
            try:
                metrics = self.collector.collect_metrics()
                results.append(metrics)
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple collection threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=collect_metrics)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should handle concurrent access gracefully
        self.assertEqual(len(results), 5)
        self.assertEqual(len(errors), 0)

    def test_collection_error_threshold(self):
        """Test collection error threshold handling"""
        # Force multiple collection errors
        with patch('psutil.cpu_percent') as mock_cpu:
            mock_cpu.side_effect = Exception("Persistent error")
            
            # Collect multiple times to trigger error threshold
            for i in range(10):
                metrics = self.collector.collect_metrics()
                
                # Should always return some form of metrics
                self.assertIsInstance(metrics, dict)
            
            # Check if error count is tracked
            self.assertGreater(self.collector.collection_errors, 0)

    def test_health_status(self):
        """Test health status reporting"""
        status = self.collector.get_health_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('status', status)
        self.assertIn('collection_errors', status)

    def test_health_status_with_errors(self):
        """Test health status with collection errors"""
        # Force some errors
        self.collector.collection_errors = 10
        
        status = self.collector.get_health_status()
        
        self.assertIsInstance(status, dict)
        self.assertEqual(status['status'], 'degraded')

if __name__ == '__main__':
    unittest.main()