import unittest
import json
import time
import threading
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from orchestrator.chaos_injector import app
    from models.database import db, ChaosExperiment
    from ai_models.nlp_log_analysis import NLPLogAnalyzer
except ImportError as e:
    print(f"Import error: {e}")

class TestChaosOrchestrator(unittest.TestCase):
    """Comprehensive integration tests for the chaos orchestrator"""

    def setUp(self):
        """Set up test client and test database"""
        self.app = app.test_client()
        self.app.testing = True
        
        # Set up test API key
        self.api_key = "test_api_key_2025"
        self.headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        # Mock the security manager for testing
        with patch('orchestrator.chaos_injector.security') as mock_security:
            mock_security.require_api_key = lambda f: f
            mock_security.rate_limit = lambda requests_per_minute: lambda f: f

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('status', data)

    def test_scenarios_endpoint(self):
        """Test scenarios listing endpoint"""
        response = self.app.get('/scenarios')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('scenarios', data)
        self.assertIsInstance(data['scenarios'], list)
        self.assertGreater(len(data['scenarios']), 10)

    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint"""
        response = self.app.get('/metrics')
        self.assertEqual(response.status_code, 200)
        self.assertIn('system_cpu_percent', response.data.decode())
        self.assertIn('system_memory_percent', response.data.decode())

    def test_cpu_spike_injection(self):
        """Test CPU spike chaos injection"""
        payload = {
            'scenario': 'cpu_spike',
            'duration': 2,
            'intensity': 'low'
        }
        
        response = self.app.post('/inject', 
                                headers=self.headers,
                                data=json.dumps(payload))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('result', data)
        self.assertEqual(data['scenario'], 'cpu_spike')

    def test_memory_leak_injection(self):
        """Test memory leak chaos injection"""
        payload = {
            'scenario': 'memory_leak',
            'duration': 2,
            'intensity': 'low'
        }
        
        response = self.app.post('/inject',
                                headers=self.headers,
                                data=json.dumps(payload))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('result', data)
        self.assertEqual(data['scenario'], 'memory_leak')

    def test_invalid_scenario(self):
        """Test handling of invalid chaos scenario"""
        payload = {
            'scenario': 'invalid_scenario',
            'duration': 10,
            'intensity': 'medium'
        }
        
        response = self.app.post('/inject',
                                headers=self.headers,
                                data=json.dumps(payload))
        
        # Should handle gracefully or return error
        self.assertIn(response.status_code, [200, 400])

    def test_duration_validation(self):
        """Test duration parameter validation"""
        # Test too short duration
        payload = {
            'scenario': 'cpu_spike',
            'duration': 0,
            'intensity': 'low'
        }
        
        response = self.app.post('/inject',
                                headers=self.headers,
                                data=json.dumps(payload))
        
        # Should reject invalid duration
        self.assertIn(response.status_code, [400, 422])

    def test_intensity_validation(self):
        """Test intensity parameter validation"""
        payload = {
            'scenario': 'cpu_spike',
            'duration': 5,
            'intensity': 'invalid_intensity'
        }
        
        response = self.app.post('/inject',
                                headers=self.headers,
                                data=json.dumps(payload))
        
        # Should reject invalid intensity
        self.assertIn(response.status_code, [400, 422])

    def test_concurrent_chaos_injection(self):
        """Test multiple concurrent chaos injections"""
        def inject_chaos(scenario):
            payload = {
                'scenario': scenario,
                'duration': 2,
                'intensity': 'low'
            }
            return self.app.post('/inject',
                               headers=self.headers,
                               data=json.dumps(payload))
        
        # Start multiple chaos scenarios concurrently
        threads = []
        scenarios = ['cpu_spike', 'memory_leak']
        
        for scenario in scenarios:
            thread = threading.Thread(target=inject_chaos, args=(scenario,))
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # All should succeed
        for scenario in scenarios:
            response = inject_chaos(scenario)
            self.assertEqual(response.status_code, 200)

    def test_system_status_endpoint(self):
        """Test system status endpoint"""
        response = self.app.get('/system-status')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('system_metrics', data)
        self.assertIn('cpu_percent', data['system_metrics'])

    def test_ui_endpoint(self):
        """Test UI serving"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        
        response = self.app.get('/ui')
        self.assertEqual(response.status_code, 200)

