import requests
import json
import os
import configuration as config
from tools import state_manager

# --- AGENT 1: BASIC SEC & DISCOVERY ---
AGENT1_PROMPT = """
You are Agent 1: The Gateway Scout.
1. Perform a basic security check. If ANY malware, stresser, miner, or malicious intent is found, REJECT IMMEDIATELY.
2. If the code is perfectly clean, identify and extract the exact names of ALL configuration variables (API keys, ports, tokens, DB URLs) found in the code.
3. Identify the project type (bot, web_app, api).

Call `reject_malware` if malicious.
Call `discovery_success` if clean, providing the exact variable names.
"""

# --- AGENT 2: NORMAL SECURITY CHECK ---
AGENT2_NORMAL_PROMPT = """
You are Agent 2: Severity Layer 2 (Standard).
You receive the codebase and the variables extracted by Agent 1.
Your job is to do a normal but thorough security check across all code separately.
1. Ensure no hidden malicious logic was missed by Agent 1.
2. Verify the variable names.
If ANYTHING suspicious is found, call `flag_and_reject`.
If verified clean, call `audit_verified` and pass along the verified variable names.
"""

# --- AGENT 2: DEEP SECURITY CHECK ---
AGENT2_DEEP_PROMPT = """
You are Agent 2: Severity Layer 2 (Deep Analysis).
The user deploying this is FLAGGED AS SUSPICIOUS. 
You must do a 10x deeper analysis on every single file. Look for obfuscation, container escapes, reverse shells, and hidden malware.
If you find ANY hint of danger, call `flag_and_reject`.
If absolutely certain it is safe, call `audit_verified` and pass along the verified variable names.
"""

# --- AGENT 3: DEPLOYMENT ARCHITECT ---
AGENT3_PROMPT = """
You are Agent 3: The Deployment Architect.
You receive the verified variable names from Agent 2.
1. Create a `.env` file using EXACTLY those variable names. (Provide placeholder values or extract them if present).
2. Create `requirements.txt` strictly based on the structure and imports. 
   **BE CAREFUL OF HALLUCINATIONS**. Map these strictly:
   - telebot -> pyTelegramBotAPI
   - discord -> discord.py
   - PIL -> Pillow
   - cv2 -> opencv-python
3. Create `start.sh`.

Call `finalize_deployment` with the exact text contents.
"""

