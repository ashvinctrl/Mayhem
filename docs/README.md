# Project Mayhem: AI-Driven Chaos Engineering Platform

## Overview

Project Mayhem is an AI-driven chaos engineering platform designed to automatically create and execute chaos experiments in cloud-native environments such as Kubernetes and Docker. By leveraging advanced AI techniques, the platform aims to identify hidden weaknesses in systems and enhance resilience through targeted fault injection and self-remediation strategies.

## Key Features

- **AI-Generated Chaos Scenarios**: Utilizes natural language processing (NLP) to analyze incident postmortems and logs, identifying common failure patterns. Reinforcement learning algorithms evolve chaos attacks to uncover vulnerabilities.

- **Adaptive Fault Injection**: The AI orchestrator intelligently decides where, when, and how to inject faults based on real-time system health and historical failure data. Supported fault types include network, CPU, memory, disk, and latency.

- **Self-Remediation AI Agent**: After executing chaos experiments, the platform employs an AI-based auto-remediation system to address and mitigate issues, enhancing system reliability.

- **Continuous Learning**: The AI continuously learns from the outcomes of chaos experiments, refining future scenarios and remediation strategies to improve effectiveness.

## Tech Stack

- **Kubernetes**: For orchestrating microservices.
- **Python/Go**: For the chaos orchestrator and various components.
- **Large Language Models (LLMs)**: For NLP-based log analysis.
- **Reinforcement Learning Algorithms**: Such as Proximal Policy Optimization (PPO) and Deep Q-Networks (DQN) for scenario evolution.
- **Grafana/Prometheus**: For real-time monitoring and metrics collection.
- **OpenAI APIs or Local LLMs**: For understanding and analyzing logs.
- **CI/CD Pipelines**: For continuous testing and deployment.

## Getting Started

To set up the Project Mayhem environment, follow these steps:

1. **Clone the Repository**:
   ```
   git clone https://github.com/yourusername/project-mayhem.git
   cd project-mayhem
   ```

2. **Install Dependencies**:
   Use the provided `requirements.txt` to install the necessary Python packages:
   ```
   pip install -r requirements.txt
   ```

3. **Set Up Environment**:
   Run the setup script to configure your development environment:
   ```
   ./scripts/setup_env.sh
   ```

4. **Deploy to Kubernetes**:
   To deploy the application, use the Kubernetes deployment script:
   ```
   ./scripts/deploy_k8s.sh
   ```

5. **Run Tests**:
   Execute the test suite to ensure everything is functioning correctly:
   ```
   ./scripts/run_tests.sh
   ```

## Contribution

Contributions are welcome! Please refer to the `CONTRIBUTING.md` file for guidelines on how to contribute to the project.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

## Acknowledgments

Special thanks to the contributors and the open-source community for their support and resources that made this project possible.