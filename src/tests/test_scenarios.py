import unittest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from orchestrator.scenario_generator import ScenarioGenerator

class TestScenarioGenerator(unittest.TestCase):
    """Enhanced tests for ScenarioGenerator with error handling scenarios"""

    def setUp(self):
        self.scenario_generator = ScenarioGenerator()

    def test_generate_scenarios_success(self):
        """Test successful scenario generation"""
        past_failures = ["cpu failure", "memory issue"]
        system_metrics = {"cpu": 80, "memory": 70}
        scenarios = self.scenario_generator.generate_scenarios(past_failures, system_metrics)
        
        self.assertIsInstance(scenarios, list)
        self.assertGreater(len(scenarios), 0)
        
        # Check scenario structure
        for scenario in scenarios:
            self.assertIn('name', scenario)
            self.assertIn('details', scenario)

    def test_generate_scenarios_empty_inputs(self):
        """Test scenario generation with empty inputs"""
        scenarios = self.scenario_generator.generate_scenarios([], {})
        
        self.assertIsInstance(scenarios, list)
        self.assertGreater(len(scenarios), 0)  # Should return defaults

    def test_generate_scenarios_none_inputs(self):
        """Test scenario generation with None inputs"""
        scenarios = self.scenario_generator.generate_scenarios(None, None)
        
        self.assertIsInstance(scenarios, list)
        self.assertGreater(len(scenarios), 0)  # Should return defaults

    def test_generate_scenarios_invalid_types(self):
        """Test scenario generation with invalid input types"""
        test_cases = [
            ("string", "string"),
            (123, 456),
            ({"dict": "instead_of_list"}, ["list", "instead_of_dict"]),
        ]
        
        for past_failures, system_metrics in test_cases:
            with self.subTest(failures=past_failures, metrics=system_metrics):
                scenarios = self.scenario_generator.generate_scenarios(past_failures, system_metrics)
                
                self.assertIsInstance(scenarios, list)
                self.assertGreater(len(scenarios), 0)

    def test_generate_scenarios_complex_failures(self):
        """Test scenario generation with complex failure objects"""
        past_failures = [
            {"description": "CPU spike in production", "severity": "high"},
            {"message": "Memory leak detected", "service": "api"},
            "simple string failure",
            123,  # Invalid type
            None,  # None value
        ]
        
        system_metrics = {"cpu": 90, "memory": 85, "disk": 95}
        scenarios = self.scenario_generator.generate_scenarios(past_failures, system_metrics)
        
        self.assertIsInstance(scenarios, list)
        self.assertGreater(len(scenarios), 0)

    def test_generate_scenarios_large_input(self):
        """Test scenario generation with large inputs"""
        # Test with many failures
        past_failures = [f"failure_{i}" for i in range(100)]
        system_metrics = {"cpu": 50, "memory": 60}
        
        scenarios = self.scenario_generator.generate_scenarios(past_failures, system_metrics)
        
        self.assertIsInstance(scenarios, list)
        # Should limit scenarios to max_scenarios
        self.assertLessEqual(len(scenarios), self.scenario_generator.max_scenarios)

    def test_generate_scenarios_invalid_metrics(self):
        """Test scenario generation with invalid metric values"""
        past_failures = ["test failure"]
        
        invalid_metrics = [
            {"cpu": "invalid", "memory": None},
            {"cpu": float('inf'), "memory": float('nan')},
            {"cpu": -1, "memory": 200},  # Invalid ranges
        ]
        
        for metrics in invalid_metrics:
            with self.subTest(metrics=metrics):
                scenarios = self.scenario_generator.generate_scenarios(past_failures, metrics)
                
                self.assertIsInstance(scenarios, list)
                self.assertGreater(len(scenarios), 0)

    def test_evolve_scenarios_success(self):
        """Test successful scenario evolution"""
        past_failures = ["failure1"]
        system_metrics = {"cpu": 80}
        initial_scenarios = self.scenario_generator.generate_scenarios(past_failures, system_metrics)
        
        feedback = {"result": "success"}
        evolved_scenarios = self.scenario_generator.evolve_scenarios(initial_scenarios, feedback)
        
        self.assertIsInstance(evolved_scenarios, list)
        self.assertGreater(len(evolved_scenarios), 0)

    def test_evolve_scenarios_with_failure_feedback(self):
        """Test scenario evolution with failure feedback"""
        scenarios = [{"name": "CPU spike", "details": "Basic CPU test"}]
        feedback = {"result": "failure"}
        
        evolved_scenarios = self.scenario_generator.evolve_scenarios(scenarios, feedback)
        
        self.assertIsInstance(evolved_scenarios, list)
        self.assertGreater(len(evolved_scenarios), 0)
        
        # Should modify the details
        self.assertIn("alternative failure mode", evolved_scenarios[0]["details"])

    def test_evolve_scenarios_none_inputs(self):
        """Test scenario evolution with None inputs"""
        evolved_scenarios = self.scenario_generator.evolve_scenarios(None, None)
        
        self.assertIsInstance(evolved_scenarios, list)
        self.assertGreater(len(evolved_scenarios), 0)

    def test_evolve_scenarios_invalid_types(self):
        """Test scenario evolution with invalid input types"""
        test_cases = [
            ("string", "string"),
            (123, 456),
            ([], "not_dict"),
            ("not_list", {}),
        ]
        
        for scenarios, feedback in test_cases:
            with self.subTest(scenarios=scenarios, feedback=feedback):
                result = self.scenario_generator.evolve_scenarios(scenarios, feedback)
                
                self.assertIsInstance(result, list)
                self.assertGreater(len(result), 0)

    def test_evolve_scenarios_malformed_scenarios(self):
        """Test scenario evolution with malformed scenario objects"""
        malformed_scenarios = [
            {"missing_name": "test"},  # Missing required 'name' field
            {"name": "test", "details": None},  # None details
            {"name": None, "details": "test"},  # None name
            "not_a_dict",  # Not a dictionary
            None,  # None value
        ]
        
        feedback = {"result": "success"}
        
        evolved_scenarios = self.scenario_generator.evolve_scenarios(malformed_scenarios, feedback)
        
        self.assertIsInstance(evolved_scenarios, list)
        self.assertGreater(len(evolved_scenarios), 0)

    def test_evolve_scenarios_with_suggestions(self):
        """Test scenario evolution with feedback suggestions"""
        scenarios = [{"name": "Basic test", "details": "Basic scenario"}]
        feedback = {
            "result": "success",
            "add_network_partition": True,
            "add_cpu_spike": True
        }
        
        evolved_scenarios = self.scenario_generator.evolve_scenarios(scenarios, feedback)
        
        self.assertIsInstance(evolved_scenarios, list)
        self.assertGreater(len(evolved_scenarios), 1)  # Should have added scenarios
        
        # Check if suggested scenarios were added
        scenario_names = [s.get("name", "") for s in evolved_scenarios]
        self.assertIn("Network partition", scenario_names)

    def test_evolve_scenarios_large_input(self):
        """Test scenario evolution with large scenario list"""
        large_scenarios = [
            {"name": f"scenario_{i}", "details": f"details_{i}"}
            for i in range(100)
        ]
        
        feedback = {"result": "success"}
        
        evolved_scenarios = self.scenario_generator.evolve_scenarios(large_scenarios, feedback)
        
        self.assertIsInstance(evolved_scenarios, list)
        # Should limit to max_scenarios
        self.assertLessEqual(len(evolved_scenarios), self.scenario_generator.max_scenarios)

    def test_evolve_scenarios_no_args(self):
        """Test scenario evolution with no arguments (backwards compatibility)"""
        # This test maintains backwards compatibility with the original test
        past_failures = ["failure1"]
        system_metrics = {"cpu": 80}
        initial_scenarios = self.scenario_generator.generate_scenarios(past_failures, system_metrics)
        feedback = {"result": "success"}
        
        evolved_scenarios = self.scenario_generator.evolve_scenarios(initial_scenarios, feedback)
        
        self.assertNotEqual(initial_scenarios, evolved_scenarios)
        self.assertIsInstance(evolved_scenarios, list)

    def test_scenario_generator_defaults(self):
        """Test scenario generator default behaviors"""
        # Test max_scenarios limit
        self.assertIsInstance(self.scenario_generator.max_scenarios, int)
        self.assertGreater(self.scenario_generator.max_scenarios, 0)
        
        # Test default_scenarios
        self.assertIsInstance(self.scenario_generator.default_scenarios, list)
        self.assertGreater(len(self.scenario_generator.default_scenarios), 0)

    def test_scenario_content_validation(self):
        """Test that generated scenarios have valid content"""
        past_failures = ["cpu failure", "memory leak", "network issue"]
        system_metrics = {"cpu": 90, "memory": 85}
        
        scenarios = self.scenario_generator.generate_scenarios(past_failures, system_metrics)
        
        for scenario in scenarios:
            # All scenarios should have name and details
            self.assertIn('name', scenario)
            self.assertIn('details', scenario)
            
            # Name and details should be non-empty strings
            self.assertIsInstance(scenario['name'], str)
            self.assertIsInstance(scenario['details'], str)
            self.assertGreater(len(scenario['name']), 0)
            self.assertGreater(len(scenario['details']), 0)

if __name__ == '__main__':
    unittest.main()