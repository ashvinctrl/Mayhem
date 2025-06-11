class ScenarioGenerator:
    def generate_scenarios(self, past_failures, system_metrics):
        """
        Generate chaos scenarios based on past failures and current system metrics.
        
        :param past_failures: List of past failure incidents.
        :param system_metrics: Current metrics of the system.
        :return: List of generated chaos scenarios.
        """
        scenarios = []
        # Analyze past failures to create targeted scenarios
        for failure in past_failures:
            if "cpu" in failure.lower():
                scenarios.append({
                    "name": "CPU spike",
                    "details": "Simulate high CPU usage based on past CPU failure"
                })
            elif "memory" in failure.lower():
                scenarios.append({
                    "name": "Memory leak",
                    "details": "Simulate memory leak based on past memory failure"
                })
            elif "network" in failure.lower():
                scenarios.append({
                    "name": "Network partition",
                    "details": "Simulate network issues based on past network failure"
                })
            else:
                scenarios.append({
                    "name": "Generic failure",
                    "details": f"Simulate failure: {failure}"
                })

        # Use system metrics to add proactive scenarios
        if system_metrics.get("cpu", 0) > 85:
            scenarios.append({
                "name": "CPU stress",
                "details": "Current CPU usage is high, stress test CPU"
            })
        if system_metrics.get("memory", 0) > 85:
            scenarios.append({
                "name": "Memory stress",
                "details": "Current memory usage is high, stress test memory"
            })
        if system_metrics.get("disk", 0) > 90:
            scenarios.append({
                "name": "Disk full",
                "details": "Disk usage is high, simulate disk full scenario"
            })

        # Remove duplicates
        unique_scenarios = [dict(t) for t in {tuple(d.items()) for d in scenarios}]
        return unique_scenarios

    def evolve_scenarios(self, scenarios, feedback):
        """
        Evolve existing chaos scenarios based on feedback from previous experiments.
        
        :param scenarios: List of existing chaos scenarios.
        :param feedback: Feedback from the outcomes of previous chaos experiments.
        :return: List of evolved chaos scenarios.
        """
        evolved_scenarios = []
        for scenario in scenarios:
            # If feedback indicates success, increase severity or add new failure mode
            if feedback.get("result") == "success":
                evolved = scenario.copy()
                evolved["details"] += " (increased severity)"
                evolved_scenarios.append(evolved)
            elif feedback.get("result") == "failure":
                # If failure, try a different type of chaos
                evolved = scenario.copy()
                evolved["details"] += " (try alternative failure mode)"
                evolved_scenarios.append(evolved)
            else:
                evolved_scenarios.append(scenario)
        # Optionally add a new scenario if feedback suggests
        if feedback.get("add_network_partition"):
            evolved_scenarios.append({
                "name": "Network partition",
                "details": "Simulate network issues as suggested by feedback"
            })
        return evolved_scenarios