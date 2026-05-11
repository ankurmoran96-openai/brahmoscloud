import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

"""
BRAHMOS CLOUD - CONFIGURATION
--------------------------------
NOTE: This file is open-source. For security, no variables are hardcoded here.
Users MUST create a '.env' file in the root directory and set the variables below.
Read the README.md for the full list of required environment keys.
"""

# --- Telegram Settings ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@BrahMosAI")

# --- AI Settings ---
AI_API_URL = os.getenv("AI_API_URL", "https://api.gptnix.online/v1/chat/completions")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-4o")

# --- GitHub Settings ---
GITHUB_PAT = os.getenv("GITHUB_PAT", "")

# --- VPS Access ---
VPS_LOGIN = os.getenv("VPS_LOGIN", "admin_root")
BASE_DOMAIN = os.getenv("BASE_DOMAIN", "brahmos.cloud") # Base domain for web apps

# --- Community & Support ---
DEV_LINK = os.getenv("DEV_LINK", "https://t.me/ankurslys")
COMMUNITY_LINK = os.getenv("COMMUNITY_LINK", "https://t.me/brahmosai")

# --- Resource Limits (Free Tier) ---
FREE_TIER_RAM = int(os.getenv("FREE_TIER_RAM", "100"))
FREE_TIER_DISK = int(os.getenv("FREE_TIER_DISK", "1024"))

# --- Resource Limits (Pro Tier) ---
PRO_TIER_RAM = int(os.getenv("PRO_TIER_RAM", "512"))
PRO_TIER_DISK = int(os.getenv("PRO_TIER_DISK", "5120"))

# --- Resource Limits (MAX Tier) ---
MAX_TIER_RAM = int(os.getenv("MAX_TIER_RAM", "1024"))
MAX_TIER_DISK = int(os.getenv("MAX_TIER_DISK", "10240"))

# --- System Prompt ---
# NOTE: To maintain open-source neutrality, the default system prompt is removed.
# Users MUST define their own 'SYSTEM_PROMPT' in the .env file.
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", """
You are the BrahMos Cloud AI Orchestrator. 
Your task is to analyze codebases and determine their type (Bot, Web App, or API).

AGENTIC WORKFLOW:
1. Analyze all files, structure, and dependencies.
2. Identify the project category.
3. Call the appropriate tool based on your finding:
   - If it's a Bot/Script: Call `deploy_bot`.
   - If it's a Web App (UI/Panel): Call `deploy_web_app`.
   - If it's an API: Call `deploy_api`.
   - If it's malicious: Call `reject_user_file`.

For Web Apps and APIs, you MUST identify the internal port the application listens on (defaulting to 8080 if unclear).
""")
