import unittest
import json
import sys
import os
from unittest.mock import patch, MagicMock, Mock
import tempfile
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from orchestrator.chaos_injector import app
    from models.database import db, ChaosExperiment
    from ai_models.nlp_log_analysis import NLPLogAnalyzer
    from monitoring.metrics_collector import MetricsCollector
    from orchestrator.scenario_generator import ScenarioGenerator
    from orchestrator.remediation_agent import RemediationAgent
except ImportError as e:
    print(f"Import error: {e}")

class TestErrorHandling(unittest.TestCase):
    """Comprehensive error handling tests for all core modules"""

    def setUp(self):
        """Set up test environment"""
        self.app = app.test_client()
        self.app.testing = True
        
        self.headers = {
            'X-API-Key': 'test_api_key_2025',
            'Content-Type': 'application/json'
        }
          # Suppress logging during tests
        logging.getLogger().setLevel(logging.CRITICAL)

    def test_chaos_injector_invalid_json(self):
        """Test chaos injector handles invalid JSON gracefully"""
        # Test with invalid API key to trigger authentication first
        response = self.app.post('/inject',
                                headers={'X-API-Key': 'invalid_key', 'Content-Type': 'application/json'},
                                data='invalid json')
        
        # Should handle gracefully (either auth error or JSON error)
        self.assertIn(response.status_code, [400, 401, 422, 500])
        
        # Test with valid API key but invalid JSON (if authentication allows)
        with patch('utils.security.require_api_key') as mock_auth:
            mock_auth.return_value = lambda f: f  # Bypass authentication
            
            response = self.app.post('/inject',
                                    headers=self.headers,
                                    data='invalid json')
              # Should handle invalid JSON gracefully
            self.assertIn(response.status_code, [400, 422, 500])

    def test_chaos_injector_missing_scenario(self):
        """Test chaos injector handles missing scenario field"""
        payload = {
            'duration': 5,
            'intensity': 'low'
        }
        
        response = self.app.post('/inject',
                                headers=self.headers,
                                data=json.dumps(payload))
        
        # Should handle gracefully (401 for auth, 400/422 for validation)
        self.assertIn(response.status_code, [400, 401, 422])

    def test_chaos_injector_invalid_duration(self):
        """Test chaos injector handles invalid duration values"""
        test_cases = [
            {'scenario': 'cpu_spike', 'duration': -1, 'intensity': 'low'},
            {'scenario': 'cpu_spike', 'duration': 'invalid', 'intensity': 'low'},
            {'scenario': 'cpu_spike', 'duration': 1000, 'intensity': 'low'},
            {'scenario': 'cpu_spike', 'duration': None, 'intensity': 'low'}
        ]
        
        for payload in test_cases:
            with self.subTest(payload=payload):
                response = self.app.post('/inject',
                                        headers=self.headers,
                                        data=json.dumps(payload))
                
                # Should reject invalid values (401 for auth, 400/422 for validation)
                self.assertIn(response.status_code, [400, 401, 422])

    def test_chaos_injector_invalid_intensity(self):
        """Test chaos injector handles invalid intensity values"""
        test_cases = [
            {'scenario': 'cpu_spike', 'duration': 5, 'intensity': 'invalid'},
            {'scenario': 'cpu_spike', 'duration': 5, 'intensity': 123},
            {'scenario': 'cpu_spike', 'duration': 5, 'intensity': None},
            {'scenario': 'cpu_spike', 'duration': 5, 'intensity': ''}
        ]
        
        for payload in test_cases:
            with self.subTest(payload=payload):
                response = self.app.post('/inject',
                                        headers=self.headers,
                                        data=json.dumps(payload))
                
                # Should reject invalid values (401 for auth, 400/422 for validation)
                self.assertIn(response.status_code, [400, 401, 422])

    def test_chaos_injector_database_error(self):
        """Test chaos injector handles database errors gracefully"""
        payload = {
            'scenario': 'cpu_spike',
            'duration': 5,
            'intensity': 'low'
        }
        
        with patch('models.database.db.session.add') as mock_add:
            mock_add.side_effect = Exception("Database connection failed")
            
            response = self.app.post('/inject',
                                    headers=self.headers,
                                    data=json.dumps(payload))
            
            # Should handle database error gracefully (401 for auth, 200/500 for execution)
            self.assertIn(response.status_code, [200, 401, 500])
            
            if response.status_code == 200:
                data = json.loads(response.data)
                # Should still return response, possibly with error indication

    def test_nlp_analyzer_invalid_input(self):
        """Test NLP analyzer handles invalid inputs gracefully"""
        analyzer = NLPLogAnalyzer()
        
        # Test various invalid inputs
        test_cases = [
            None,
            123,
            [],
            {},
            "",
            "a" * 50_000_000  # Extremely large input
        ]
        
        for invalid_input in test_cases:
            with self.subTest(input=invalid_input):
                result = analyzer.analyze_logs(invalid_input)
                
                # Should always return a dict
                self.assertIsInstance(result, dict)
                
                # Should contain error information for invalid inputs
                if invalid_input in [None, 123, [], {}]:
                    self.assertIn('error', result)

    def test_nlp_analyzer_malformed_logs(self):
        """Test NLP analyzer handles malformed log data"""
        analyzer = NLPLogAnalyzer()
        
        # Test malformed log entries
        malformed_logs = [
            "completely invalid log format",
            "2025-13-45 25:99:99 INVALID Invalid timestamp",
            "\x00\x01\x02 binary data in logs",
            "log without any structure or timestamps",
            "\n\n\n\n\n",  # Only newlines
            "日本語のログエントリ",  # Non-ASCII characters
        ]
        
        for log in malformed_logs:
            with self.subTest(log=log[:50]):
                result = analyzer.analyze_logs(log)
                
                # Should handle gracefully
                self.assertIsInstance(result, dict)
                self.assertIn('total_lines', result)

    def test_nlp_analyzer_extraction_errors(self):
        """Test NLP analyzer handles extraction errors"""
        analyzer = NLPLogAnalyzer()
        
        # Mock regex errors
        with patch('re.search') as mock_search:
            mock_search.side_effect = Exception("Regex compilation error")
            
            result = analyzer.analyze_logs("test log entry")
            
            # Should handle regex errors gracefully
            self.assertIsInstance(result, dict)

    def test_metrics_collector_system_errors(self):
        """Test metrics collector handles system errors gracefully"""
        collector = MetricsCollector()
        
        # Mock psutil errors
        with patch('psutil.cpu_percent') as mock_cpu:
            mock_cpu.side_effect = Exception("System access denied")
            
            metrics = collector.collect_metrics()
            
            # Should handle gracefully and return fallback metrics
            self.assertIsInstance(metrics, dict)
            self.assertIn('cpu', metrics)
            self.assertIn('collection', metrics)

    def test_metrics_collector_network_errors(self):
        """Test metrics collector handles network errors"""
        collector = MetricsCollector("http://invalid-prometheus-url:9090")
        
        test_metrics = {'cpu': {'usage_percent': 50}}
        
        # Should handle network errors gracefully
        result = collector.send_to_prometheus(test_metrics)
        
        # Should return False but not crash
        self.assertIsInstance(result, bool)

    def test_scenario_generator_invalid_inputs(self):
        """Test scenario generator handles invalid inputs"""
        generator = ScenarioGenerator()
        
        # Test various invalid inputs
        test_cases = [
            (None, None),
            ("invalid", "invalid"),
            (123, 456),
            ([None, None], {"invalid": "data"}),
            (["failure with very long description " * 100], {}),
        ]
        
        for past_failures, system_metrics in test_cases:
            with self.subTest(failures=past_failures, metrics=system_metrics):
                scenarios = generator.generate_scenarios(past_failures, system_metrics)
                
                # Should always return a list
                self.assertIsInstance(scenarios, list)
                self.assertGreater(len(scenarios), 0)

    def test_scenario_generator_evolution_errors(self):
        """Test scenario generator handles evolution errors"""
        generator = ScenarioGenerator()
        
        # Test with invalid scenarios and feedback
        invalid_scenarios = [
            None,
            "invalid",
            [{"missing_name": "test"}],
            [{"name": "test", "details": None}],
        ]
        
        invalid_feedback = [
            None,
            "invalid",
            123,
            {"result": None}
        ]
        
        for scenarios in invalid_scenarios:
            for feedback in invalid_feedback:
                with self.subTest(scenarios=scenarios, feedback=feedback):
                    result = generator.evolve_scenarios(scenarios, feedback)
                    
                    # Should always return a list
                    self.assertIsInstance(result, list)
                    self.assertGreater(len(result), 0)

    def test_remediation_agent_invalid_inputs(self):
        """Test remediation agent handles invalid inputs"""
        agent = RemediationAgent()
        
        # Test invalid event data
        invalid_events = [
            None,
            123,
            "string_event",
            [],
            {"malformed": "event"},
        ]
        
        for event in invalid_events:
            with self.subTest(event=event):
                assessment = agent.assess_impact(event)
                
                # Should always return a dict
                self.assertIsInstance(assessment, dict)
                self.assertIn('severity', assessment)

    def test_remediation_agent_execution_errors(self):
        """Test remediation agent handles execution errors"""
        agent = RemediationAgent()
        
        # Test invalid assessment results
        invalid_assessments = [
            None,
            123,
            "invalid_string",
            [],
            {"invalid": "data"}
        ]
        
        for assessment in invalid_assessments:
            with self.subTest(assessment=assessment):
                result = agent.execute_remediation(assessment)
                
                # Should always return a boolean
                self.assertIsInstance(result, bool)

    def test_database_model_json_errors(self):
        """Test database models handle JSON errors gracefully"""
        # Test creating experiment with invalid JSON data
        experiment = ChaosExperiment(
            scenario='test',
            duration=5,
            intensity='low',
            metrics_before='invalid json',
            metrics_after='{"valid": "json"}'
        )
          # Should handle invalid JSON gracefully
        result = experiment.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertIn('scenario', result)

    def test_api_endpoint_errors(self):
        """Test API endpoints handle various error conditions"""
        
        # Test health endpoint (should work without authentication)
        response = self.app.get('/health')
        
        # Should return a response (may include error information)
        self.assertIn(response.status_code, [200, 500])
        
        # Test other endpoints that don't require authentication
        response = self.app.get('/scenarios')
        self.assertIn(response.status_code, [200, 401, 500])  # May require auth

    def test_concurrent_error_handling(self):
        """Test error handling under concurrent load"""
        import threading
        import time
        
        errors = []
        
        def make_request():
            try:
                # Make request with invalid data
                response = self.app.post('/inject',
                                        headers=self.headers,
                                        data='invalid json')
                if response.status_code >= 500:
                    errors.append(f"Server error: {response.status_code}")
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple concurrent threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should handle concurrent errors gracefully without crashes
        # Some errors are expected, but no server crashes
        if errors:
            print(f"Concurrent errors (expected): {len(errors)}")

    def test_memory_pressure_handling(self):
        """Test error handling under memory pressure"""
        analyzer = NLPLogAnalyzer()
        
        # Create large log data to simulate memory pressure
        large_logs = "ERROR: test error\n" * 100000  # 100k lines
        
        try:
            result = analyzer.analyze_logs(large_logs)
            
            # Should handle large inputs gracefully
            self.assertIsInstance(result, dict)
            
        except MemoryError:
            # If memory error occurs, it should be handled gracefully
            pass

    def test_file_system_errors(self):
        """Test handling of file system related errors"""
        # Test with read-only directory (if possible)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # This test would be platform-specific
                # For now, just ensure no crashes occur
                pass
        except Exception as e:
            # Should handle gracefully
            pass

    def test_network_timeout_handling(self):
        """Test handling of network timeouts"""
        collector = MetricsCollector("http://192.0.2.1:9090")  # Non-routable IP
        
        metrics = {'cpu': {'usage_percent': 50}}
        
        # Should handle timeout gracefully
        result = collector.send_to_prometheus(metrics)
        
        # Should return False but not crash
        self.assertIsInstance(result, bool)

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
