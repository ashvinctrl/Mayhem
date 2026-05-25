# Mayhem — AI-Driven Chaos Engineering Platform

[![CI/CD Pipeline](https://github.com/ashvinctrl/Mayhem/workflows/Project%20Mayhem%20CI%2FCD/badge.svg)](https://github.com/ashvinctrl/Mayhem/actions)
[![Security Score](https://img.shields.io/badge/security-A+-green.svg)](https://github.com/ashvinctrl/Mayhem/security)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

Mayhem is a chaos engineering platform that systematically injects faults into your systems to identify weaknesses before they cause production outages. It uses an AI-powered NLP engine to analyze logs, detect failure patterns, and recommend targeted chaos scenarios.

## Key Features

**AI-Generated Chaos Scenarios**
The NLP engine analyzes postmortems and system logs to identify failure patterns and generate targeted chaos scenarios, learning from each experiment.

**Adaptive Fault Injection**
Supports 15+ realistic failure scenarios including network partitions, CPU spikes, memory pressure, disk saturation, latency injection, and Kubernetes-level events.

**Production-Ready Security**
- API key authentication with rate limiting
- Secure secrets management
- Input validation and sanitization
- Non-root Docker containers
- RBAC-enabled Kubernetes deployment

**Real-Time Monitoring**
- Prometheus metrics integration
- Grafana dashboards with 15+ visualizations
- System health monitoring
- Chaos experiment history and analytics

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.9+, Flask, SQLAlchemy |
| Frontend | HTML5/CSS3/JavaScript, Bootstrap 5 |
| Containerization | Docker (multi-stage builds) |
| Orchestration | Kubernetes with RBAC |
| Monitoring | Prometheus, Grafana |
| Database | SQLite (dev) / PostgreSQL (prod) |
| CI/CD | GitHub Actions |

## Prerequisites

- Docker 20.0+ and Docker Compose 2.0+
- Kubernetes 1.21+ (production deployment only)
- Python 3.9+ (local development)

## Quick Start

### 1. Clone

```bash
git clone https://github.com/ashvinctrl/Mayhem.git
cd Mayhem
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set CHAOS_API_KEY, SECRET_KEY, GRAFANA_PASSWORD
```

### 3. Start with Docker Compose

```bash
docker-compose up --build -d
docker-compose logs -f chaos-orchestrator
```

### 4. Access

| Service | URL | Credentials |
|---|---|---|
| Platform UI | http://localhost:5000 | API key from .env |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / GRAFANA_PASSWORD |

### 5. Inject your first chaos experiment

Via the UI: open http://localhost:5000, go to **Chaos Scenarios**, enter your API key, select a scenario and click Execute.

Via API:
```bash
curl -X POST http://localhost:5000/inject \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"scenario": "cpu_spike", "duration": 30, "intensity": "medium"}'
```

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | /health | No | Health check |
| GET | /scenarios | No | List available scenarios |
| GET | /metrics | No | Prometheus metrics |
| GET | /system-status | No | Real-time system metrics |
| GET | /chaos-history | No | Experiment history (last 20) |
| POST | /inject | Yes (API key) | Inject a chaos scenario |
| POST | /analyze-logs | No | NLP log analysis |

### Inject payload

```json
{
  "scenario": "cpu_spike",
  "duration": 30,
  "intensity": "medium"
}
```

**Valid scenarios**: `cpu_spike`, `memory_leak`, `disk_fill`, `network_latency`, `network_partition`, `process_kill`, `container_restart`, `database_slowdown`, `api_timeout`, `ssl_certificate_expired`, `dns_failure`, `storage_corruption`, `kubernetes_pod_eviction`, `service_discovery_failure`, `load_balancer_failure`

**Intensity**: `low`, `medium`, `high`

**Duration**: 1–300 seconds

### Analyze logs payload

```bash
curl -X POST http://localhost:5000/analyze-logs \
  -H "Content-Type: application/json" \
  -d '{"logs": "2024-01-01 ERROR connection timeout\n2024-01-01 WARN memory high"}'
```

## Production Deployment

```bash
# Deploy to Kubernetes
./scripts/deploy_production.sh

# Or manually
kubectl apply -f configs/kubernetes_deployment_production.yaml
kubectl get pods -n chaos-engineering
```

Generate a secure API key:
```bash
export CHAOS_API_KEY=$(openssl rand -hex 32)
kubectl create secret generic chaos-secrets \
  --from-literal=api-key=${CHAOS_API_KEY} \
  -n chaos-engineering
```

## Testing

```bash
# Unit tests
python -m pytest src/tests/ -v

# With coverage
python -m pytest src/tests/ --cov=src --cov-report=html

# Integration tests (requires Docker Compose running)
python -m pytest src/tests/test_integration.py -v
```

## Environment Variables

```bash
# Core
ENV=production
FLASK_ENV=production
SECRET_KEY=your_flask_secret_key

# Database
DATABASE_URL=sqlite:///chaos_platform.db   # or postgresql://...

# Security
CHAOS_API_KEY=your_secure_api_key
GRAFANA_PASSWORD=your_grafana_password

# Monitoring
LOG_LEVEL=INFO
PROMETHEUS_RETENTION=30d

# Optional
OPENAI_API_KEY=your_openai_key
SLACK_WEBHOOK_URL=your_slack_webhook
```

## Monitoring

### Prometheus metrics exposed

```
system_cpu_percent
system_memory_percent
chaos_injections_total
chaos_scenarios_total{scenario_type="..."}
chaos_orchestrator_requests_total
```

### Log analysis

The `/analyze-logs` endpoint accepts raw log text and returns:
- Severity distribution
- Detected failure patterns (memory, CPU, network, storage)
- Anomaly score
- Recommended chaos scenarios
- Actionable recommendations

## Resource Requirements

| Environment | CPU | RAM | Storage |
|---|---|---|---|
| Minimum | 2 cores | 4 GB | 10 GB |
| Recommended | 4 cores | 8 GB | 50 GB |
| Production | 8+ cores | 16+ GB | 100+ GB |

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for contribution guidelines.

Code standards: Black, isort, flake8, bandit, pytest (80%+ coverage target).

## License

MIT License. See [LICENSE](LICENSE) for details.

## Support

- Issues: https://github.com/ashvinctrl/Mayhem/issues
- Discussions: https://github.com/ashvinctrl/Mayhem/discussions
