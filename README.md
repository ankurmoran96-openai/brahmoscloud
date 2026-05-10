# BrahMos Cloud PaaS 🚀

BrahMos Cloud is a lightweight, AI-powered Platform as a Service (PaaS) that allows users to host bots, websites, and web apps directly through a Telegram interface. Each application is securely isolated in its own Docker container with strict resource monitoring.

## ✨ Features

- **AI-Powered Security:** Automatically scans code for malware, miners, and stressers using LLMs (OpenAI GPT-4o).
- **Smart Secret Handling:** Detects hardcoded API keys and bot tokens, automatically extracting them into secure environment variables.
- **Isolated Hosting:** Runs every application in a non-root Docker container with dedicated storage and resource limits.
- **Real-Time Monitoring:** Built-in resource watchdog that kills containers exceeding their RAM/Disk pool.
- **GitHub CI/CD:** Native webhook support for zero-friction redeployments on every commit.
- **Professional Telegram UI:** Clean, OSINT-style grid dashboard with interactive management tools.

## 🛠 Project Structure

- `main.py`: Central Telegram Bot logic and command handlers.
- `configuration.py`: System constants and system prompt management.
- `tools/`:
    - `ai_agent.py`: Native Tool Calling integration with OpenAI for code analysis.
    - `shell_worker.py`: Docker SDK wrapper for image building and container management.
    - `webhook_listener.py`: FastAPI server for GitHub push events.
    - `state_manager.py`: JSON-based persistent storage for user-container mappings.
    - `resource_watchdog.py`: Background thread for real-time resource enforcement.
- `utils/`:
    - `subscription_manager.py`: Tier-based logic for Free, Pro, and Admin access.
    - `error_handler.py`: Formatted HTML log reporter for Telegram.

## 🚀 Getting Started

1.  **Clone the Repo**:
    ```bash
    git clone https://github.com/ankurmoran96-openai/brahmoscloud.git
    cd brahmoscloud
    ```
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Setup Environment**:
    Create a `.env` file based on `.env.example` and add your tokens.
4.  **Run with PM2**:
    ```bash
    pm2 start main.py --name brahmos-cloud --interpreter python3
    ```

## 🛡 License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.

---
*Developed by a 14-year-old on a phone.*
