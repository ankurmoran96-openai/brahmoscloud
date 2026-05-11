import telebot
from telebot import types
import configuration as config
import os
import threading
import uuid
import requests
import html

from tools import state_manager, file_manager, ai_agent, shell_worker, resource_watchdog, webhook_listener, garbage_collector
from utils import subscription_manager, error_handler

# Initialize Bot
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')

# --- UI Helpers ---

def escape_html(text):
    return html.escape(str(text))

def get_start_keyboard(user_id=None):
    markup = types.InlineKeyboardMarkup()
    
    has_apps = False
    if user_id:
        projects = state_manager.get_user_projects(user_id)
        if projects:
            has_apps = True
            
    if has_apps:
        markup.row(types.InlineKeyboardButton("📁 My Applications", callback_data="my_apps"))
    else:
        markup.row(types.InlineKeyboardButton("🚀 Deploy App", callback_data="deploy_menu"))
        
    markup.row(types.InlineKeyboardButton("👤 My Account", callback_data="account_info"),
               types.InlineKeyboardButton("📖 Guide", callback_data="help_menu"))
    markup.row(types.InlineKeyboardButton("👨‍💻 Developer", url=config.DEV_LINK),
               types.InlineKeyboardButton("🌐 Community", url=config.COMMUNITY_LINK))
    return markup

def get_join_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn_join = types.InlineKeyboardButton("📢 Join Official Channel", url=f"https://t.me/{config.CHANNEL_USERNAME[1:]}")
    btn_verify = types.InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_member")
    markup.row(btn_join)
    markup.row(btn_verify)
    return markup

