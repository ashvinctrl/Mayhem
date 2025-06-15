
# Project Mayhem: The AI-Driven Chaos Engineering Platform That Breaks Things (So You Don't Have To)


## Overview

Welcome to Project Mayhem, the only platform where breaking your own stuff is not just encouraged—it's automated, AI-powered, and oddly satisfying! Our mission: unleash chaos (safely) on your cloud-native systems, so you can sleep at night knowing your infrastructure is tougher than a caffeinated SRE on call.

**Why?** Because real resilience is forged in the fires of (simulated) disaster. And because it's way more fun to watch your app survive a CPU spike than to explain to your boss why it didn't.


## Key Features (and Shenanigans)

- 🤖 **AI-Generated Chaos Scenarios**: Our AI reads your postmortems and logs (so you don't have to) and invents new ways to break things. It learns from your past failures, so every disaster is a learning opportunity—literally.

- 💥 **Adaptive Fault Injection**: The platform picks the worst possible time and place to inject faults—just like real life! Network partitions, CPU spikes, memory leaks, disk fill-ups, and latency gremlins are all on the menu.

- 🛠️ **Self-Remediation AI Agent**: After the chaos, our AI tries to fix what it broke. Sometimes it even succeeds. (But seriously, it gets smarter every time.)

- 🔄 **Continuous Learning**: The more chaos you unleash, the smarter the platform gets. It's like a chaos monkey, but with a PhD and a sense of humor.


## Tech Stack (a.k.a. The Mayhem Arsenal)

- **Kubernetes**: Herds your containers like digital sheep.
- **Python**: The brains behind the chaos.
- **Large Language Models (LLMs)**: Reads logs, finds patterns, and occasionally writes poetry about your outages.
- **Reinforcement Learning**: The AI gets better at breaking things the more you use it. (Don't worry, it only uses its powers for good.)
- **Grafana & Prometheus**: So you can watch the chaos unfold in real time, with pretty graphs.
- **OpenAI APIs or Local LLMs**: For log understanding and scenario generation.
- **CI/CD Pipelines**: Because chaos waits for no one.



## Getting Started (Release the Mayhem)

1. **Clone the Repository**
   ```sh
   git clone https://github.com/yourusername/project-mayhem.git
   cd project-mayhem
   ```

2. **Set Up the Environment**
   Run the setup script to install necessary dependencies (or just use Docker Compose if you like living on the edge).
   ```sh
   ./scripts/setup_env.sh
   ```

3. **Deploy to Kubernetes or Docker Compose**
   - For Kubernetes:
     ```sh
     ./scripts/deploy_k8s.sh
     ```
   - For Docker Compose:
     ```sh
     docker-compose up --build
     ```

4. **Run Tests**
   ```sh
   ./scripts/run_tests.sh
   ```

5. **Open the Beautiful Chaos UI**
   - Once the orchestrator is running, open your browser and go to:
     - [http://localhost:5000/](http://localhost:5000/) or [http://localhost:5000/ui](http://localhost:5000/ui)
   - Here you can:
     - View orchestrator health and live metrics
     - List and inject chaos scenarios with a click
     - Enjoy a modern, humorous interface

**Note:** The UI is served directly from the orchestrator Flask app. No extra setup needed!


## Contribution

Contributions are welcome! If you have a new way to break things (or fix them), open a PR. Please refer to the [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines. Bonus points for adding more chaos and more jokes.


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details. (You break it, you bought it!)


## Acknowledgments

- Inspired by Netflix's Chaos Monkey, Gremlins, and every SRE who's ever said "What could possibly go wrong?"
- Special thanks to the open-source community for their contributions, memes, and moral support.