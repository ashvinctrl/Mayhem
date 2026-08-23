import logging
from collections import Counter
from typing import Any, Dict, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Maps failure text keywords → canonical scenario IDs (matching the injector's known scenarios)
_KEYWORD_TO_SCENARIO = {
    "cpu": "cpu_spike",
    "processor": "cpu_spike",
    "memory": "memory_leak",
    "heap": "memory_leak",
    "oom": "memory_leak",
    "disk": "disk_fill",
    "storage": "disk_fill",
    "no space": "disk_fill",
    "network": "network_latency",
    "latency": "network_latency",
    "partition": "network_partition",
    "split brain": "network_partition",
    "database": "database_slowdown",
    "db": "database_slowdown",
    "sql": "database_slowdown",
    "timeout": "api_timeout",
    "api": "api_timeout",
    "process": "process_kill",
    "crash": "process_kill",
    "dns": "dns_failure",
    "ssl": "ssl_certificate_expired",
    "certificate": "ssl_certificate_expired",
    "kubernetes": "kubernetes_pod_eviction",
    "k8s": "kubernetes_pod_eviction",
    "pod": "kubernetes_pod_eviction",
    "service discovery": "service_discovery_failure",
    "consul": "service_discovery_failure",
    "load balancer": "load_balancer_failure",
    "lb": "load_balancer_failure",
}

_SCENARIO_LABELS = {
    "cpu_spike": "CPU Spike",
    "memory_leak": "Memory Leak",
    "disk_fill": "Disk Fill",
    "network_latency": "Network Latency",
    "network_partition": "Network Partition",
    "database_slowdown": "Database Slowdown",
    "api_timeout": "API Timeout",
    "process_kill": "Process Kill",
    "dns_failure": "DNS Failure",
    "ssl_certificate_expired": "SSL Certificate Expiry",
    "kubernetes_pod_eviction": "Kubernetes Pod Eviction",
    "service_discovery_failure": "Service Discovery Failure",
    "load_balancer_failure": "Load Balancer Failure",
    "container_restart": "Container Restart",
    "storage_corruption": "Storage Corruption",
}


def _classify_failure(text: str) -> str:
    """Return the canonical scenario ID that best matches failure text."""
    lower = text.lower()
    for keyword, scenario_id in _KEYWORD_TO_SCENARIO.items():
        if keyword in lower:
            return scenario_id
    return "cpu_spike"  # safe default


def _metric_score(system_metrics: Dict[str, Any]) -> Dict[str, float]:
    """Return a 0-1 urgency score per scenario based on live system metrics."""
    cpu = float(system_metrics.get("cpu", system_metrics.get("cpu_percent", 0)))
    mem = float(system_metrics.get("memory", system_metrics.get("memory_percent", 0)))
    disk = float(system_metrics.get("disk", system_metrics.get("disk_percent", 0)))

    def _normalize(value, warn=70, crit=90):
        if value >= crit:
            return 1.0
        if value >= warn:
            return 0.5 + 0.5 * (value - warn) / (crit - warn)
        return value / (warn * 2)

    return {
        "cpu_spike": _normalize(cpu),
        "memory_leak": _normalize(mem, warn=75, crit=90),
        "disk_fill": _normalize(disk, warn=80, crit=95),
    }


def _suggest_intensity(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


class ScenarioGenerator:
    """Chaos scenario generator — ranks scenarios by failure frequency and live metric urgency."""

    def __init__(self):
        self.max_scenarios = 50
        self.default_scenarios = [
            {
                "scenario_id": "cpu_spike",
                "name": "CPU Spike",
                "details": "Basic CPU stress test",
                "priority_score": 0.3,
                "suggested_intensity": "medium",
            },
            {
                "scenario_id": "memory_leak",
                "name": "Memory Leak",
                "details": "Basic memory stress test",
                "priority_score": 0.3,
                "suggested_intensity": "medium",
            },
            {
                "scenario_id": "network_latency",
                "name": "Network Latency",
                "details": "Basic network degradation test",
                "priority_score": 0.3,
                "suggested_intensity": "medium",
            },
        ]
        logger.info("ScenarioGenerator initialized")

    def generate_scenarios(
        self,
        past_failures: Optional[List[Union[str, Dict]]] = None,
        system_metrics: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate and rank chaos scenarios from past failures and live system metrics.

        Each returned item includes:
          scenario_id        — matches the /inject API's "scenario" field
          name               — human-readable label
          details            — why this scenario was selected
          priority_score     — 0.0–1.0 (higher = more urgent)
          suggested_intensity — low / medium / high
        """
        try:
            if not isinstance(past_failures, list):
                past_failures = []
            if not isinstance(system_metrics, dict):
                system_metrics = {}

            # ── 1. Count scenario frequency from past failures ────────────────
            frequency: Counter = Counter()
            for failure in past_failures[:20]:
                try:
                    if isinstance(failure, str):
                        text = failure
                    elif isinstance(failure, dict):
                        text = failure.get(
                            "description", failure.get("message", str(failure))
                        )
                    else:
                        continue
                    frequency[_classify_failure(text)] += 1
                except Exception as e:
                    logger.warning(f"Error processing failure entry: {e}")

            # ── 2. Urgency scores from live metrics ───────────────────────────
            metric_scores = _metric_score(system_metrics)

            # ── 3. Build scored candidate set ─────────────────────────────────
            # Start with every scenario that appeared in failures
            candidates: Dict[str, float] = {}
            total_failures = sum(frequency.values()) or 1
            for scenario_id, count in frequency.items():
                freq_score = min(1.0, count / total_failures * 2)  # normalise, cap at 1
                candidates[scenario_id] = freq_score

            # Boost or add scenarios that have elevated live metrics
            for scenario_id, mscore in metric_scores.items():
                if mscore > 0.1:  # only if metric is meaningfully elevated
                    candidates[scenario_id] = max(
                        candidates.get(scenario_id, 0.0), mscore
                    )

            # If nothing was generated, emit the three defaults at low priority
            if not candidates:
                logger.info(
                    "No signals from failures or metrics — returning default scenarios"
                )
                return self.default_scenarios.copy()

            # ── 4. Build output list sorted by score descending ───────────────
            results: List[Dict[str, Any]] = []
            for scenario_id, score in sorted(
                candidates.items(), key=lambda x: x[1], reverse=True
            ):
                label = _SCENARIO_LABELS.get(
                    scenario_id, scenario_id.replace("_", " ").title()
                )
                details_parts = []
                if frequency.get(scenario_id):
                    details_parts.append(
                        f"seen {frequency[scenario_id]}x in past failures"
                    )
                if scenario_id in metric_scores and metric_scores[scenario_id] > 0.1:
                    details_parts.append(
                        f"live metric score {metric_scores[scenario_id]:.0%}"
                    )
                results.append(
                    {
                        "scenario_id": scenario_id,
                        "name": label,
                        "details": (
                            "; ".join(details_parts)
                            if details_parts
                            else f"Simulate {label}"
                        ),
                        "priority_score": round(score, 3),
                        "suggested_intensity": _suggest_intensity(score),
                    }
                )

            results = results[: self.max_scenarios]
            logger.info(f"Generated {len(results)} ranked chaos scenarios")
            return results

        except Exception as e:
            logger.error(f"Critical error in scenario generation: {e}")
            return self.default_scenarios.copy()

    def evolve_scenarios(
        self,
        scenarios: Optional[List[Dict[str, Any]]] = None,
        feedback: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evolve existing scenarios using experiment feedback.

        feedback keys:
          result          — "success" | "failure"
          impact_score    — float 0-10 from the experiment's recorded impact
          add_<scenario_id> — True to inject an additional scenario
        """
        try:
            if not isinstance(scenarios, list):
                scenarios = self.default_scenarios.copy()
            if not isinstance(feedback, dict):
                feedback = {}

            feedback_result = feedback.get("result", "unknown")
            impact_score = float(feedback.get("impact_score", 5.0))
            # Normalise impact to 0-1
            impact_norm = min(1.0, impact_score / 10.0)

            evolved: List[Dict[str, Any]] = []
            for scenario in scenarios[: self.max_scenarios]:
                try:
                    if not isinstance(scenario, dict) or "name" not in scenario:
                        continue
                    s = scenario.copy()
                    current_score = float(s.get("priority_score", 0.3))

                    if feedback_result == "success":
                        # Experiment exposed a weakness — raise priority and push intensity up
                        s["priority_score"] = round(
                            min(1.0, current_score + impact_norm * 0.2), 3
                        )
                        s["suggested_intensity"] = _suggest_intensity(
                            s["priority_score"]
                        )
                        s["details"] = (
                            s.get("details", "")
                            + " [priority raised after successful chaos]"
                        )
                    elif feedback_result == "failure":
                        # Experiment had no effect — lower priority, suggest alternative intensity
                        s["priority_score"] = round(max(0.0, current_score - 0.1), 3)
                        s["details"] = (
                            s.get("details", "")
                            + " [deprioritised — previous run had no impact]"
                        )
                    evolved.append(s)
                except Exception as e:
                    logger.warning(f"Error evolving scenario: {e}")

            # Inject any feedback-requested extra scenarios
            for key, value in feedback.items():
                if key.startswith("add_") and value:
                    scenario_id = key[4:]
                    label = _SCENARIO_LABELS.get(
                        scenario_id, scenario_id.replace("_", " ").title()
                    )
                    evolved.append(
                        {
                            "scenario_id": scenario_id,
                            "name": label,
                            "details": "Added via feedback request",
                            "priority_score": 0.5,
                            "suggested_intensity": "medium",
                        }
                    )

            evolved = evolved[: self.max_scenarios]
            # Re-sort by priority after mutations
            evolved.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

            if not evolved:
                return scenarios if scenarios else self.default_scenarios.copy()

            logger.info(f"Evolved {len(evolved)} chaos scenarios")
            return evolved

        except Exception as e:
            logger.error(f"Critical error in scenario evolution: {e}")
            return scenarios if scenarios else self.default_scenarios.copy()