def check_membership(user_id):
    if user_id == config.ADMIN_ID:
        return True
    try:
        member = bot.get_chat_member(config.CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception as e:
        print(f"Membership check failed for {user_id}: {e}")
    return False

# --- Deployment Logic ---

def process_deployment(message, repo_url=None, zip_path=None, custom_pat=None, project_name=None):
    user_id = message.from_user.id
    user_state = state_manager.get_user(user_id)
    is_admin = (user_id == config.ADMIN_ID)
    
    # 1. Check Subscription
    can_go, reason = subscription_manager.can_deploy(user_state, is_admin=is_admin)
    if not can_go:
        return bot.reply_to(message, f"❌ <b>Deployment Blocked</b>\n{reason}")
    
    status_msg = bot.reply_to(message, "⚙️ <b>Initializing deployment pipeline...</b>")
    
    temp_dir = file_manager.get_temp_dir()
    success = False
    
    try:
        # 2. Extract/Clone
        if repo_url:
            bot.edit_message_text("📂 <b>Cloning repository...</b>", message.chat.id, status_msg.message_id)
            # Use custom PAT if provided, else fallback to global config PAT
            active_pat = custom_pat if custom_pat else config.GITHUB_PAT
            success = file_manager.clone_repo(repo_url, temp_dir, pat=active_pat)
            
            if not success:
                if not custom_pat:
                    return bot.edit_message_text("❌ <b>Access Denied:</b> This repository appears to be private or invalid. <b>Please send a public link or a PAT token along with it.</b> Private repos aren't executable without authorization.", message.chat.id, status_msg.message_id)
                else:
                    return bot.edit_message_text("❌ <b>Source Error:</b> Failed to retrieve codebase. Even with the provided PAT, access was denied. Ensure the URL and Token are correct.", message.chat.id, status_msg.message_id)

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
            
        env_content = analysis.get("env_file", "")
        if env_content:
            with open(os.path.join(temp_dir, '.env'), 'w') as f:
                f.write(env_content)
            
        # 5. Docker Deployment
        codebase_id = str(uuid.uuid4())[:8]
        proj_type = analysis.get("project_type", "bot")
        is_web = proj_type in ['web_app', 'api']
        assigned_port = state_manager.get_next_available_port() if is_web else None
        
        bot.edit_message_text(f"🐳 <b>Deploying {proj_type.upper()}...</b>", message.chat.id, status_msg.message_id)
        dep_success, container_id = shell_worker.deploy_project(user_id, temp_dir, codebase_id, port=assigned_port)
        
        if dep_success:
            state_manager.add_container(user_id, container_id, codebase_id, port=assigned_port, project_name=project_name)
            
            # Post-deployment check
            import time
            time.sleep(5)
            try:
                container = shell_worker.client.containers.get(container_id)
                if container.status == "running":
                    access_info = ""
                    if is_web:
                        # Netlify-style Default URL
                        web_url = f"http://{codebase_id}.{config.BASE_DOMAIN}"
                        # Raw IP access for immediate local testing
                        try:
                            vps_ip = requests.get('https://api.ipify.org', timeout=5).text
                        except Exception:
                            vps_ip = "YOUR_VPS_IP"
                            
                        raw_access = f"http://{vps_ip}:{assigned_port}"
                        
                        access_info = f"\n🌐 <b>Default URL:</b> {web_url}\n🔗 <b>Raw Access:</b> <code>{raw_access}</code>"
                    
                    bot.edit_message_text(f"✅ <b>{proj_type.upper()} Deployed!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n<b>Bot ID:</b> <code>{codebase_id}</code>\n<b>Status:</b> Running 🟢{access_info}\n\nManage your app in the dashboard.", message.chat.id, status_msg.message_id)
                else:
                    logs = container.logs(tail=20).decode("utf-8")
                    bot.edit_message_text(f"⚠️ <b>Deployment Alert:</b> Container started but is now <code>{container.status}</code>.\n\n<b>Recent Logs:</b>\n<code>{html.escape(logs)}</code>", message.chat.id, status_msg.message_id)
            except Exception:
                bot.edit_message_text(f"✅ <b>Deployment Initialized!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n<b>Bot ID:</b> <code>{codebase_id}</code>\n\nCheck status in your dashboard.", message.chat.id, status_msg.message_id)
        else:
            error_handler.send_error_to_user(bot, message.chat.id, "Docker Build Failed", container_id)
            
    except Exception as e:
        error_handler.send_error_to_user(bot, message.chat.id, "Runtime Exception", str(e))
    finally:
        garbage_collector.cleanup_deployment(temp_dir)

# --- Command Handlers ---

@bot.message_handler(commands=['start'])
def start_command(message, edit=False):
    # Support both Message and CallbackQuery objects
    is_callback = hasattr(message, 'message')
    target_user = message.from_user
    chat_id = message.message.chat.id if is_callback else message.chat.id
    message_id = message.message.message_id if is_callback else None

    first_name = escape_html(target_user.first_name)
    user_id = target_user.id
    
    if not check_membership(user_id):
        caption = f"""<b>🛑 Access Restricted</b>
━━━━━━━━━━━━━━━━━━━━━━
Welcome! To utilize the powerful features of <b>BrahMos Cloud</b>, you must first become a verified member of our community.

<b>Required Steps:</b>
1️⃣ Join our official channel.
2️⃣ Click the verify button below.

<i>This ensures a secure and dedicated environment for all our users.</i>"""
        if edit and message_id:
            try:
                return bot.edit_message_caption(caption, chat_id, message_id, reply_markup=get_join_keyboard())
            except Exception:
                return bot.edit_message_text(caption, chat_id, message_id, reply_markup=get_join_keyboard())
        return bot.send_message(chat_id, caption, reply_markup=get_join_keyboard())

    caption = f"""🚀 <b>BrahMos Cloud PaaS</b>
━━━━━━━━━━━━━━━━━━━━━━
Welcome, <a href="tg://user?id={user_id}">{first_name}</a>! 👋

Deploy and manage your lightweight bots or web apps directly from Telegram. Our AI-driven security layer ensures your code is safe and optimized for hosting.

⚡ <b>System Status:</b> <code>Functional 🟢</code>
🛡 <b>Security:</b> <code>Active 🛡</code>

⚠️ <b>Notice:</b> <i>Users are responsible for their own backups. We are not responsible for any data loss.</i>"""
    
    if edit and message_id:
        try:
            return bot.edit_message_caption(caption, chat_id, message_id, reply_markup=get_start_keyboard(user_id))
        except Exception:
            return bot.edit_message_text(caption, chat_id, message_id, reply_markup=get_start_keyboard(user_id))

    banner_path = os.path.join(os.path.dirname(__file__), 'banner.jpg')
    if os.path.exists(banner_path):
        with open(banner_path, 'rb') as photo:
            bot.send_photo(chat_id, photo, caption=caption, reply_markup=get_start_keyboard(user_id))
    else:
        bot.send_message(chat_id, caption, reply_markup=get_start_keyboard(user_id))

# --- Deployment Handlers ---

def set_project_name_step(message, repo_url=None, zip_path=None, custom_pat=None):
    project_name = message.text.strip()
    if len(project_name) < 3:
        project_name = None # Fallback to default
        
    process_deployment(message, repo_url=repo_url, zip_path=zip_path, custom_pat=custom_pat, project_name=project_name)

def start_naming_flow(message, repo_url=None, zip_path=None, custom_pat=None):
    msg = bot.reply_to(message, "📝 <b>Set Project Name:</b>\n━━━━━━━━━━━━━━━━━━━━━━\nPlease send a name for your new application (e.g., <code>My Website</code>).")
    bot.register_next_step_handler(msg, set_project_name_step, repo_url=repo_url, zip_path=zip_path, custom_pat=custom_pat)

@bot.message_handler(commands=['deploy'])
def deploy_command_manual(message):
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("🚀")])
    except Exception:
        pass
        
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/deploy &lt;github_url&gt; [pat_token]</code>\n\n<i>Note: PAT token is only required for private repositories.</i>")
    
    repo_url = args[1]
    pat_token = args[2] if len(args) > 2 else None
    start_naming_flow(message, repo_url=repo_url, custom_pat=pat_token)