class TestNLPLogAnalyzer(unittest.TestCase):
    """Test AI/ML log analysis functionality"""

    def setUp(self):
        self.analyzer = NLPLogAnalyzer()

    def test_analyze_simple_logs(self):
        """Test basic log analysis"""
        sample_logs = """
        2025-06-18 10:00:01 INFO Application started
        2025-06-18 10:00:02 ERROR Database connection failed
        2025-06-18 10:00:03 CRITICAL Out of memory error
        2025-06-18 10:00:04 WARNING High CPU usage detected
        """
        
        result = self.analyzer.analyze_logs(sample_logs)
        
        self.assertIsInstance(result, dict)
        self.assertIn('total_lines', result)
        self.assertIn('severity_distribution', result)
        self.assertIn('failure_indicators', result)
        
        # Should detect the error and critical entries
        severity_dist = result['severity_distribution']
        self.assertGreater(severity_dist.get('critical', 0), 0)
        self.assertGreater(severity_dist.get('high', 0), 0)

    def test_extract_failure_patterns(self):
        """Test failure pattern extraction"""
        analyzed_logs = {
            'total_lines': 100,
            'severity_distribution': {'critical': 5, 'high': 10, 'medium': 20},
            'failure_indicators': {'memory_issues': 3, 'cpu_issues': 2},
            'affected_services': ['auth-service', 'payment-service']
        }
        
        patterns = self.analyzer.extract_failure_patterns(analyzed_logs)
        
        self.assertIsInstance(patterns, list)
        self.assertGreater(len(patterns), 0)
        
        # Should contain pattern information
        for pattern in patterns:
            self.assertIn('type', pattern)
            self.assertIn('description', pattern)
            self.assertIn('severity', pattern)
            self.assertIn('confidence', pattern)

    def test_predict_failure_likelihood(self):
        """Test failure prediction"""
        current_metrics = {
            'cpu_percent': 85.0,
            'memory_percent': 90.0,
            'disk_percent': 75.0
        }
        
        historical_patterns = [
            {'type': 'high_error_rate', 'severity': 'high'},
            {'type': 'memory_exhaustion', 'severity': 'critical'}
        ]
        
        prediction = self.analyzer.predict_failure_likelihood(current_metrics, historical_patterns)
        
        self.assertIsInstance(prediction, dict)
        self.assertIn('overall_risk', prediction)
        self.assertIn('risk_score', prediction)
        self.assertIn('specific_risks', prediction)
        self.assertIn('recommended_preventive_chaos', prediction)
        
        # High memory usage should trigger high risk
        self.assertGreater(prediction['risk_score'], 0.5)

    def test_invalid_logs_handling(self):
        """Test handling of invalid log input"""
        # Test empty logs
        result = self.analyzer.analyze_logs("")
        self.assertIn('error', result)
        
        # Test None input
        result = self.analyzer.analyze_logs(None)
        self.assertIn('error', result)
        
        # Test non-string input
        result = self.analyzer.analyze_logs(123)
        self.assertIn('error', result)

class TestPerformance(unittest.TestCase):
    """Performance and load testing"""

    def setUp(self):
        self.app = app.test_client()
        self.headers = {
            'X-API-Key': 'test_api_key_2025',
            'Content-Type': 'application/json'
        }

    def test_chaos_injection_performance(self):
        """Test performance of chaos injection under load"""
        start_time = time.time()
        
        # Inject multiple scenarios quickly
        for i in range(10):
            payload = {
                'scenario': 'cpu_spike',
                'duration': 1,
                'intensity': 'low'
            }
            
            response = self.app.post('/inject',
                                   headers=self.headers,
                                   data=json.dumps(payload))
            
            # Should respond quickly
            self.assertEqual(response.status_code, 200)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete all injections in reasonable time
        self.assertLess(total_time, 30)  # 30 seconds max for 10 injections

    def test_metrics_endpoint_performance(self):
        """Test metrics endpoint performance"""
        start_time = time.time()
        
        # Make multiple requests to metrics endpoint
        for i in range(50):
            response = self.app.get('/metrics')
            self.assertEqual(response.status_code, 200)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should respond quickly even under load
        self.assertLess(total_time, 10)  # 10 seconds max for 50 requests

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
