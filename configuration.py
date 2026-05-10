import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Telegram Settings ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6049120581"))
CHANNEL_USERNAME = "@BrahMosAI"

# --- AI Settings ---
AI_API_URL = os.getenv("AI_API_URL", "https://api.gptnix.online/v1/chat/completions")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-4o")

# --- GitHub Settings ---
GITHUB_PAT = os.getenv("GITHUB_PAT", "")

# --- Community & Support ---
DEV_LINK = "https://t.me/ankurslys"
COMMUNITY_LINK = "https://t.me/brahmosai"

# --- Resource Limits (Free Tier) ---
FREE_TIER_RAM = 100  # MB
FREE_TIER_DISK = 1000  # MB

# --- Resource Limits (Pro Tier) ---
PRO_TIER_RAM = 512  # MB
PRO_TIER_DISK = 5000  # MB

# --- System Prompt ---
SYSTEM_PROMPT = """
You are the BrahMos Cloud Security & Deployment Agent. 
Your task is to analyze user-provided codebases for malicious scripts, malware, or any code that violates VPS guidelines (e.g., crypto miners, stressers, phishing tools).

If you find anything suspicious:
1. Call the `reject_user_file` tool with a clear reason.

If the code is safe:
1. Analyze the project structure.
2. Identify dependencies and create a `requirements.txt` if missing.
3. Create a `start.sh` script to launch the application (e.g., `python3 main.py`).
4. Call the `deploy_project` tool to initiate hosting.

Be strict about security but helpful for legitimate developers.
"""
