import telebot
from telebot import types
import configuration as config
import os
import threading
import uuid
import requests

from tools import state_manager, file_manager, ai_agent, shell_worker, resource_watchdog, webhook_listener, garbage_collector
from utils import subscription_manager, error_handler

# Initialize Bot
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')

# --- UI Helpers ---

def get_start_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_deploy = types.InlineKeyboardButton("🚀 Deploy App", callback_query_data="deploy_menu")
    btn_stats = types.InlineKeyboardButton("📊 My Dashboard", callback_query_data="view_stats")
    btn_help = types.InlineKeyboardButton("📖 Guide", callback_query_data="help_menu")
    btn_account = types.InlineKeyboardButton("👤 Account", callback_query_data="account_info")
    btn_dev = types.InlineKeyboardButton("👨‍💻 Developer", url=config.DEV_LINK)
    btn_community = types.InlineKeyboardButton("🌐 Community", url=config.COMMUNITY_LINK)
    
    markup.add(btn_deploy)
    markup.add(btn_stats, btn_help)
    markup.add(btn_account)
    markup.add(btn_dev, btn_community)
    return markup

def get_join_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn_join = types.InlineKeyboardButton("📢 Join Official Channel", url=f"https://t.me/{config.CHANNEL_USERNAME[1:]}")
    btn_verify = types.InlineKeyboardButton("🔄 Verify Membership", callback_query_data="verify_member")
    markup.add(btn_join)
    markup.add(btn_verify)
    return markup