@bot.message_handler(commands=['addpremium'])
def add_premium_admin(message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    args = message.text.split()
    if len(args) < 3:
        return bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/addpremium &lt;user_id&gt; &lt;days&gt; [tier: pro/max]</code>")
    
    target_id = args[1]
    try:
        days = int(args[2])
    except ValueError:
        return bot.reply_to(message, "❌ Invalid days provided.")
        
    tier = args[3].lower() if len(args) > 3 else "pro"
    if tier not in ["pro", "max"]:
        return bot.reply_to(message, "❌ Invalid tier. Use 'pro' or 'max'.")

    if state_manager.update_user_premium(target_id, days, tier=tier):
        bot.reply_to(message, f"✅ User <code>{target_id}</code> now has <b>{tier.upper()}</b> access for {days} days.")
        try:
            bot.send_message(target_id, f"💎 <b>{tier.upper()} Tier Activated!</b>\n━━━━━━━━━━━━━━━━━━━━━━\nYou have been granted <b>{tier.upper()}</b> access for {days} days. Your limits are now expanded! 🚀")
        except Exception:
            pass
    else:
        bot.reply_to(message, "❌ Failed to update premium status.")

@bot.message_handler(commands=['rempremium'])
def rem_premium_admin(message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/rempremium &lt;user_id&gt;</code>")
    
    target_id = args[1]
    if state_manager.update_user_premium(target_id, 0):
        bot.reply_to(message, f"✅ User <code>{target_id}</code> has been returned to the <b>FREE</b> tier.")
        try:
            bot.send_message(target_id, "⚠️ <b>Premium Expired/Removed</b>\n━━━━━━━━━━━━━━━━━━━━━━\nYour PRO access has been revoked. You have returned to the <b>FREE</b> tier limits.")
        except Exception:
            pass
    else:
        bot.reply_to(message, "❌ Failed to remove premium.")

@bot.message_handler(commands=['listusers'])
def list_users_admin(message):
    # Check ID from from_user (for command) or from call (for callback)
    user_id = message.from_user.id if message.from_user else None
    if user_id != config.ADMIN_ID and not hasattr(message, 'admin_authorized'):
        return

    users = state_manager.get_all_users()
    if not users:
        return bot.reply_to(message, "📂 <b>No users found in database.</b>")

    text = "👑 <b>Admin: User & File Audit</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    
    for user_id, data in users.items():
        text += f"👤 <b>User:</b> <code>{user_id}</code> ({data['tier'].upper()})\n"
        projects = state_manager.get_user_projects(user_id)
        
        if not projects:
            text += "⤷ <i>No active projects.</i>\n"
        else:
            for proj in projects:
                code_id = proj['codebase_id']
                path = os.path.join(shell_worker.STORAGE_BASE, str(user_id), code_id)
                
                # List files in the project directory
                try:
                    files = os.listdir(path)
                    file_list = ", ".join(files[:5]) + ("..." if len(files) > 5 else "")
                except Exception:
                    file_list = "Directory Error"

                text += f"⤷ 📂 <code>{code_id}</code>\n  └ 📍 <code>{path}</code>\n  └ 📄 {file_list}\n"
        
        text += "──────────────────\n"

    # Handle long messages by splitting
    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            bot.send_message(message.chat.id, text[x:x+4000])
    else:
        bot.reply_to(message, text)

@bot.message_handler(func=lambda message: message.text and "github.com" in message.text)
def handle_github_url(message):
    try:
        bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("🚀")])
    except Exception:
        pass
    start_naming_flow(message, repo_url=message.text.strip())

