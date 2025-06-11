import unittest
from src.orchestrator.scenario_generator import ScenarioGenerator

class TestScenarioGenerator(unittest.TestCase):

    def setUp(self):
        self.scenario_generator = ScenarioGenerator()


    def test_generate_scenarios(self):
        past_failures = ["failure1", "failure2"]
        system_metrics = {"cpu": 80, "memory": 70}
        scenarios = self.scenario_generator.generate_scenarios(past_failures, system_metrics)
        self.assertIsInstance(scenarios, list)

    def test_evolve_scenarios(self):
        past_failures = ["failure1"]
        system_metrics = {"cpu": 80}
        initial_scenarios = self.scenario_generator.generate_scenarios(past_failures, system_metrics)
        feedback = {"result": "success"}
        evolved_scenarios = self.scenario_generator.evolve_scenarios(initial_scenarios, feedback)
        self.assertIsInstance(evolved_scenarios, list)

    def test_evolve_scenarios_no_args(self):
        # Provide dummy arguments to match the method signature
        past_failures = ["failure1"]
        system_metrics = {"cpu": 80}
        initial_scenarios = self.scenario_generator.generate_scenarios(past_failures, system_metrics)
        feedback = {"result": "success"}
        evolved_scenarios = self.scenario_generator.evolve_scenarios(initial_scenarios, feedback)
        self.assertNotEqual(initial_scenarios, evolved_scenarios)
        self.assertIsInstance(evolved_scenarios, list)

if __name__ == '__main__':
    unittest.main()