def check_membership(user_id):
    if user_id == config.ADMIN_ID:
        return True
    try:
        member = bot.get_chat_member(config.CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        pass
    return False

# --- Deployment Logic ---

def process_deployment(message, repo_url=None, zip_path=None):
    user_id = message.from_user.id
    user_state = state_manager.get_user(user_id)
    
    # 1. Check Subscription
    can_go, reason = subscription_manager.can_deploy(user_state)
    if not can_go:
        return bot.reply_to(message, f"❌ <b>Deployment Blocked</b>\n{reason}")
    
    status_msg = bot.reply_to(message, "⚙️ <b>Initializing deployment pipeline...</b>")
    
    temp_dir = file_manager.get_temp_dir()
    success = False
    
    try:
        # 2. Extract/Clone
        if repo_url:
            bot.edit_message_text("📂 <b>Cloning repository...</b>", message.chat.id, status_msg.message_id)
            success = file_manager.clone_repo(repo_url, temp_dir, pat=config.GITHUB_PAT)
        elif zip_path:
            bot.edit_message_text("📦 <b>Extracting codebase...</b>", message.chat.id, status_msg.message_id)
            file_manager.extract_zip(zip_path, temp_dir)
            success = True
            
        if not success:
            return bot.edit_message_text("❌ <b>Source Error:</b> Failed to retrieve codebase.", message.chat.id, status_msg.message_id)
            
        # 3. AI Analysis
        bot.edit_message_text("🧠 <b>AI Security Scan in progress...</b>", message.chat.id, status_msg.message_id)
        file_list, code_contents = ai_agent.read_relevant_files(temp_dir)
        analysis = ai_agent.analyze_codebase(file_list, code_contents)
        
        if not analysis.get("safe"):
            bot.edit_message_text(f"🛑 <b>Security Alert:</b> {analysis.get('reason')}", message.chat.id, status_msg.message_id)
            return garbage_collector.cleanup_deployment(temp_dir)
            
        # 4. Preparation
        bot.edit_message_text("🛠 <b>Generating deployment scripts...</b>", message.chat.id, status_msg.message_id)
        with open(os.path.join(temp_dir, 'requirements.txt'), 'w') as f:
            f.write(analysis.get("requirements_txt", ""))
        with open(os.path.join(temp_dir, 'start.sh'), 'w') as f:
            f.write(analysis.get("start_sh", ""))
            
        # 5. Docker Deployment
        codebase_id = str(uuid.uuid4())[:8]
        bot.edit_message_text("🐳 <b>Building Docker container...</b>", message.chat.id, status_msg.message_id)
        dep_success, container_id = shell_worker.deploy_project(user_id, temp_dir, codebase_id)
        
        if dep_success:
            state_manager.add_container(user_id, container_id, codebase_id)
            bot.edit_message_text(f"✅ <b>Deployment Successful!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n<b>Bot ID:</b> <code>{codebase_id}</code>\n<b>Status:</b> Running 🟢\n\nManage your app in the dashboard.", message.chat.id, status_msg.message_id)
        else:
            error_handler.send_error_to_user(bot, message.chat.id, "Docker Build Failed", container_id)
            
    except Exception as e:
        error_handler.send_error_to_user(bot, message.chat.id, "Runtime Exception", str(e))
    finally:
        garbage_collector.cleanup_deployment(temp_dir)

# --- Command Handlers ---

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    if not check_membership(user_id):
        caption = f"""<b>🛑 Access Restricted</b>
━━━━━━━━━━━━━━━━━━━━━━
Welcome! To utilize the powerful features of <b>BrahMos Cloud</b>, you must first become a verified member of our community.

<b>Required Steps:</b>
1️⃣ Join our official channel.
2️⃣ Click the verify button below.

<i>This ensures a secure and dedicated environment for all our users.</i>"""
        return bot.send_message(message.chat.id, caption, reply_markup=get_join_keyboard())

    caption = f"""🚀 <b>BrahMos Cloud PaaS</b>
━━━━━━━━━━━━━━━━━━━━━━
Welcome, <a href="tg://user?id={user_id}">{first_name}</a>! 👋

Deploy and manage your lightweight bots or web apps directly from Telegram. Our AI-driven security layer ensures your code is safe and optimized for hosting.

⚡ <b>Core Capabilities:</b>
• <b>AI Analysis:</b> Instant malware detection.
• <b>Auto-Deploy:</b> Zero-friction CI/CD.
• <b>Monitoring:</b> Real-time resource tracking.

🛡 <i><b>Disclaimer:</b> This platform is strictly for legitimate hosting. Any malicious activities will result in an immediate ban.</i>"""
    
    banner_path = os.path.join(os.path.dirname(__file__), 'banner.jpg')
    if os.path.exists(banner_path):
        with open(banner_path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=caption, reply_markup=get_start_keyboard())
    else:
        bot.send_message(message.chat.id, caption, reply_markup=get_start_keyboard())

@bot.message_handler(commands=['givepremium'])
def give_premium(message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Usage: /givepremium [user_id]")
    
    target_id = args[1]
    if state_manager.update_user_tier(target_id, "pro"):
        bot.reply_to(message, f"✅ User <code>{target_id}</code> has been elevated to <b>PRO</b> tier.")
    else:
        bot.reply_to(message, "❌ User not found in database.")

@bot.message_handler(func=lambda message: message.text and "github.com" in message.text)
def handle_github_url(message):
    process_deployment(message, repo_url=message.text.strip())

@bot.message_handler(content_types=['document'])
def handle_zip(message):
    if message.document.file_name.endswith('.zip'):
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        temp_zip = f"temp_{uuid.uuid4()}.zip"
        with open(temp_zip, 'wb') as f:
            f.write(downloaded_file)
            
        process_deployment(message, zip_path=temp_zip)
        os.remove(temp_zip)

# --- Callbacks ---

@bot.callback_query_handler(func=lambda call: call.data == "verify_member")
def verify_member_callback(call):
    if check_membership(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Access Granted!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start_command(call)
    else:
        bot.answer_callback_query(call.id, "❌ Verification Failed!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "view_stats")
def view_stats_callback(call):
    user_state = state_manager.get_user(call.from_user.id)
    active_count = len(user_state.get("active_bots", []))
    tier = user_state.get("tier", "free").upper()
    
    text = f"""📊 <b>BrahMos Cloud Dashboard</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>User ID:</b> <code>{call.from_user.id}</code>
<b>Current Tier:</b> {tier}

<b>Active Apps:</b> {active_count}
<b>RAM Limit:</b> {subscription_manager.get_limits(user_state.get("tier"))['ram']}MB
<b>Disk Limit:</b> {subscription_manager.get_limits(user_state.get("tier"))['disk']}MB

<i>Select an app to manage it (coming soon).</i>"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Back", callback_query_data="back_start"))
    bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_start")
def back_start_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    start_command(call)

if __name__ == "__main__":
    # Start Resource Watchdog
    threading.Thread(target=resource_watchdog.monitor_resources, daemon=True).start()
    
    # Start Webhook Listener (Run in background)
    threading.Thread(target=webhook_listener.start_listener, daemon=True).start()
    
    print("BrahMos Cloud Bot is starting...")
    bot.infinity_polling()
