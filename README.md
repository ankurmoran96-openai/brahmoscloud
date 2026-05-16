# ☁️ BrahMos Cloud: The Autonomous AI-Native PaaS

[![Development](https://img.shields.io/badge/Platform-Mobile-orange?style=for-the-badge&logo=android)](https://github.com/ankurmoran96-openai)
[![Architecture](https://img.shields.io/badge/Architecture-Agentic--Orchestration-blue?style=for-the-badge)](https://github.com/ankurmoran96-openai)
[![Security](https://img.shields.io/badge/Security-LLM--Audited-red?style=for-the-badge)](https://github.com/ankurmoran96-openai)

**BrahMos Cloud** is an enterprise-grade, AI-native **Platform as a Service (PaaS)** engineered to bridge the gap between AI intelligence and high-performance infrastructure. It automates the entire software lifecycle—from code analysis and security auditing to containerized deployment and real-time resource management.

> "Infrastructure is the engine, AI is the pilot."

---

## 🚀 Key Features

### 🤖 Agentic Orchestration (The Brain)
Powered by a 3-agent GPT-4o pipeline that "thinks" before it builds:
*   **Agent 1 (Discovery Scout):** Automatically detects project types (Python/Node.js), identifies entry points, and extracts environment variables.
*   **Agent 2 (Security Auditor):** Performs deep, intent-based security scans to block malware, miners, and DDoS scripts.
*   **Agent 3 (Deployment Architect):** Dynamically generates production-ready `Dockerfiles`, `start.sh` scripts, and dependency manifests.

### 🐳 High-Performance Infrastructure (The Engine)
*   **Isolated Environments:** Every deployment runs in a dedicated Docker container with strict RAM and Disk limits.
*   **Dynamic Port Mapping:** Automatic allocation of high-range ports for Web Apps and APIs.
*   **Persistent Storage:** Dedicated user-specific storage volumes ensure data survives redeployments.

### 🔄 Zero-Touch CI/CD
*   **GitHub Webhook Integration:** Push your code to GitHub, and BrahMos Cloud automatically triggers a fetch, security re-audit, and container rebuild.
*   **Real-time Notifications:** Get detailed Telegram alerts for every update, including commit messages and build status.

### 🛡️ Site Reliability Engineering (SRE)
*   **Resource Watchdog:** An asynchronous monitoring thread that kills rogue containers violating tier limits.
*   **Self-Healing:** Autonomous recovery protocols that analyze crash logs and attempt to redeploy failing services.

---

## 🛠️ Tech Stack

*   **Logic:** Python 3.10+
*   **Orchestration:** Docker Engine SDK
*   **AI:** OpenAI GPT-4o / GPT-4o-mini
*   **Web Layer:** FastAPI & Uvicorn (Webhooks)
*   **UI:** Telegram Bot API (Mobile-First Management)
*   **Database:** Thread-Safe JSON State Management

---

## 📂 System Architecture

```text
BrahMosCloud/
├── main.py              # Telegram UI & Main Controller
├── tools/
│   ├── ai_agent.py      # The 3-Agent Logic Brain
│   ├── shell_worker.py   # Docker Lifecycle Manager
│   ├── state_manager.py  # Thread-Safe persistence
│   └── webhook_listener.py # CI/CD Engine
├── storage/             # Production Container Data
└── utils/               # Subscription & Error Handling
```

---

## 🌟 The Developer Story

BrahMos Cloud was designed and built by **Ankur Moran**, a 14-year-old software architect. In a world of high-end workstations, this entire ecosystem—including the Docker orchestration logic and multi-agent pipelines—was engineered entirely on a **mobile phone (Oppo A3 5G)**. 

It stands as a testament that **Architectural Vision** is not limited by hardware.

---

## 📜 License
MIT License. Built with grit and vision by **Ankur Moran**.
[Telegram](https://t.me/ankurslys) | [GitHub](https://github.com/ankurmoran96-openai)
