
# Project Mayhem: The AI-Driven Chaos Engineering Platform That Breaks Things (So You Don't Have To)

[![CI/CD Pipeline](https://github.com/yourusername/project-mayhem/workflows/Project%20Mayhem%20CI/CD/badge.svg)](https://github.com/yourusername/project-mayhem/actions)
[![Security Score](https://img.shields.io/badge/security-A+-green.svg)](https://github.com/yourusername/project-mayhem/security)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Pulls](https://img.shields.io/docker/pulls/yourusername/chaos-orchestrator.svg)](https://hub.docker.com/r/yourusername/chaos-orchestrator)

## 🌟 Overview

Welcome to Project Mayhem, the only platform where breaking your own stuff is not just encouraged—it's automated, AI-powered, and oddly satisfying! Our mission: unleash chaos (safely) on your cloud-native systems, so you can sleep at night knowing your infrastructure is tougher than a caffeinated SRE on call.

**Why?** Because real resilience is forged in the fires of (simulated) disaster. And because it's way more fun to watch your app survive a CPU spike than to explain to your boss why it didn't.

## 🚀 Key Features (and Shenanigans)

### 🤖 **AI-Generated Chaos Scenarios**
Our advanced NLP engine reads your postmortems and logs (so you don't have to) and invents new ways to break things. It learns from your past failures, so every disaster is a learning opportunity—literally.

### 💥 **Adaptive Fault Injection**
The platform picks the worst possible time and place to inject faults—just like real life! Network partitions, CPU spikes, memory leaks, disk fill-ups, and latency gremlins are all on the menu.

### �️ **Production-Ready Security**
- API key authentication with rate limiting
- Secure secrets management
- Input validation and sanitization
- Non-root Docker containers
- RBAC-enabled Kubernetes deployment

### 🔄 **Continuous Learning**
The more chaos you unleash, the smarter the platform gets. It's like a chaos monkey, but with a PhD and a sense of humor.

### 📊 **Real-Time Monitoring**
- Prometheus metrics integration
- Grafana dashboards with 15+ visualizations
- System health monitoring
- Chaos experiment tracking and analytics

### 🎯 **15+ Realistic Chaos Scenarios**
- CPU spikes and memory leaks
- Network latency and partitions
- Database slowdowns and timeouts
- Container restarts and process kills
- SSL certificate expiry simulation
- And many more enterprise-grade scenarios!

## 🛠️ Tech Stack (a.k.a. The Mayhem Arsenal)

- **Backend**: Python 3.9+ with Flask and SQLAlchemy
- **Frontend**: Modern HTML5/CSS3/JavaScript with Bootstrap 5
- **Containerization**: Docker with multi-stage builds
- **Orchestration**: Kubernetes with RBAC and security policies
- **Monitoring**: Prometheus + Grafana with custom dashboards
- **AI/ML**: Advanced NLP for log analysis and pattern detection
- **Security**: API authentication, rate limiting, input validation
- **CI/CD**: GitHub Actions with automated testing and deployment
- **Database**: SQLite (dev) / PostgreSQL (production)

## 📋 Prerequisites

- **Docker** 20.0+ and Docker Compose 2.0+
- **Kubernetes** 1.21+ (for production deployment)
- **Python** 3.9+ (for local development)
- **Git** for version control

## ⚡ Quick Start

### 1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/project-mayhem.git
cd project-mayhem
```

### 2. **Environment Setup**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# CHAOS_API_KEY=your_secure_api_key_here
# GRAFANA_PASSWORD=your_secure_password_here
```

### 3. **Docker Compose Deployment (Recommended)**
```bash
# Start the complete stack
docker-compose up --build -d

# View logs
docker-compose logs -f chaos-orchestrator
```

### 4. **Access the Platform**
- **Main UI**: http://localhost:5000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin / your_password)

### 5. **Run Your First Chaos Experiment**
```bash
# Using the UI - navigate to http://localhost:5000
# Or using API with your API key:

curl -X POST http://localhost:5000/inject \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "cpu_spike",
    "duration": 30,
    "intensity": "medium"
  }'
```

## 🚢 Production Deployment

### Kubernetes Deployment
```bash
# Production deployment to Kubernetes
./scripts/deploy_production.sh

# Or step by step:
kubectl apply -f configs/kubernetes_deployment_production.yaml

# Check deployment status
kubectl get pods -n chaos-engineering
```

### Security Configuration
```bash
# Generate secure API key
export CHAOS_API_KEY=$(openssl rand -hex 32)

# Create Kubernetes secrets
kubectl create secret generic chaos-secrets \
  --from-literal=api-key=${CHAOS_API_KEY} \
  --from-literal=database-url="postgresql://..." \
  -n chaos-engineering
```

## 🧪 Testing

### Unit Tests
```bash
# Run all tests
python -m pytest src/tests/ -v

# Run with coverage
python -m pytest src/tests/ --cov=src --cov-report=html
```

### Integration Tests
```bash
# Start test environment
docker-compose up -d

# Run integration tests
python -m pytest src/tests/test_integration.py -v

# Cleanup
docker-compose down
```

### Load Testing
```bash
# Install artillery
npm install -g artillery

# Run load tests
artillery run tests/load-test.yml
```

## 📊 Monitoring & Observability

### Grafana Dashboards
- **System Metrics**: CPU, Memory, Disk, Network utilization
- **Chaos Experiments**: Success/failure rates, duration tracking
- **Application Metrics**: Request rates, response times, error rates
- **AI Insights**: Pattern detection, failure predictions

### Prometheus Metrics
```
# System metrics
system_cpu_percent
system_memory_percent
chaos_injections_total
chaos_scenarios_total{scenario_type="cpu_spike"}

# Application metrics
flask_http_request_duration_seconds
flask_http_request_total
```

### Log Analysis
The platform includes advanced NLP-based log analysis that:
- Identifies failure patterns automatically
- Predicts potential system failures
- Recommends targeted chaos scenarios
- Generates actionable insights

## 🤖 AI Features

### Intelligent Scenario Generation
```python
# Example: AI-generated chaos recommendations
analyzer = NLPLogAnalyzer()
analysis = analyzer.analyze_logs(your_logs)
patterns = analyzer.extract_failure_patterns(analysis)
prediction = analyzer.predict_failure_likelihood(current_metrics, patterns)
```

### Pattern Recognition
- **Memory leaks**: Detects memory-related failures in logs
- **CPU exhaustion**: Identifies CPU-related performance issues
- **Network issues**: Recognizes network partition patterns
- **Service failures**: Maps service-specific failure patterns

## 🔐 Security Features

### Authentication & Authorization
- API key-based authentication
- Rate limiting (configurable per endpoint)
- Input validation and sanitization
- Secure secrets management

### Container Security
- Non-root user execution
- Read-only root filesystem
- Security context policies
- Vulnerability scanning with Trivy

### Kubernetes Security
- RBAC policies with minimal permissions
- Network policies for traffic isolation
- Pod Security Standards enforcement
- Secret management with encryption

## 🔧 Configuration

### Environment Variables
```bash
# Core Configuration
ENV=production
FLASK_ENV=production
SECRET_KEY=your_flask_secret_key

# Database
DATABASE_URL=sqlite:///chaos_platform.db

# Security
CHAOS_API_KEY=your_secure_api_key
GRAFANA_PASSWORD=your_grafana_password

# Monitoring
LOG_LEVEL=INFO
PROMETHEUS_RETENTION=30d

# Optional: External Services
OPENAI_API_KEY=your_openai_key
SLACK_WEBHOOK_URL=your_slack_webhook
```

### Chaos Scenario Configuration
```yaml
# configs/chaos_config.yaml
scenarios:
  cpu_spike:
    max_duration: 300
    intensity_levels: [low, medium, high]
    safety_checks: true
  
  memory_leak:
    max_duration: 180
    memory_limit_mb: 500
    cleanup_enabled: true
```

## 📈 Performance & Scalability

### Resource Requirements
- **Minimum**: 2 CPU cores, 4GB RAM, 10GB storage
- **Recommended**: 4 CPU cores, 8GB RAM, 50GB storage
- **Production**: 8+ CPU cores, 16GB+ RAM, 100GB+ storage

### Scaling
- Horizontal pod autoscaling in Kubernetes
- Database connection pooling
- Prometheus metrics for scaling decisions
- Load balancer support with session affinity

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone and setup development environment
git clone https://github.com/yourusername/project-mayhem.git
cd project-mayhem

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run pre-commit hooks
pre-commit install

# Start development server
python src/app.py
```

### Code Quality Standards
- **Code formatting**: Black + isort
- **Linting**: flake8 + pylint
- **Security**: bandit + safety
- **Testing**: pytest with 80%+ coverage
- **Documentation**: Sphinx with type hints

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details. (You break it, you bought it!)

## 🙏 Acknowledgments

- Inspired by Netflix's Chaos Monkey, Gremlins, and every SRE who's ever said "What could possibly go wrong?"
- Special thanks to the open-source community for their contributions, memes, and moral support
- Built with ❤️ and a healthy dose of controlled chaos

## 📞 Support

- **Documentation**: [Full documentation](https://yourusername.github.io/project-mayhem)
- **Issues**: [GitHub Issues](https://github.com/yourusername/project-mayhem/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/project-mayhem/discussions)
- **Security**: security@yourdomain.com

---

**Remember**: In chaos we trust, but in monitoring we verify! 🔥💥🚀