@bot.message_handler(content_types=['document'])
def handle_zip(message):
    if message.document.file_name.endswith('.zip'):
        try:
            bot.set_message_reaction(message.chat.id, message.message_id, [types.ReactionTypeEmoji("🚀")])
        except Exception:
            pass
            
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        temp_zip = f"temp_{uuid.uuid4()}.zip"
        with open(temp_zip, 'wb') as f:
            f.write(downloaded_file)
            
        start_naming_flow(message, zip_path=temp_zip)

# --- Callbacks ---

@bot.message_handler(commands=['stats'])
def stats_command_admin(message):
    user_id = message.from_user.id if message.from_user else None
    if user_id != config.ADMIN_ID and not hasattr(message, 'admin_authorized'):
        return
    
    users = state_manager.get_all_users()
    total_users = len(users)
    pro_users = sum(1 for u in users.values() if u['tier'] == 'pro')
    
    import docker
    client = docker.from_env()
    containers = client.containers.list()
    active_containers = len([c for c in containers if c.name.startswith("brahmos_cont_")])
    
    text = f"""📊 <b>Global System Stats</b>
━━━━━━━━━━━━━━━━━━━━━━
👤 <b>Total Users:</b> {total_users}
💎 <b>Pro Users:</b> {pro_users}
🐳 <b>Active Containers:</b> {active_containers}
⚙️ <b>Server Identity:</b> <code>{config.VPS_LOGIN}</code>

<i>Monitoring system performance...</i>"""
    bot.reply_to(message, text)

