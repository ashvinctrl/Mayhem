import logging
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RemediationAgent:
    """Automated remediation agent with comprehensive error handling"""
    
    def __init__(self):
        """Initialize the remediation agent"""
        self.current_state = "unknown"
        self.remediation_history = []
        self.max_history = 100  # Limit history to prevent memory bloat
        self.supported_events = {
            'cpu_spike', 'memory_leak', 'network_partition', 'disk_full',
            'process_crash', 'database_error', 'api_timeout'
        }
        logger.info("RemediationAgent initialized")
    
    def assess_impact(self, chaos_event: Optional[Union[Dict[str, Any], str]] = None) -> Dict[str, Any]:
        """
        Evaluate the impact of the chaos event on the system.
        
        Parameters:
        chaos_event (dict or str): Information about the chaos event to assess.
        
        Returns:
        dict: Assessment result indicating the severity and affected components.
        """
        try:
            # Input validation
            if chaos_event is None:
                logger.warning("No chaos event provided for assessment")
                return {
                    "severity": "unknown",
                    "affected_services": [],
                    "error": "No event data provided"
                }
            
            # Handle string input
            if isinstance(chaos_event, str):
                chaos_event = {"event": chaos_event, "description": chaos_event}
            
            # Validate dict input
            if not isinstance(chaos_event, dict):
                logger.error(f"Invalid chaos_event type: {type(chaos_event)}")
                return {
                    "severity": "unknown",
                    "affected_services": [],
                    "error": "Invalid event data type"
                }
            
            # Extract event information
            event_type = chaos_event.get("event", chaos_event.get("type", "unknown"))
            event_description = chaos_event.get("description", str(chaos_event))
            event_intensity = chaos_event.get("intensity", "medium")
            event_duration = chaos_event.get("duration", 0)
            
            # Assess severity based on event type and characteristics
            try:
                severity = self._calculate_severity(event_type, event_intensity, event_duration)
                affected_services = self._identify_affected_services(event_type, chaos_event)
                confidence = self._calculate_confidence(event_type, chaos_event)
                
                assessment = {
                    "severity": severity,
                    "affected_services": affected_services,
                    "event_type": event_type,
                    "confidence": confidence,
                    "assessment_time": datetime.utcnow().isoformat(),
                    "recommendations": self._generate_recommendations(event_type, severity)
                }
                
                logger.info(f"Impact assessment completed: {severity} severity for {event_type}")
                return assessment
                
            except Exception as e:
                logger.error(f"Error calculating impact assessment: {e}")
                return {
                    "severity": "medium",  # Default to medium severity
                    "affected_services": ["unknown"],
                    "event_type": event_type,
                    "confidence": 0.3,
                    "error": f"Assessment calculation failed: {str(e)}"
                }
            
        except Exception as e:
            logger.error(f"Critical error in impact assessment: {e}")
            return {
                "severity": "unknown",
                "affected_services": [],
                "error": f"Critical assessment failure: {str(e)}"
            }
    
    def execute_remediation(self, assessment_result: Optional[Union[str, Dict[str, Any]]] = None) -> bool:
        """
        Apply remediation strategies based on the assessment result.
        
        Parameters:
        assessment_result (str or dict): The result of the impact assessment.
        
        Returns:
        bool: True if remediation was successful, False otherwise.
        """
        try:
            # Input validation
            if assessment_result is None:
                logger.warning("No assessment result provided for remediation")
                return False
            
            # Handle string input
            if isinstance(assessment_result, str):
                assessment_result = {"strategy": assessment_result}
            
            # Validate dict input
            if not isinstance(assessment_result, dict):
                logger.error(f"Invalid assessment_result type: {type(assessment_result)}")
                return False
            
            # Extract remediation strategy
            strategy = assessment_result.get("strategy", "default")
            severity = assessment_result.get("severity", "medium")
            event_type = assessment_result.get("event_type", "unknown")
            
            remediation_start = time.time()
            success = False
            
            try:
                # Execute appropriate remediation strategy
                if strategy == "remediate_network_failure" or event_type == "network_partition":
                    success = self._remediate_network_issues(assessment_result)
                elif strategy == "remediate_cpu_spike" or event_type == "cpu_spike":
                    success = self._remediate_cpu_issues(assessment_result)
                elif strategy == "remediate_memory_leak" or event_type == "memory_leak":
                    success = self._remediate_memory_issues(assessment_result)
                elif strategy == "remediate_disk_full" or event_type == "disk_full":
                    success = self._remediate_disk_issues(assessment_result)
                else:
                    success = self._generic_remediation(assessment_result)
                
                # Update system state based on remediation success
                if success:
                    self.current_state = "healthy"
                    logger.info(f"Remediation successful for {event_type}")
                else:
                    self.current_state = "degraded"
                    logger.warning(f"Remediation failed for {event_type}")
                
                # Record remediation attempt
                remediation_duration = time.time() - remediation_start
                self._record_remediation(strategy, event_type, success, remediation_duration)
                
                return success
                
            except Exception as e:
                logger.error(f"Error executing remediation strategy {strategy}: {e}")
                self.current_state = "error"
                self._record_remediation(strategy, event_type, False, time.time() - remediation_start, str(e))
                return False
            
        except Exception as e:
            logger.error(f"Critical error in remediation execution: {e}")
            self.current_state = "error"
            return False
    
    def _calculate_severity(self, event_type: str, intensity: str, duration: int) -> str:
        """Calculate severity based on event characteristics"""
        try:
            base_severity = {
                "cpu_spike": "medium",
                "memory_leak": "high",
                "network_partition": "high",
                "disk_full": "high",
                "process_crash": "medium",
                "database_error": "high",
                "api_timeout": "medium"
            }.get(event_type.lower(), "medium")
            
            # Adjust based on intensity
            intensity_multiplier = {
                "low": 0.5,
                "medium": 1.0,
                "high": 1.5,
                "critical": 2.0
            }.get(intensity.lower(), 1.0)
            
            # Adjust based on duration
            duration_multiplier = 1.0
            if duration > 300:  # 5 minutes
                duration_multiplier = 1.5
            elif duration > 600:  # 10 minutes
                duration_multiplier = 2.0
            
            severity_score = intensity_multiplier * duration_multiplier
            
            if severity_score >= 2.0:
                return "critical"
            elif severity_score >= 1.5:
                return "high"
            elif severity_score >= 1.0:
                return "medium"
            else:
                return "low"
                
        except Exception as e:
            logger.warning(f"Error calculating severity: {e}")
            return "medium"
    
    def _identify_affected_services(self, event_type: str, event_data: Dict[str, Any]) -> List[str]:
        """Identify services potentially affected by the event"""
        try:
            # Extract explicit service list if provided
            if "affected_services" in event_data:
                services = event_data["affected_services"]
                if isinstance(services, list):
                    return services[:10]  # Limit to 10 services
            
            # Predict affected services based on event type
            service_mapping = {
                "cpu_spike": ["api-server", "worker-processes", "background-jobs"],
                "memory_leak": ["application-services", "cache-layer", "database"],
                "network_partition": ["all-services", "load-balancer", "service-mesh"],
                "disk_full": ["logging-service", "database", "file-storage"],
                "database_error": ["api-server", "data-layer", "reporting"],
                "api_timeout": ["frontend", "gateway", "external-integrations"]
            }
            
            return service_mapping.get(event_type.lower(), ["unknown-service"])
            
        except Exception as e:
            logger.warning(f"Error identifying affected services: {e}")
            return ["unknown-service"]
    
    def _calculate_confidence(self, event_type: str, event_data: Dict[str, Any]) -> float:
        """Calculate confidence level in the assessment"""
        try:
            base_confidence = 0.7  # 70% default confidence
            
            # Higher confidence for known event types
            if event_type.lower() in self.supported_events:
                base_confidence = 0.8
            
            # Adjust based on data completeness
            data_completeness = 0
            expected_fields = ["intensity", "duration", "description"]
            for field in expected_fields:
                if field in event_data and event_data[field]:
                    data_completeness += 1
            
            completeness_bonus = (data_completeness / len(expected_fields)) * 0.2
            
            return min(base_confidence + completeness_bonus, 1.0)
            
        except Exception as e:
            logger.warning(f"Error calculating confidence: {e}")
            return 0.5
    
    def _generate_recommendations(self, event_type: str, severity: str) -> List[str]:
        """Generate remediation recommendations"""
        try:
            recommendations = []
            
            if event_type == "cpu_spike":
                recommendations = [
                    "Scale out application instances",
                    "Optimize CPU-intensive processes",
                    "Implement CPU throttling"
                ]
            elif event_type == "memory_leak":
                recommendations = [
                    "Restart affected services",
                    "Implement memory monitoring",
                    "Review application code for memory leaks"
                ]
            elif event_type == "network_partition":
                recommendations = [
                    "Check network connectivity",
                    "Verify load balancer configuration",
                    "Implement circuit breaker pattern"
                ]
            else:
                recommendations = [
                    "Monitor system metrics",
                    "Review application logs",
                    "Implement health checks"
                ]
            
            # Add severity-specific recommendations
            if severity in ["high", "critical"]:
                recommendations.append("Consider triggering incident response")
                recommendations.append("Notify on-call team")
            
            return recommendations
            
        except Exception as e:
            logger.warning(f"Error generating recommendations: {e}")
            return ["Review system status manually"]
    
    def _remediate_network_issues(self, assessment: Dict[str, Any]) -> bool:
        """Remediate network-related issues"""
        try:
            logger.info("Executing network remediation strategy")
            # Simulate network remediation steps
            time.sleep(0.1)  # Simulate work
            return True
        except Exception as e:
            logger.error(f"Network remediation failed: {e}")
            return False
    
    def _remediate_cpu_issues(self, assessment: Dict[str, Any]) -> bool:
        """Remediate CPU-related issues"""
        try:
            logger.info("Executing CPU remediation strategy")
            # Simulate CPU remediation steps
            time.sleep(0.1)  # Simulate work
            return True
        except Exception as e:
            logger.error(f"CPU remediation failed: {e}")
            return False
    
    def _remediate_memory_issues(self, assessment: Dict[str, Any]) -> bool:
        """Remediate memory-related issues"""
        try:
            logger.info("Executing memory remediation strategy")
            # Simulate memory remediation steps
            time.sleep(0.1)  # Simulate work
            return True
        except Exception as e:
            logger.error(f"Memory remediation failed: {e}")
            return False
    
    def _remediate_disk_issues(self, assessment: Dict[str, Any]) -> bool:
        """Remediate disk-related issues"""
        try:
            logger.info("Executing disk remediation strategy")
            # Simulate disk remediation steps
            time.sleep(0.1)  # Simulate work
            return True
        except Exception as e:
            logger.error(f"Disk remediation failed: {e}")
            return False
    
    def _generic_remediation(self, assessment: Dict[str, Any]) -> bool:
        """Generic remediation for unknown issues"""
        try:
            logger.info("Executing generic remediation strategy")
            # Simulate generic remediation steps
            time.sleep(0.1)  # Simulate work
            return True
        except Exception as e:
            logger.error(f"Generic remediation failed: {e}")
            return False
    
    def _record_remediation(self, strategy: str, event_type: str, success: bool, 
                          duration: float, error: Optional[str] = None):
        """Record remediation attempt in history"""
        try:
            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "strategy": strategy,
                "event_type": event_type,
                "success": success,
                "duration": duration,
                "error": error
            }
            
            self.remediation_history.append(record)
            
            # Limit history size
            if len(self.remediation_history) > self.max_history:
                self.remediation_history = self.remediation_history[-self.max_history:]
                
        except Exception as e:
            logger.warning(f"Failed to record remediation history: {e}")
    
    def get_remediation_status(self) -> Dict[str, Any]:
        """Get current remediation agent status"""
        try:
            return {
                "current_state": self.current_state,
                "history_count": len(self.remediation_history),
                "recent_remediations": self.remediation_history[-5:] if self.remediation_history else [],
                "supported_events": list(self.supported_events)
            }
        except Exception as e:
            logger.error(f"Error getting remediation status: {e}")
            return {"error": str(e)}