# BrahMos Cloud PaaS 🚀

BrahMos Cloud is a lightweight PaaS (Platform as a Service) solution that allows users to deploy and host their bots, web apps, or websites directly through a Telegram interface.

## ✨ Features
- **AI-Powered Security:** Automatically scans incoming code for malware and malicious scripts using LLMs.
- **Zero-Friction CI/CD:** Auto-redeployments via GitHub Webhooks.
- **Resource Management:** Automated monitoring of RAM and Disk usage with instant container isolation.
- **Isolated Hosting:** Each application runs in its own secure Docker container.
- **Telegram Native:** Manage your entire cloud infrastructure via simple Telegram commands and interactive keyboards.

## 🛠 Project Structure
- `main.py`: Telegram Bot logic and command handlers.
- `tools/ai_agent.py`: LLM-based code analysis and script generation.
- `tools/shell_worker.py`: Docker-based deployment engine.
- `tools/webhook_listener.py`: GitHub webhook handler for CI/CD.
- `tools/file_manager.py`: Secure file extraction and PAT handling.
- `tools/state_manager.py`: User state and resource tracking.
- `tools/resource_watchdog.py`: Background resource monitoring.
- `tools/garbage_collector.py`: Automatic disk cleanup.

## 🚀 Getting Started
1. Clone the repository.
2. Setup your `.env` file with the required API keys and tokens.
3. Run `python3 main.py`.

## 🛡 License
This project is licensed under the MIT License.

---
*Developed by a 14-year-old on a phone.*
