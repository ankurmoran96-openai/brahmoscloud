import telebot
import html

def clean_logs(logs_str):
    if not logs_str:
        return ""
    lines = logs_str.strip().split('\n')
    seen = set()
    cleaned = []
    for line in lines:
        if line.strip() == "" or line not in seen:
            if line.strip() != "":
                seen.add(line)
            cleaned.append(line)
    return '\n'.join(cleaned[-15:])

def format_error_log(error_msg, log_content=None):
    formatted = f"❌ <b>Deployment Error</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    formatted += f"<b>Message:</b> <code>{html.escape(str(error_msg))}</code>\n\n"
    
    if log_content:
        formatted += "Your project has multiple errors, please fix:\n"
        formatted += f"```Error Log\n{html.escape(clean_logs(str(log_content)))}\n```"
    
    return formatted

def send_error_to_user(bot, chat_id, error_msg, log_content=None):
    text = format_error_log(error_msg, log_content)
    try:
        bot.send_message(chat_id, text, parse_mode='HTML')
    except Exception as e:
        print(f"Failed to send error message: {e}")
