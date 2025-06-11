import unittest
from src.orchestrator.remediation_agent import RemediationAgent

class TestRemediationAgent(unittest.TestCase):

    def setUp(self):
        self.agent = RemediationAgent()


    def test_assess_impact(self):
        # Simulate a chaos scenario impact
        impact = self.agent.assess_impact({"event": "network_failure"})
        self.assertIsNotNone(impact)
        self.assertIn("severity", impact)
        self.assertIn("affected_services", impact)


    def test_execute_remediation(self):
        # Simulate executing a remediation strategy
        self.agent.current_state = "unhealthy"
        result = self.agent.execute_remediation("remediate_network_failure")
        self.assertTrue(result)
        self.assertEqual(self.agent.current_state, "healthy")

if __name__ == '__main__':
    unittest.main()