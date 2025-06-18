import re
import json
from datetime import datetime
from collections import Counter, defaultdict
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple

class NLPLogAnalyzer:
    """Advanced NLP-based log analyzer for chaos engineering insights"""
    
    def __init__(self):
        self.failure_patterns = [
            # Common failure patterns
            r'(?i)(error|exception|failure|fault|crash)',
            r'(?i)(timeout|connection\s+refused|connection\s+reset)',
            r'(?i)(out\s+of\s+memory|memory\s+leak|heap\s+space)',
            r'(?i)(cpu\s+spike|high\s+cpu|cpu\s+usage)',
            r'(?i)(disk\s+full|no\s+space|storage\s+full)',
            r'(?i)(network\s+partition|network\s+failure|packet\s+loss)',
            r'(?i)(database\s+error|sql\s+error|connection\s+pool)',
            r'(?i)(service\s+unavailable|502|503|504)',
        ]
        
        self.severity_keywords = {
            'critical': ['fatal', 'critical', 'emergency', 'panic', 'crash'],
            'high': ['error', 'exception', 'failure', 'timeout', 'refuse'],
            'medium': ['warning', 'warn', 'deprecated', 'slow', 'retry'],
            'low': ['info', 'debug', 'trace', 'notice']
        }
        
        self.service_patterns = [
            r'service[:\-\s]+([a-zA-Z0-9\-_]+)',
            r'component[:\-\s]+([a-zA-Z0-9\-_]+)',
            r'module[:\-\s]+([a-zA-Z0-9\-_]+)',
        ]

    def analyze_logs(self, logs: str) -> Dict[str, Any]:
        """
        Analyzes the provided logs to extract relevant information for failure pattern identification.
        
        Args:
            logs (str): The logs to analyze.
        
        Returns:
            dict: A dictionary containing analyzed log information.
        """
        if not logs or not isinstance(logs, str):
            return {'error': 'Invalid logs provided'}
        
        log_lines = logs.strip().split('\n')
        
        analysis = {
            'total_lines': len(log_lines),
            'timestamp_range': self._extract_timestamp_range(log_lines),
            'severity_distribution': self._analyze_severity(log_lines),
            'failure_indicators': self._detect_failures(log_lines),
            'affected_services': self._extract_services(log_lines),
            'error_frequency': self._calculate_error_frequency(log_lines),
            'anomaly_score': self._calculate_anomaly_score(log_lines),
            'recommendations': []
        }
        
        # Generate recommendations based on analysis
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis

    def extract_failure_patterns(self, analyzed_logs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts failure patterns from the analyzed logs.
        
        Args:
            analyzed_logs (dict): The analyzed log information.
        
        Returns:
            list: A list of identified failure patterns.
        """
        patterns = []
        
        failure_indicators = analyzed_logs.get('failure_indicators', {})
        severity_dist = analyzed_logs.get('severity_distribution', {})
        affected_services = analyzed_logs.get('affected_services', [])
        
        # Pattern 1: High error rate
        total_errors = severity_dist.get('critical', 0) + severity_dist.get('high', 0)
        total_lines = analyzed_logs.get('total_lines', 1)
        error_rate = total_errors / total_lines if total_lines > 0 else 0
        
        if error_rate > 0.1:  # More than 10% errors
            patterns.append({
                'type': 'high_error_rate',
                'description': f'High error rate detected: {error_rate:.2%}',
                'severity': 'high' if error_rate > 0.3 else 'medium',
                'confidence': min(error_rate * 2, 1.0),
                'recommended_chaos_scenarios': ['api_timeout', 'service_discovery_failure']
            })
        
        # Pattern 2: Resource exhaustion
        for failure_type, count in failure_indicators.items():
            if count > 0:
                if 'memory' in failure_type:
                    patterns.append({
                        'type': 'memory_exhaustion',
                        'description': f'Memory issues detected ({count} occurrences)',
                        'severity': 'high',
                        'confidence': min(count / 10, 1.0),
                        'recommended_chaos_scenarios': ['memory_leak']
                    })
                elif 'cpu' in failure_type:
                    patterns.append({
                        'type': 'cpu_exhaustion',
                        'description': f'CPU issues detected ({count} occurrences)',
                        'severity': 'high',
                        'confidence': min(count / 10, 1.0),
                        'recommended_chaos_scenarios': ['cpu_spike']
                    })
                elif 'network' in failure_type:
                    patterns.append({
                        'type': 'network_issues',
                        'description': f'Network problems detected ({count} occurrences)',
                        'severity': 'medium',
                        'confidence': min(count / 5, 1.0),
                        'recommended_chaos_scenarios': ['network_latency', 'network_partition']
                    })
        
        # Pattern 3: Service-specific failures
        if affected_services:
            for service in affected_services[:3]:  # Top 3 affected services
                patterns.append({
                    'type': 'service_specific_failure',
                    'description': f'Service "{service}" showing issues',
                    'severity': 'medium',
                    'confidence': 0.7,
                    'recommended_chaos_scenarios': ['container_restart', 'process_kill']
                })
        
        return patterns

    def predict_failure_likelihood(self, current_metrics: Dict[str, float], 
                                 historical_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Predict likelihood of failures based on current metrics and historical patterns.
        
        Args:
            current_metrics: Current system metrics
            historical_patterns: Historical failure patterns
            
        Returns:
            dict: Prediction results with probabilities and recommendations
        """
        prediction = {
            'overall_risk': 'low',
            'risk_score': 0.0,
            'specific_risks': {},
            'recommended_preventive_chaos': []
        }
        
        # Analyze current metrics
        cpu_risk = self._assess_cpu_risk(current_metrics.get('cpu_percent', 0))
        memory_risk = self._assess_memory_risk(current_metrics.get('memory_percent', 0))
        disk_risk = self._assess_disk_risk(current_metrics.get('disk_percent', 0))
        
        risks = {
            'cpu_failure': cpu_risk,
            'memory_failure': memory_risk,
            'disk_failure': disk_risk
        }
        
        # Calculate overall risk
        overall_risk_score = max(risks.values())
        prediction['risk_score'] = overall_risk_score
        prediction['specific_risks'] = risks
        
        if overall_risk_score > 0.7:
            prediction['overall_risk'] = 'high'
        elif overall_risk_score > 0.4:
            prediction['overall_risk'] = 'medium'
        else:
            prediction['overall_risk'] = 'low'
        
        # Recommend preventive chaos scenarios
        if cpu_risk > 0.5:
            prediction['recommended_preventive_chaos'].append('cpu_spike')
        if memory_risk > 0.5:
            prediction['recommended_preventive_chaos'].append('memory_leak')
        if disk_risk > 0.5:
            prediction['recommended_preventive_chaos'].append('disk_fill')
        
        return prediction

    def _extract_timestamp_range(self, log_lines: List[str]) -> Dict[str, str]:
        """Extract timestamp range from logs"""
        timestamps = []
        for line in log_lines[:10] + log_lines[-10:]:  # Check first and last 10 lines
            # Common timestamp patterns
            timestamp_patterns = [
                r'\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}',
                r'\d{2}/\d{2}/\d{4}\s\d{2}:\d{2}:\d{2}',
                r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}'
            ]
            
            for pattern in timestamp_patterns:
                match = re.search(pattern, line)
                if match:
                    timestamps.append(match.group())
                    break
        
        if timestamps:
            return {'start': timestamps[0], 'end': timestamps[-1]}
        return {'start': 'unknown', 'end': 'unknown'}

    def _analyze_severity(self, log_lines: List[str]) -> Dict[str, int]:
        """Analyze severity distribution in logs"""
        severity_counts = defaultdict(int)
        
        for line in log_lines:
            line_lower = line.lower()
            for severity, keywords in self.severity_keywords.items():
                if any(keyword in line_lower for keyword in keywords):
                    severity_counts[severity] += 1
                    break
        
        return dict(severity_counts)

    def _detect_failures(self, log_lines: List[str]) -> Dict[str, int]:
        """Detect various failure types in logs"""
        failure_counts = defaultdict(int)
        
        for line in log_lines:
            for pattern in self.failure_patterns:
                if re.search(pattern, line):
                    # Categorize the failure type
                    if re.search(r'(?i)(memory|heap)', line):
                        failure_counts['memory_issues'] += 1
                    elif re.search(r'(?i)(cpu|processor)', line):
                        failure_counts['cpu_issues'] += 1
                    elif re.search(r'(?i)(network|connection)', line):
                        failure_counts['network_issues'] += 1
                    elif re.search(r'(?i)(disk|storage)', line):
                        failure_counts['storage_issues'] += 1
                    else:
                        failure_counts['general_errors'] += 1
        
        return dict(failure_counts)

    def _extract_services(self, log_lines: List[str]) -> List[str]:
        """Extract affected services from logs"""
        services = set()
        
        for line in log_lines:
            for pattern in self.service_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                services.update(matches)
        
        # Return most frequently mentioned services
        service_counts = Counter()
        for line in log_lines:
            for service in services:
                if service.lower() in line.lower():
                    service_counts[service] += 1
        
        return [service for service, count in service_counts.most_common(10)]

    def _calculate_error_frequency(self, log_lines: List[str]) -> float:
        """Calculate error frequency per minute"""
        error_count = sum(1 for line in log_lines 
                         if any(re.search(pattern, line) for pattern in self.failure_patterns))
        
        # Assume logs span approximately the number of lines / 60 minutes
        estimated_minutes = max(len(log_lines) / 60, 1)
        return error_count / estimated_minutes

    def _calculate_anomaly_score(self, log_lines: List[str]) -> float:
        """Calculate anomaly score based on various factors"""
        factors = []
        
        # Factor 1: Error density
        error_density = sum(1 for line in log_lines 
                           if any(re.search(pattern, line) for pattern in self.failure_patterns)) / len(log_lines)
        factors.append(error_density)
        
        # Factor 2: Critical error presence
        critical_errors = sum(1 for line in log_lines 
                             if any(keyword in line.lower() for keyword in self.severity_keywords['critical']))
        critical_factor = min(critical_errors / 10, 1.0)
        factors.append(critical_factor)
        
        # Factor 3: Pattern diversity
        unique_patterns = len(set(pattern for line in log_lines 
                                for pattern in self.failure_patterns 
                                if re.search(pattern, line)))
        pattern_factor = min(unique_patterns / len(self.failure_patterns), 1.0)
        factors.append(pattern_factor)
        
        return np.mean(factors)

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on log analysis"""
        recommendations = []
        
        anomaly_score = analysis.get('anomaly_score', 0)
        failure_indicators = analysis.get('failure_indicators', {})
        
        if anomaly_score > 0.7:
            recommendations.append("High anomaly score detected - immediate investigation recommended")
        
        if failure_indicators.get('memory_issues', 0) > 5:
            recommendations.append("Consider running memory_leak chaos scenarios to test resilience")
        
        if failure_indicators.get('network_issues', 0) > 3:
            recommendations.append("Network issues detected - test with network_partition scenarios")
        
        if failure_indicators.get('cpu_issues', 0) > 3:
            recommendations.append("CPU performance issues - consider cpu_spike chaos testing")
        
        if not recommendations:
            recommendations.append("System appears stable - good time for preventive chaos testing")
        
        return recommendations

    def _assess_cpu_risk(self, cpu_percent: float) -> float:
        """Assess CPU failure risk based on current usage"""
        if cpu_percent > 90:
            return 0.9
        elif cpu_percent > 80:
            return 0.7
        elif cpu_percent > 70:
            return 0.5
        elif cpu_percent > 60:
            return 0.3
        else:
            return 0.1

    def _assess_memory_risk(self, memory_percent: float) -> float:
        """Assess memory failure risk based on current usage"""
        if memory_percent > 95:
            return 0.95
        elif memory_percent > 85:
            return 0.8
        elif memory_percent > 75:
            return 0.6
        elif memory_percent > 65:
            return 0.4
        else:
            return 0.1

    def _assess_disk_risk(self, disk_percent: float) -> float:
        """Assess disk failure risk based on current usage"""
        if disk_percent > 95:
            return 0.9
        elif disk_percent > 90:
            return 0.7
        elif disk_percent > 80:
            return 0.5
        elif disk_percent > 70:
            return 0.3
        else:
            return 0.1