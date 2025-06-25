import logging
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScenarioGenerator:
    """Chaos scenario generator with comprehensive error handling"""
    
    def __init__(self):
        """Initialize the scenario generator with default configurations"""
        self.max_scenarios = 50  # Prevent excessive scenario generation
        self.default_scenarios = [
            {"name": "CPU spike", "details": "Basic CPU stress test"},
            {"name": "Memory leak", "details": "Basic memory stress test"},
            {"name": "Network latency", "details": "Basic network degradation test"}
        ]
        logger.info("ScenarioGenerator initialized")
    
    def generate_scenarios(self, past_failures: Optional[List[Union[str, Dict]]] = None, 
                         system_metrics: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """
        Generate chaos scenarios based on past failures and current system metrics.
        
        :param past_failures: List of past failure incidents.
        :param system_metrics: Current metrics of the system.
        :return: List of generated chaos scenarios.
        """
        try:
            scenarios = []
            
            # Input validation
            if past_failures is None:
                past_failures = []
                logger.debug("No past failures provided, using empty list")
            
            if system_metrics is None:
                system_metrics = {}
                logger.debug("No system metrics provided, using empty dict")
            
            # Validate past_failures is a list
            if not isinstance(past_failures, list):
                logger.warning(f"past_failures should be a list, got {type(past_failures)}")
                past_failures = []
            
            # Validate system_metrics is a dict
            if not isinstance(system_metrics, dict):
                logger.warning(f"system_metrics should be a dict, got {type(system_metrics)}")
                system_metrics = {}
            
            # Analyze past failures to create targeted scenarios
            try:
                for failure in past_failures[:20]:  # Limit to first 20 failures to prevent excessive processing
                    try:
                        # Handle both string and dict failure entries
                        failure_text = ""
                        if isinstance(failure, str):
                            failure_text = failure
                        elif isinstance(failure, dict):
                            failure_text = failure.get('description', failure.get('message', str(failure)))
                        else:
                            logger.debug(f"Skipping invalid failure entry: {failure}")
                            continue
                        
                        failure_lower = failure_text.lower()
                        
                        if "cpu" in failure_lower:
                            scenarios.append({
                                "name": "CPU spike",
                                "details": "Simulate high CPU usage based on past CPU failure"
                            })
                        elif "memory" in failure_lower:
                            scenarios.append({
                                "name": "Memory leak",
                                "details": "Simulate memory leak based on past memory failure"
                            })
                        elif "network" in failure_lower:
                            scenarios.append({
                                "name": "Network partition",
                                "details": "Simulate network issues based on past network failure"
                            })
                        else:
                            scenarios.append({
                                "name": "Generic failure",
                                "details": f"Simulate failure: {failure_text[:100]}"  # Truncate long descriptions
                            })
                    except Exception as e:
                        logger.warning(f"Error processing failure entry: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error processing past failures: {e}")
            
            # Use system metrics to add proactive scenarios
            try:
                cpu_usage = system_metrics.get("cpu", 0)
                memory_usage = system_metrics.get("memory", 0)
                disk_usage = system_metrics.get("disk", 0)
                
                # Validate metric values
                if isinstance(cpu_usage, (int, float)) and cpu_usage > 85:
                    scenarios.append({
                        "name": "CPU stress",
                        "details": f"Current CPU usage is high ({cpu_usage}%), stress test CPU"
                    })
                
                if isinstance(memory_usage, (int, float)) and memory_usage > 85:
                    scenarios.append({
                        "name": "Memory stress",
                        "details": f"Current memory usage is high ({memory_usage}%), stress test memory"
                    })
                
                if isinstance(disk_usage, (int, float)) and disk_usage > 90:
                    scenarios.append({
                        "name": "Disk full",
                        "details": f"Disk usage is high ({disk_usage}%), simulate disk full scenario"
                    })
                    
            except Exception as e:
                logger.error(f"Error processing system metrics: {e}")
            
            # Remove duplicates safely
            try:
                unique_scenarios = []
                seen = set()
                
                for scenario in scenarios:
                    if isinstance(scenario, dict) and 'name' in scenario:
                        scenario_key = (scenario['name'], scenario.get('details', ''))
                        if scenario_key not in seen:
                            seen.add(scenario_key)
                            unique_scenarios.append(scenario)
                
                # Ensure we don't exceed max scenarios
                if len(unique_scenarios) > self.max_scenarios:
                    logger.warning(f"Generated {len(unique_scenarios)} scenarios, truncating to {self.max_scenarios}")
                    unique_scenarios = unique_scenarios[:self.max_scenarios]
                
                # If no scenarios were generated, use defaults
                if not unique_scenarios:
                    logger.info("No scenarios generated from inputs, using default scenarios")
                    unique_scenarios = self.default_scenarios.copy()
                
                logger.info(f"Generated {len(unique_scenarios)} chaos scenarios")
                return unique_scenarios
                
            except Exception as e:
                logger.error(f"Error removing duplicates: {e}")
                return self.default_scenarios.copy()
            
        except Exception as e:
            logger.error(f"Critical error in scenario generation: {e}")
            return self.default_scenarios.copy()

    def evolve_scenarios(self, scenarios: Optional[List[Dict[str, str]]] = None, 
                        feedback: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """
        Evolve existing chaos scenarios based on feedback from previous experiments.
        
        :param scenarios: List of existing chaos scenarios.
        :param feedback: Feedback from the outcomes of previous chaos experiments.
        :return: List of evolved chaos scenarios.
        """
        try:
            # Input validation
            if scenarios is None:
                scenarios = self.default_scenarios.copy()
                logger.debug("No scenarios provided, using defaults")
            
            if feedback is None:
                feedback = {}
                logger.debug("No feedback provided, using empty dict")
            
            if not isinstance(scenarios, list):
                logger.warning(f"scenarios should be a list, got {type(scenarios)}")
                scenarios = self.default_scenarios.copy()
            
            if not isinstance(feedback, dict):
                logger.warning(f"feedback should be a dict, got {type(feedback)}")
                feedback = {}
            
            evolved_scenarios = []
            
            try:
                for scenario in scenarios[:self.max_scenarios]:  # Limit processing
                    try:
                        if not isinstance(scenario, dict):
                            logger.debug(f"Skipping invalid scenario: {scenario}")
                            continue
                        
                        # Ensure scenario has required fields
                        if 'name' not in scenario:
                            logger.debug(f"Scenario missing 'name' field: {scenario}")
                            continue
                        
                        scenario_copy = scenario.copy()
                        
                        # If feedback indicates success, increase severity or add new failure mode
                        feedback_result = feedback.get("result", "unknown")
                        
                        if feedback_result == "success":
                            details = scenario_copy.get("details", "")
                            scenario_copy["details"] = f"{details} (increased severity)"
                            evolved_scenarios.append(scenario_copy)
                        elif feedback_result == "failure":
                            # If failure, try a different type of chaos
                            details = scenario_copy.get("details", "")
                            scenario_copy["details"] = f"{details} (try alternative failure mode)"
                            evolved_scenarios.append(scenario_copy)
                        else:
                            evolved_scenarios.append(scenario_copy)
                            
                    except Exception as e:
                        logger.warning(f"Error evolving scenario {scenario}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error evolving scenarios: {e}")
                evolved_scenarios = scenarios.copy() if scenarios else self.default_scenarios.copy()
            
            # Optionally add a new scenario if feedback suggests
            try:
                if feedback.get("add_network_partition"):
                    evolved_scenarios.append({
                        "name": "Network partition",
                        "details": "Simulate network issues as suggested by feedback"
                    })
                
                if feedback.get("add_cpu_spike"):
                    evolved_scenarios.append({
                        "name": "CPU spike",
                        "details": "Simulate CPU spike as suggested by feedback"
                    })
                    
            except Exception as e:
                logger.warning(f"Error adding feedback-suggested scenarios: {e}")
            
            # Ensure we don't exceed max scenarios
            if len(evolved_scenarios) > self.max_scenarios:
                logger.warning(f"Evolved scenarios exceed limit, truncating to {self.max_scenarios}")
                evolved_scenarios = evolved_scenarios[:self.max_scenarios]
            
            # If no scenarios evolved, return originals or defaults
            if not evolved_scenarios:
                logger.info("No scenarios evolved, returning original scenarios")
                evolved_scenarios = scenarios if scenarios else self.default_scenarios.copy()
            
            logger.info(f"Evolved {len(evolved_scenarios)} chaos scenarios")
            return evolved_scenarios
            
        except Exception as e:
            logger.error(f"Critical error in scenario evolution: {e}")
            return scenarios if scenarios else self.default_scenarios.copy()