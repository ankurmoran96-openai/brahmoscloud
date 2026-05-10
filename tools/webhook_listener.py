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
    if payload.get("ref") == "refs/heads/main":
        repo_url = payload["repository"]["clone_url"]
        print(f"CI/CD: Push detected for {user_id}/{codebase_id}. Redeploying...")
        
        # Trigger redeployment logic (Simplified for now)
        # In a real scenario, we'd need to re-clone, re-analyze, and re-run shell_worker.
        # This listener should ideally talk to a task queue or the main bot process.
        
    return {"status": "received"}

def start_listener():
    uvicorn.run(app, host="0.0.0.0", port=8000)
