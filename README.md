# BrahMos Cloud PaaS 🚀

BrahMos Cloud is a lightweight, AI-powered **Platform as a Service (PaaS)** that allows users to deploy and manage bots, websites, and web apps directly through a Telegram interface. It combines the intelligence of Large Language Models with the security of Docker containerization to provide a "Zero-Friction" hosting experience.

## 🎯 Use Cases

- **Bot Hosting:** Instantly deploy Telegram/Discord bots without manual server setup.
- **Web Applications:** Host lightweight Python (Flask/FastAPI) or Node.js web apps.
- **Script Execution:** Run background automation scripts in a secure, isolated environment.
- **PaaS Prototyping:** Ideal for developers wanting to offer a hosting service to their own community via Telegram.

## 🧠 How it Works

1.  **Input:** User sends a GitHub Repository link or a `.zip` file.
2.  **AI Security Layer:** An LLM (OpenAI GPT-4o) scans the code for malware, miners, or malicious scripts.
3.  **Auto-Correction:** If the AI finds hardcoded secrets (like bot tokens), it automatically extracts them into a `.env` file and updates the code to use environment variables.
4.  **Containerization:** The system generates a custom `Dockerfile`, `start.sh`, and `requirements.txt` on the fly.
5.  **Isolation:** The app is deployed in a dedicated Docker container as a **non-root user** with strict RAM and Disk limits.
6.  **CI/CD:** Any subsequent commits to the linked GitHub repository automatically trigger a redeployment via webhooks.

## ✨ Key Features

- **Dynamic Dashboard:** Automatically switches between "Deploy" and "Manage" views.
- **Real-Time Stats:** Track live RAM usage and remaining quota for every project.
- **Resource Watchdog:** Background sniper that kills containers exceeding their resource pool.
- **Administrative Suite:** Complete audit tools to view all users, files, and global system usage.

## 🛠 Setup & Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/ankurmoran96-openai/brahmoscloud.git
    cd brahmoscloud
    ```
2.  **Configure Environment**:
    Create a `.env` file based on the keys found in `configuration.py`.
    ```env
    BOT_TOKEN=your_telegram_bot_token
    ADMIN_ID=your_telegram_id
    AI_API_KEY=your_openai_api_key
    GITHUB_PAT=your_github_personal_access_token
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run with PM2**:
    ```bash
    pm2 start main.py --name brahmos-cloud --interpreter python3
    ```

## 🛡 License

This project is licensed under the **MIT License**. See the [LICENSE](./LICENSE) file for details.

---
*Developed by a 14-year-old on a phone.*
