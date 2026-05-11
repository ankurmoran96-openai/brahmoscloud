from fastapi import FastAPI, Request, HTTPException
import uvicorn
import hmac
import hashlib
import os
from tools import shell_worker, state_manager, file_manager, ai_agent, garbage_collector

app = FastAPI()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "supersecret")

def verify_signature(payload_body, signature_header):
    if not signature_header:
        return False
    sha_name, signature = signature_header.split('=')
    if sha_name != 'sha1':
        return False
    mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload_body, digestmod=hashlib.sha1)
    return hmac.compare_digest(mac.hexdigest(), signature)

@app.post("/webhook/{user_id}/{codebase_id}")
async def github_webhook(user_id: str, codebase_id: str, request: Request):
    # Verify GitHub Signature
    signature = request.headers.get('X-Hub-Signature')
    body = await request.body()
    
    if not verify_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    
    # Check if it's a push event
    if payload.get("ref") in ["refs/heads/main", "refs/heads/master"]:
        print(f"CI/CD: Push detected for {user_id}/{codebase_id}. Redeploying...")
        
        user_storage = os.path.join(shell_worker.STORAGE_BASE, str(user_id), codebase_id)
        if os.path.exists(user_storage):
            import subprocess
            try:
                # Pull latest changes
                subprocess.run(['git', 'pull'], cwd=user_storage, check=True)
            except Exception as e:
                print(f"Git pull failed: {e}")
                
            # Get port if it exists
            db = state_manager.load_db()
            assigned_port = None
            for cont_id, data in db["containers"].items():
                if data["codebase_id"] == codebase_id:
                    assigned_port = data.get("port")
                    break
            
            success, new_container_id = shell_worker.rebuild_container(user_id, codebase_id, port=assigned_port)
            if success:
                # Update state manager to point to the new container ID
                for cont_id, data in list(db["containers"].items()):
                    if data["codebase_id"] == codebase_id:
                        state_manager.remove_container(cont_id)
                state_manager.add_container(user_id, new_container_id, codebase_id)
                
                # Notify user
                import telebot
                import configuration as config
                try:
                    bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode='HTML')
                    bot.send_message(user_id, f"🔄 <b>Auto-Redeploy Complete!</b>\n━━━━━━━━━━━━━━━━━━━━━━\nYour project <code>{codebase_id}</code> was successfully updated via GitHub Webhook. 🚀")
                except Exception as e:
                    print(f"Failed to send webhook notification: {e}")
        
    return {"status": "received"}

def start_listener():
    uvicorn.run(app, host="0.0.0.0", port=8000)