def call_ai(prompt, tools, tool_choice="required"):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.AI_API_KEY}"
    }
    payload = {
        "model": config.AI_MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Analyze the codebase according to your instructions."}
        ],
        "tools": tools,
        "tool_choice": tool_choice
    }
    try:
        response = requests.post(config.AI_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message'].get('tool_calls')
    except Exception as e:
        print(f"AI Call failed: {e}")
        return None

def orchestrate_deployment(user_id, file_path_list, code_contents):
    # --- PHASE 1: AGENT 1 (Basic Check & Extraction) ---
    tools1 = [
        {
            "type": "function",
            "function": {
                "name": "reject_malware",
                "description": "Reject immediately if ANY malware is found.",
                "parameters": { "type": "object", "properties": { "reason": { "type": "string" } }, "required": ["reason"] }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "discovery_success",
                "description": "Code passes basic check. Provide extracted variables.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "variables": { "type": "array", "items": { "type": "string" } },
                        "project_type": { "type": "string", "enum": ["bot", "web_app", "api"] },
                        "internal_port": { "type": "integer" }
                    },
                    "required": ["variables", "project_type"]
                }
            }
        }
    ]
    
    prompt1 = f"{AGENT1_PROMPT}\n\nFiles: {json.dumps(file_path_list)}\nCode: {json.dumps(code_contents)}"
    calls1 = call_ai(prompt1, tools1)
    
    if not calls1: return {"success": False, "reason": "Agent 1 failed."}
    call1 = calls1[0]
    args1 = json.loads(call1['function']['arguments'])
    
    if call1['function']['name'] == 'reject_malware':
        return {"success": False, "reason": f"Agent 1 Rejected: {args1['reason']}"}
    
    discovered_vars = args1.get('variables', [])
    project_type = args1.get('project_type', 'bot')
    internal_port = args1.get('internal_port', 8000)

    # --- PHASE 2: AGENT 2 (Severity Layer 2) ---
    is_suspicious = state_manager.is_user_suspicious(user_id)
    
    tools2 = [
        {
            "type": "function",
            "function": {
                "name": "flag_and_reject",
                "description": "Found hidden threat. Reject and flag user.",
                "parameters": { "type": "object", "properties": { "reason": { "type": "string" } }, "required": ["reason"] }
            }
        },
        {
            "type": "function",
            "function": { 
                "name": "audit_verified", 
                "description": "Code is 100% verified. Passing variable names to Agent 3.", 
                "parameters": { 
                    "type": "object", 
                    "properties": {
                        "verified_variables": { "type": "array", "items": { "type": "string" } }
                    },
                    "required": ["verified_variables"]
                } 
            }
        }
    ]
    
    if is_suspicious:
        # Deep Analysis
        prompt2 = f"{AGENT2_DEEP_PROMPT}\n\nAgent 1 Variables: {json.dumps(discovered_vars)}\nFiles: {json.dumps(file_path_list)}\nCode: {json.dumps(code_contents)}"
    else:
        # Normal Check Separately
        prompt2 = f"{AGENT2_NORMAL_PROMPT}\n\nAgent 1 Variables: {json.dumps(discovered_vars)}\nFiles: {json.dumps(file_path_list)}\nCode: {json.dumps(code_contents)}"
        
    calls2 = call_ai(prompt2, tools2)
    
    if not calls2: return {"success": False, "reason": "Agent 2 failed."}
    call2 = calls2[0]
    args2 = json.loads(call2['function']['arguments'])
    
    if call2['function']['name'] == 'flag_and_reject':
        reason = args2.get('reason', 'Security violation detected in Layer 2.')
        state_manager.flag_suspicious_user(user_id) # Flag the user
        return {"success": False, "reason": f"Agent 2 Security Alert (User Flagged): {reason}"}

    final_vars = args2.get('verified_variables', discovered_vars)

    # --- PHASE 3: AGENT 3 (Deployment Architect) ---
    tools3 = [
        {
            "type": "function",
            "function": {
                "name": "finalize_deployment",
                "description": "Generate final deployment files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "requirements_txt": { "type": "string", "description": "Ensure exact mapping. No hallucinations." },
                        "env_file": { "type": "string", "description": "Built from variables passed by Agent 2." },
                        "start_sh": { "type": "string" }
                    },
                    "required": ["requirements_txt", "env_file", "start_sh"]
                }
            }
        }
    ]
    
    prompt3 = f"{AGENT3_PROMPT}\n\nVariables from Agent 2: {json.dumps(final_vars)}\nCode for imports: {json.dumps(code_contents)}"
    calls3 = call_ai(prompt3, tools3)
    
    if not calls3: return {"success": False, "reason": "Agent 3 failed."}
    args3 = json.loads(calls3[0]['function']['arguments'])
    
    return {
        "success": True,
        "project_type": project_type,
        "internal_port": internal_port,
        "requirements_txt": args3.get('requirements_txt', ''),
        "env_file": args3.get('env_file', ''),
        "start_sh": args3.get('start_sh', '')
    }

def audit_commit_change(user_id, file_name, new_code):
    """
    Commit Security Layer (Gemini CLI Requirement)
    Displayed and enforced during CI/CD push.
    """
    is_suspicious = state_manager.is_user_suspicious(user_id)
    
    prompt = f"""
You are the Commit Security Auditor.
A user is pushing a change to their deployment.
User Status: {"SUSPICIOUS" if is_suspicious else "Normal"}
File: {file_name}
Code:
{new_code}

If there is anything harmful = reject.
If not harmful = granted.
"""

    tools = [
        {
            "type": "function",
            "function": { "name": "grant_commit", "parameters": { "type": "object", "properties": {} } }
        },
        {
            "type": "function",
            "function": {
                "name": "reject_commit",
                "parameters": {
                    "type": "object",
                    "properties": { "reason": { "type": "string" } },
                    "required": ["reason"]
                }
            }
        }
    ]
    
    calls = call_ai(prompt, tools)
    if not calls: return {"safe": False, "reason": "Commit Auditor failed to respond."}
    
    call = calls[0]
    if call['function']['name'] == 'grant_commit':
        return {"safe": True, "reason": "Commit verified as safe."}
    else:
        args = json.loads(call['function']['arguments'])
        return {"safe": False, "reason": args.get("reason", "Harmful commit detected.")}

def read_relevant_files(directory):
    relevant_extensions = ('.py', '.js', '.ts', '.sh', '.json', '.txt', '.yaml', '.yml')
    code_contents = {}
    file_list = []
    
    for root, dirs, files in os.walk(directory):
        if '.git' in dirs: dirs.remove('.git')
        for file in files:
            file_path = os.path.relpath(os.path.join(root, file), directory)
            file_list.append(file_path)
            
            if file.endswith(relevant_extensions) and len(code_contents) < 15:
                try:
                    full_path = os.path.join(root, file)
                    with open(full_path, 'r', errors='ignore') as f:
                        code_contents[file_path] = f.read(2000)
                except Exception:
                    pass
                    
    return file_list, code_contents