@bot.message_handler(commands=['admincmd', 'adminhelp'])
def admin_help_command(message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    help_text = """👑 <b>Admin Intelligence Manual</b>
━━━━━━━━━━━━━━━━━━━━━━
Master your VPS infrastructure with these commands:

<b>👤 User Management</b>
• <code>/addpremium &lt;user_id&gt; &lt;days&gt; [pro/max]</code> - Grant access.
• <code>/rempremium &lt;user_id&gt;</code> - Revoke PRO access.
• <code>/listusers</code> - Audit all users and their files.

<b>📊 System Oversight</b>
• <code>/stats</code> - View global system usage.
• <code>/admin</code> or <code>/addcmd</code> - Open the UI Control Panel.

<i>Use these tools responsibly to manage BrahMos Cloud.</i>"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['addcmd', 'admin'])
def addcmd_admin(message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    text = "👑 <b>Administrative Control Panel</b>\n━━━━━━━━━━━━━━━━━━━━━━\nSelect an audit or management tool below:"
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("📋 List All Users", callback_data="admin_list_users"),
               types.InlineKeyboardButton("📊 System Stats", callback_data="admin_view_stats"))
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_list_users")
def admin_list_users_callback(call):
    bot.answer_callback_query(call.id)
    call.message.admin_authorized = True
    list_users_admin(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_view_stats")
def admin_view_stats_callback(call):
    bot.answer_callback_query(call.id)
    call.message.admin_authorized = True
    stats_command_admin(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "verify_member")
def verify_member_callback(call):
    if check_membership(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Access Granted!")
        start_command(call, edit=True)
    else:
        bot.answer_callback_query(call.id, "❌ Verification Failed!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("manage_"))
def manage_app_callback(call, code_id=None):
    if code_id:
        codebase_id = code_id
    else:
        codebase_id = call.data.replace("manage_", "")
        
    user_id = call.from_user.id
    user_state = state_manager.get_user(user_id)
    proj = state_manager.get_container_by_codebase(user_id, codebase_id)
    
    if not proj:
        return bot.answer_callback_query(call.id, "❌ Project not found.", show_alert=True)
    
    container_id = proj['container_id']
    status = proj['status'].capitalize()
    status_emoji = "🟢" if proj['status'] == 'running' else "🔴"
    
    # Fetch real-time RAM usage & Runtime
    ram_usage_text = "N/A"
    ram_left_text = "N/A"
    runtime_text = "Offline"
    
    if proj['status'] == 'running':
        try:
            container = shell_worker.client.containers.get(container_id)
            
            # Runtime calculation
            from datetime import datetime
            started_at = container.attrs['State']['StartedAt']
            # Convert ISO 8601 to datetime (handling Z and sub-seconds)
            start_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            uptime = datetime.now(start_dt.tzinfo) - start_dt
            
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            if uptime.days > 0:
                runtime_text = f"{uptime.days}d {hours}h {minutes}m"
            else:
                runtime_text = f"{hours}h {minutes}m {seconds}s"

            # RAM stats
            stats = container.stats(stream=False)
            usage_bytes = stats['memory_stats'].get('usage', 0)
            usage_mb = usage_bytes / (1024 * 1024)
            
            is_admin = (user_id == config.ADMIN_ID)
            if is_admin:
                ram_usage_text = f"{usage_mb:.2f} MB"
                ram_left_text = "Unlimited"
            else:
                limits = subscription_manager.get_limits(user_state)
                total_ram = limits['ram']
                ram_usage_text = f"{usage_mb:.2f} / {total_ram} MB"
                ram_left_text = f"{max(0, total_ram - usage_mb):.2f} MB"
        except Exception:
            ram_usage_text = "Error fetching stats"
            runtime_text = "Unknown"

    text = f"""🛠 <b>Manage Project: {proj['project_name']}</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>Status:</b> {status} {status_emoji}
<b>Runtime:</b> <code>{runtime_text}</code>
<b>Project ID:</b> <code>{codebase_id}</code>
<b>Container ID:</b> <code>{container_id[:12]}</code>

⚡ <b>Resources:</b>
• <b>RAM Used:</b> <code>{ram_usage_text}</code>
• <b>RAM Left:</b> <code>{ram_left_text}</code>

Choose an action below to control your application."""

    markup = types.InlineKeyboardMarkup()
    if proj['status'] == 'running':
        btn_action = types.InlineKeyboardButton("🛑 Stop", callback_data=f"stop_{codebase_id}")
    else:
        btn_action = types.InlineKeyboardButton("▶️ Start", callback_data=f"start_{codebase_id}")
        
    btn_redeploy = types.InlineKeyboardButton("🔄 Redeploy", callback_data=f"redeploy_{codebase_id}")
    btn_delete = types.InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{codebase_id}")
    btn_logs = types.InlineKeyboardButton("📋 View Logs", callback_data=f"logs_{codebase_id}")
    btn_rename = types.InlineKeyboardButton("✏️ Rename", callback_data=f"rename_{codebase_id}")
    btn_domain = types.InlineKeyboardButton("🌐 Custom Domain", callback_data=f"domain_{codebase_id}")
    btn_back = types.InlineKeyboardButton("⬅️ Back to My Apps", callback_data="my_apps")
    
    markup.row(btn_action, btn_redeploy)
    markup.row(btn_logs, btn_delete)
    markup.row(btn_rename, btn_domain)
    markup.row(btn_back)
    
    try:
        bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.message_handler(commands=['stop'])
def stop_command_manual(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "Usage: /stop [app_id]")
    
    app_id = args[1]
    user_id = message.from_user.id
    proj = state_manager.get_container_by_codebase(user_id, app_id)
            
    if not proj:
        return bot.reply_to(message, "❌ Application not found.")
        
    if shell_worker.stop_container(proj['container_id']):
        state_manager.update_container_status(proj['container_id'], "stopped")
        bot.reply_to(message, f"✅ Application <code>{app_id}</code> has been stopped.")
    else:
        bot.reply_to(message, "❌ Failed to stop container.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def delete_app_callback(call):
    codebase_id = call.data.replace("delete_", "")
    user_id = call.from_user.id
    proj = state_manager.get_container_by_codebase(user_id, codebase_id)
    
    if not proj:
        return bot.answer_callback_query(call.id, "❌ Project not found.", show_alert=True)
        
    bot.answer_callback_query(call.id, "🗑 Deleting container and files...")
    
    if shell_worker.remove_container_physical(proj['container_id']):
        path = os.path.join(shell_worker.STORAGE_BASE, str(user_id), codebase_id)
        import shutil
        if os.path.exists(path):
            shutil.rmtree(path)
                
        state_manager.remove_container(proj['container_id'])
        bot.answer_callback_query(call.id, "✅ Application deleted successfully.", show_alert=True)
        my_apps_callback(call)
    else:
        bot.answer_callback_query(call.id, "❌ Failed to delete container.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("stop_"))
def stop_app_callback(call):
    codebase_id = call.data.replace("stop_", "")
    user_id = call.from_user.id
    proj = state_manager.get_container_by_codebase(user_id, codebase_id)
    
    if not proj:
        return bot.answer_callback_query(call.id, "❌ Project not found.", show_alert=True)
        
    bot.answer_callback_query(call.id, "⌛ Stopping container...")
    
    if shell_worker.stop_container(proj['container_id']):
        state_manager.update_container_status(proj['container_id'], "stopped")
        bot.answer_callback_query(call.id, "✅ Application stopped.", show_alert=True)
        manage_app_callback(call, code_id=codebase_id)
    else:
        bot.answer_callback_query(call.id, "❌ Failed to stop container.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("start_"))
def start_app_callback(call):
    codebase_id = call.data.replace("start_", "")
    user_id = call.from_user.id
    proj = state_manager.get_container_by_codebase(user_id, codebase_id)
    
    if not proj:
        return bot.answer_callback_query(call.id, "❌ Project not found.", show_alert=True)
        
    bot.answer_callback_query(call.id, "⌛ Starting container...")
    
    if shell_worker.start_container(proj['container_id']):
        state_manager.update_container_status(proj['container_id'], "running")
        bot.answer_callback_query(call.id, "✅ Application started.", show_alert=True)
        manage_app_callback(call, code_id=codebase_id)
    else:
        bot.answer_callback_query(call.id, "❌ Failed to start container.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "back_start")
def back_start_callback(call):
    bot.answer_callback_query(call.id)
    start_command(call, edit=True)

@bot.callback_query_handler(func=lambda call: call.data == "help_menu")
def help_menu_callback(call):
    bot.answer_callback_query(call.id)
    help_text = """📖 <b>BrahMos Intelligence Manual</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>How to Deploy (Automatic CI/CD):</b>
1️⃣ <b>GitHub Repo:</b> Use <code>/deploy &lt;url&gt; [pat]</code> or just send the link.
2️⃣ <b>ZIP Archive:</b> Upload a <code>.zip</code> file with your code.
<i>The AI will scan for security, auto-generate setup files, and deploy instantly.</i>

<b>User Commands:</b>
• <code>/stop [id]</code> - Kill an active project.
• <code>/myplan</code> - View your current limits.
• <code>/myapps</code> - List all your projects.

<i>Need help? Contact Developer or join the Community.</i>"""
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⬅️ Back to Home", callback_data="back_start"))
    
    try:
        bot.edit_message_caption(help_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.message_handler(commands=['myapps', 'apps'])
def myapps_command(message):
    my_apps_callback(message)

@bot.message_handler(commands=['myplan', 'plan'])
def myplan_command(message):
    # For /plan command, show the plan comparison
    if message.text.startswith('/plan'):
        view_plans_callback(message)
    else:
        # For /myplan, show the current user's status
        account_info_callback(message)

@bot.callback_query_handler(func=lambda call: call.data == "my_apps")
def my_apps_callback(call):
    # Handle both message and callback objects
    is_callback = hasattr(call, 'message')
    user_id = call.from_user.id
    chat_id = call.message.chat.id if is_callback else call.chat.id
    message_id = call.message.message_id if is_callback else None

    if is_callback:
        bot.answer_callback_query(call.id)
        
    projects = state_manager.get_user_projects(user_id)
    
    text = f"""📁 <b>My Applications</b>
━━━━━━━━━━━━━━━━━━━━━━
Select a project to manage its status or deploy a new application.\n\n"""
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🚀 Deploy New App", callback_data="deploy_menu"))
    
    if not projects:
        text += "<i>No active deployments found.</i>"
    else:
        proj_buttons = []
        for proj in projects:
            status_emoji = "🟢" if proj['status'] == 'running' else "🔴"
            code_id = proj['codebase_id']
            proj_name = proj.get('project_name', f"Project-{code_id}")
            text += f"• {status_emoji} <b>{proj_name}</b> (<code>{code_id}</code>)\n"
            proj_buttons.append(types.InlineKeyboardButton(f"⚙️ {proj_name}", callback_data=f"manage_{code_id}"))

        
        # Grid layout: 2 buttons per row
        for i in range(0, len(proj_buttons), 2):
            if i + 1 < len(proj_buttons):
                markup.row(proj_buttons[i], proj_buttons[i+1])
            else:
                markup.row(proj_buttons[i])
                
    markup.row(types.InlineKeyboardButton("⬅️ Back to Home", callback_data="back_start"))
    
    try:
        if is_callback:
            try:
                bot.edit_message_caption(text, chat_id, message_id, reply_markup=markup)
            except Exception:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)
    except Exception as e:
        print(f"Error in my_apps view: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "account_info")
def account_info_callback(call):
    # Handle both message and callback objects
    is_callback = hasattr(call, 'message')
    user_id = call.from_user.id
    chat_id = call.message.chat.id if is_callback else call.chat.id
    message_id = call.message.message_id if is_callback else None

    if is_callback:
        bot.answer_callback_query(call.id)

    user_state = state_manager.get_user(user_id)
    projects = state_manager.get_user_projects(user_id)
    
    is_admin = (user_id == config.ADMIN_ID)
    tier = "👑 ADMIN" if is_admin else user_state.get("tier", "free").upper()
    active_bots = len(projects)
    ram_limit = "Unlimited" if is_admin else f"{subscription_manager.get_limits(user_state)['ram']}MB"
    disk_limit = "Unlimited" if is_admin else f"{subscription_manager.get_limits(user_state)['disk']}MB"
    
    expiry_text = ""
    if not is_admin and user_state.get("tier") in ["pro", "max"]:
        expiry = user_state.get("premium_expiry")
        if expiry:
            expiry_text = f"\n📅 <b>Expiry:</b> <code>{expiry}</code>"

    text = f"""👤 <b>Account Overview</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>User ID:</b> <code>{user_id}</code>
<b>Current Tier:</b> {tier}{expiry_text}

⚡ <b>Limits:</b>
• <b>RAM:</b> <code>{ram_limit}</code>
• <b>Disk:</b> <code>{disk_limit}</code>

📂 <b>Active Projects:</b> <code>{active_bots}</code>

⚠️ <b>Backup Policy:</b> <i>Always keep a local copy of your code. We are not liable for data loss during maintenance or system errors.</i>

<i>{"Full administrative access granted." if is_admin else "Need more power? Contact the developer for a Pro upgrade."}</i>"""
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("💎 Premium Plans", callback_data="view_plans"))
    markup.row(types.InlineKeyboardButton("⬅️ Back to Home", callback_data="back_start"))
    
    try:
        if is_callback:
            try:
                bot.edit_message_caption(text, chat_id, message_id, reply_markup=markup)
            except Exception:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)
    except Exception as e:
        print(f"Error in account info view: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "view_plans")
def view_plans_callback(call):
    # Handle both message and callback objects
    is_callback = hasattr(call, 'message')
    chat_id = call.message.chat.id if is_callback else call.chat.id
    message_id = call.message.message_id if is_callback else None

    if is_callback:
        bot.answer_callback_query(call.id)

    text = f"""💎 <b>BrahMos Cloud Premium</b>
━━━━━━━━━━━━━━━━━━━━━━
Upgrade your hosting experience with our powerful <b>PRO</b> & <b>MAX</b> tiers.

🆓 <b>FREE TIER:</b>
• <b>RAM:</b> {config.FREE_TIER_RAM}MB
• <b>Disk:</b> {config.FREE_TIER_DISK}MB
• <b>Max Projects:</b> 5
• <b>Price:</b> ₹0

🔥 <b>PRO TIER:</b>
• <b>RAM:</b> {config.PRO_TIER_RAM}MB
• <b>Disk:</b> {config.PRO_TIER_DISK}MB
• <b>Max Projects:</b> 10
• <b>Price:</b> ₹199

⚡ <b>MAX TIER:</b>
• <b>RAM:</b> {config.MAX_TIER_RAM}MB
• <b>Disk:</b> {config.MAX_TIER_DISK}MB
• <b>Max Projects:</b> 25
• <b>Price:</b> ₹499

<i>To upgrade, please contact the <a href="{config.DEV_LINK}">Developer</a> with your User ID.</i>"""
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⬅️ Back to Account", callback_data="account_info"))
    
    try:
        if is_callback:
            try:
                bot.edit_message_caption(text, chat_id, message_id, reply_markup=markup)
            except Exception:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)
    except Exception as e:
        print(f"Error in plans view: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "deploy_menu")
def deploy_menu_callback(call):
    bot.answer_callback_query(call.id)
    text = """🚀 <b>How to Deploy</b>
━━━━━━━━━━━━━━━━━━━━━━
To host your application on <b>BrahMos Cloud</b>, choose one of these methods:

1️⃣ <b>GitHub Repository:</b>
Send the command <code>/deploy &lt;url&gt; [pat]</code> or just send the public link.

2️⃣ <b>ZIP Archive:</b>
Upload a <code>.zip</code> file containing your project's source code.

<i>Our AI will automatically scan your files, create a <code>start.sh</code>, and deploy your container in seconds.</i>"""

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⬅️ Back", callback_data="back_start"))

    
    try:
        bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rename_"))
def rename_app_callback(call):
    codebase_id = call.data.replace("rename_", "")
    bot.answer_callback_query(call.id)
    
    msg = bot.reply_to(call.message, f"📝 <b>Rename Project:</b> <code>{codebase_id}</code>\n━━━━━━━━━━━━━━━━━━━━━━\nPlease send the new name for this project.")
    bot.register_next_step_handler(msg, set_new_name_step, codebase_id=codebase_id)

def set_new_name_step(message, codebase_id):
    new_name = message.text.strip()
    user_id = message.from_user.id
    
    proj = state_manager.get_container_by_codebase(user_id, codebase_id)
    if proj:
        if state_manager.update_project_name(proj['container_id'], new_name):
            bot.reply_to(message, f"✅ Project renamed to: <b>{escape_html(new_name)}</b>")
        else:
            bot.reply_to(message, "❌ Failed to rename project.")
    else:
        bot.reply_to(message, "❌ Project not found.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("logs_"))
def view_logs_callback(call):
    codebase_id = call.data.replace("logs_", "")
    user_id = call.from_user.id
    proj = state_manager.get_container_by_codebase(user_id, codebase_id)
    
    if not proj:
        return bot.answer_callback_query(call.id, "❌ Project not found.", show_alert=True)
        
    bot.answer_callback_query(call.id, "⌛ Fetching logs...")
    
    try:
        client = shell_worker.client
        container = client.containers.get(proj['container_id'])
        logs = container.logs(tail=20).decode("utf-8")
        
        if not logs:
            logs = "No recent logs found."
            
        text = f"📋 <b>Recent Logs ({codebase_id}):</b>\n<code>\n{logs}\n</code>"
        bot.send_message(call.message.chat.id, text)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("domain_"))
def custom_domain_callback(call):
    codebase_id = call.data.replace("domain_", "")
    bot.answer_callback_query(call.id)
    
    try:
        vps_ip = requests.get('https://api.ipify.org', timeout=5).text
    except Exception:
        vps_ip = "YOUR_VPS_IP"

    text = f"""🌐 <b>Connect Your Custom Domain</b>
━━━━━━━━━━━━━━━━━━━━━━
To point your own domain (e.g., <code>api.example.com</code>) to your project <b>{codebase_id}</b>, follow these steps:

1️⃣ <b>Configure DNS:</b>
Go to your domain provider (Cloudflare, Namecheap, etc.) and add an <b>A Record</b>:
• <b>Name:</b> your-subdomain (or @ for root)
• <b>Value:</b> <code>{vps_ip}</code>

2️⃣ <b>Secure with Cloudflare (Recommended):</b>
Enable the <b>Proxy (Orange Cloud)</b> in Cloudflare. This hides your VPS IP and protects you from DDoS attacks.

<i>Once pointed, contact the administrator to finalize the SSL/Nginx configuration for your domain.</i>"""
    
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("⬅️ Back", callback_data=f"manage_{codebase_id}"))
    
    try:
        bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("redeploy_"))
def redeploy_callback(call):
    codebase_id = call.data.replace("redeploy_", "")
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id, "🔄 Redeploying container...")
    
    # Get existing port
    db = state_manager.load_db()
    assigned_port = None
    for cont_id, data in db["containers"].items():
        if data["codebase_id"] == codebase_id:
            assigned_port = data.get("port")
            break
    
    success, new_container_id = shell_worker.rebuild_container(user_id, codebase_id, port=assigned_port)
    if success:
        # Update state manager
        for cont_id, data in list(db["containers"].items()):
            if data["codebase_id"] == codebase_id:
                state_manager.remove_container(cont_id)
                
        state_manager.add_container(user_id, new_container_id, codebase_id, port=assigned_port)
        bot.answer_callback_query(call.id, "✅ Application redeployed successfully.", show_alert=True)
        manage_app_callback(call, code_id=codebase_id)
    else:
        bot.answer_callback_query(call.id, f"❌ Failed to redeploy container.", show_alert=True)

if __name__ == "__main__":
    # Start Resource Watchdog
    threading.Thread(target=resource_watchdog.monitor_resources, daemon=True).start()
    
    # Start Webhook Listener (Run in background)
    threading.Thread(target=webhook_listener.start_listener, daemon=True).start()
    
    print("BrahMos Cloud Bot is starting...")
    bot.infinity_polling()
