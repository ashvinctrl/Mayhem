import unittest
import time
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from orchestrator.remediation_agent import RemediationAgent

class TestRemediationAgent(unittest.TestCase):
    """Enhanced tests for RemediationAgent with error handling scenarios"""

    def setUp(self):
        self.agent = RemediationAgent()

    def test_assess_impact_success(self):
        """Test successful impact assessment"""
        event = {"event": "network_failure", "intensity": "high", "duration": 60}
        impact = self.agent.assess_impact(event)
        
        self.assertIsNotNone(impact)
        self.assertIsInstance(impact, dict)
        self.assertIn("severity", impact)
        self.assertIn("affected_services", impact)
        self.assertIn("confidence", impact)

    def test_assess_impact_string_input(self):
        """Test impact assessment with string input"""
        impact = self.agent.assess_impact("network_failure")
        
        self.assertIsInstance(impact, dict)
        self.assertIn("severity", impact)
        self.assertIn("affected_services", impact)

    def test_assess_impact_none_input(self):
        """Test impact assessment with None input"""
        impact = self.agent.assess_impact(None)
        
        self.assertIsInstance(impact, dict)
        self.assertIn("severity", impact)
        self.assertIn("error", impact)

    def test_assess_impact_invalid_types(self):
        """Test impact assessment with invalid input types"""
        invalid_inputs = [123, [], set(), lambda: None]
        
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                impact = self.agent.assess_impact(invalid_input)
                
                self.assertIsInstance(impact, dict)
                self.assertIn("severity", impact)
                self.assertIn("error", impact)

    def test_assess_impact_malformed_dict(self):
        """Test impact assessment with malformed dictionary"""
        malformed_events = [
            {},  # Empty dict
            {"invalid": "data"},  # Missing expected fields
            {"event": None},  # None event type
            {"event": "", "intensity": None},  # Empty/None values
        ]
        
        for event in malformed_events:
            with self.subTest(event=event):
                impact = self.agent.assess_impact(event)
                
                self.assertIsInstance(impact, dict)
                self.assertIn("severity", impact)

    def test_assess_impact_various_severities(self):
        """Test impact assessment with different severity levels"""
        test_cases = [
            {"event": "cpu_spike", "intensity": "low", "duration": 10},
            {"event": "memory_leak", "intensity": "high", "duration": 300},
            {"event": "network_partition", "intensity": "critical", "duration": 600},
        ]
        
        for event in test_cases:
            with self.subTest(event=event):
                impact = self.agent.assess_impact(event)
                
                self.assertIsInstance(impact, dict)
                self.assertIn("severity", impact)
                self.assertIn(impact["severity"], ["low", "medium", "high", "critical"])

    def test_execute_remediation_success(self):
        """Test successful remediation execution"""
        assessment = {"strategy": "remediate_network_failure", "severity": "high"}
        result = self.agent.execute_remediation(assessment)
        
        self.assertIsInstance(result, bool)
        if result:
            self.assertEqual(self.agent.current_state, "healthy")

    def test_execute_remediation_string_input(self):
        """Test remediation execution with string input"""
        result = self.agent.execute_remediation("remediate_network_failure")
        
        self.assertIsInstance(result, bool)

    def test_execute_remediation_none_input(self):
        """Test remediation execution with None input"""
        result = self.agent.execute_remediation(None)
        
        self.assertIsInstance(result, bool)
        self.assertFalse(result)  # Should fail gracefully

    def test_execute_remediation_invalid_types(self):
        """Test remediation execution with invalid input types"""
        invalid_inputs = [123, [], set(), lambda: None]
        
        for invalid_input in invalid_inputs:
            with self.subTest(input=invalid_input):
                result = self.agent.execute_remediation(invalid_input)
                
                self.assertIsInstance(result, bool)
                self.assertFalse(result)  # Should fail gracefully

    def test_execute_remediation_various_strategies(self):
        """Test remediation execution with various strategies"""
        strategies = [
            {"strategy": "remediate_cpu_spike", "event_type": "cpu_spike"},
            {"strategy": "remediate_memory_leak", "event_type": "memory_leak"},
            {"strategy": "remediate_disk_full", "event_type": "disk_full"},
            {"strategy": "unknown_strategy", "event_type": "unknown"},
        ]
        
        for assessment in strategies:
            with self.subTest(assessment=assessment):
                result = self.agent.execute_remediation(assessment)
                
                self.assertIsInstance(result, bool)

    def test_remediation_history_tracking(self):
        """Test that remediation history is properly tracked"""
        initial_history_count = len(self.agent.remediation_history)
        
        # Execute some remediations
        assessments = [
            {"strategy": "remediate_network_failure"},
            {"strategy": "remediate_cpu_spike"},
        ]
        
        for assessment in assessments:
            self.agent.execute_remediation(assessment)
        
        # History should have grown
        self.assertGreater(len(self.agent.remediation_history), initial_history_count)

    def test_remediation_history_limit(self):
        """Test that remediation history respects size limit"""
        # Fill history beyond limit
        for i in range(self.agent.max_history + 10):
            self.agent._record_remediation(f"strategy_{i}", "test", True, 0.1)
        
        # Should not exceed max_history
        self.assertLessEqual(len(self.agent.remediation_history), self.agent.max_history)

    def test_get_remediation_status(self):
        """Test remediation status reporting"""
        status = self.agent.get_remediation_status()
        
        self.assertIsInstance(status, dict)
        self.assertIn('current_state', status)
        self.assertIn('history_count', status)
        self.assertIn('supported_events', status)

    def test_remediation_state_transitions(self):
        """Test state transitions during remediation"""
        # Initial state
        initial_state = self.agent.current_state
        
        # Successful remediation
        result = self.agent.execute_remediation({"strategy": "remediate_network_failure"})
        if result:
            self.assertEqual(self.agent.current_state, "healthy")

    def test_concurrent_remediation(self):
        """Test concurrent remediation attempts"""
        import threading
        
        results = []
        errors = []
        
        def execute_remediation():
            try:
                result = self.agent.execute_remediation({"strategy": "remediate_cpu_spike"})
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple remediation threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=execute_remediation)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should handle concurrent access gracefully
        self.assertEqual(len(results), 5)
        self.assertEqual(len(errors), 0)

    def test_severity_calculation_edge_cases(self):
        """Test severity calculation with edge cases"""
        test_cases = [
            ("unknown_event", "invalid_intensity", -1),
            ("cpu_spike", "", 0),
            ("memory_leak", "critical", 10000),  # Very long duration
            (None, None, None),
        ]
        
        for event_type, intensity, duration in test_cases:
            try:
                severity = self.agent._calculate_severity(event_type or "", intensity or "", duration or 0)
                self.assertIn(severity, ["low", "medium", "high", "critical"])
            except Exception:
                # Should not raise exceptions
                self.fail("_calculate_severity raised an exception")

    def test_service_identification_edge_cases(self):
        """Test service identification with edge cases"""
        test_cases = [
            ("unknown_event", {}),
            ("cpu_spike", {"affected_services": "not_a_list"}),
            ("memory_leak", {"affected_services": list(range(20))}),  # Too many services
            (None, None),
        ]
        
        for event_type, event_data in test_cases:
            try:
                services = self.agent._identify_affected_services(event_type or "", event_data or {})
                self.assertIsInstance(services, list)
                self.assertLessEqual(len(services), 10)  # Should limit services
            except Exception:
                # Should not raise exceptions
                self.fail("_identify_affected_services raised an exception")

    def test_confidence_calculation_edge_cases(self):
        """Test confidence calculation with edge cases"""
        test_cases = [
            ("unknown_event", {}),
            ("cpu_spike", {"invalid": "data"}),
            (None, None),
        ]
        
        for event_type, event_data in test_cases:
            try:
                confidence = self.agent._calculate_confidence(event_type or "", event_data or {})
                self.assertIsInstance(confidence, float)
                self.assertGreaterEqual(confidence, 0.0)
                self.assertLessEqual(confidence, 1.0)
            except Exception:
                # Should not raise exceptions
                self.fail("_calculate_confidence raised an exception")

    def test_recommendations_generation_edge_cases(self):
        """Test recommendations generation with edge cases"""
        test_cases = [
            ("unknown_event", "unknown_severity"),
            (None, None),
            ("", ""),
        ]
        
        for event_type, severity in test_cases:
            try:
                recommendations = self.agent._generate_recommendations(event_type or "", severity or "")
                self.assertIsInstance(recommendations, list)
                self.assertGreater(len(recommendations), 0)
            except Exception:
                # Should not raise exceptions
                self.fail("_generate_recommendations raised an exception")

if __name__ == '__main__':
    unittest.main()