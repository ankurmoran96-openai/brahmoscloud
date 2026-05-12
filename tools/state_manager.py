import json
import os
import threading
from datetime import datetime, timedelta

db_lock = threading.Lock()

DB_FILE = os.path.join(os.path.dirname(__file__), '..', 'database.json')

SUSPICIOUS_FILE = os.path.join(os.path.dirname(__file__), '..', 'utils', 'suspicious_user.json')

def load_suspicious():
    with db_lock:
        if not os.path.exists(SUSPICIOUS_FILE):
            os.makedirs(os.path.dirname(SUSPICIOUS_FILE), exist_ok=True)
            return []
        with open(SUSPICIOUS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

def save_suspicious(data):
    with db_lock:
        with open(SUSPICIOUS_FILE, 'w') as f:
            json.dump(data, f, indent=4)

def flag_suspicious_user(user_id):
    users = load_suspicious()
    if str(user_id) not in users:
        users.append(str(user_id))
        save_suspicious(users)
        return True
    return False

def is_user_suspicious(user_id):
    users = load_suspicious()
    return str(user_id) in users

def load_db():
    with db_lock:
        if not os.path.exists(DB_FILE):
            return {"users": {}, "containers": {}}
        with open(DB_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"users": {}, "containers": {}}

def save_db(data):
    with db_lock:
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)

def get_all_users():
    db = load_db()
    return db["users"]

def get_user(user_id):
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str not in db["users"]:
        # Initialize default user state
        db["users"][user_id_str] = {
            "tier": "free",
            "premium_expiry": None, # Date string or None
            "active_bots": [],
            "resource_usage": {"ram": 0, "disk": 0}
        }
        save_db(db)
    
    user = db["users"][user_id_str]
    # Handle legacy users without premium_expiry field
    if "premium_expiry" not in user:
        user["premium_expiry"] = None
        save_db(db)
        
    return user

def update_user_premium(user_id, days, tier="pro"):
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str not in db["users"]:
        get_user(user_id)
        db = load_db()
        
    if days > 0:
        expiry_date = datetime.now() + timedelta(days=days)
        db["users"][user_id_str]["tier"] = tier.lower()
        db["users"][user_id_str]["premium_expiry"] = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
    else:
        db["users"][user_id_str]["tier"] = "free"
        db["users"][user_id_str]["premium_expiry"] = None
        
    save_db(db)
    return True

def add_container(user_id, container_id, codebase_id, port=None, project_name=None):
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str not in db["users"]:
        get_user(user_id) # Initialize
        db = load_db()
    
    db["users"][user_id_str]["active_bots"].append(container_id)
    db["containers"][container_id] = {
        "user_id": user_id,
        "codebase_id": codebase_id,
        "project_name": project_name or f"Project-{codebase_id}",
        "status": "running",
        "port": port
    }
    save_db(db)

def update_project_name(container_id, new_name):
    db = load_db()
    if container_id in db["containers"]:
        db["containers"][container_id]["project_name"] = new_name
        save_db(db)
        return True
    return False

def get_next_available_port():
    db = load_db()
    assigned_ports = [c.get("port") for c in db["containers"].values() if c.get("port")]
    
    # Start range from 10000
    current_port = 10000
    while current_port in assigned_ports:
        current_port += 1
    
    return current_port

def get_user_projects(user_id):
    db = load_db()
    user_id_str = str(user_id)
    projects = []
    if user_id_str in db["users"]:
        for cont_id in db["users"][user_id_str]["active_bots"]:
            if cont_id in db["containers"]:
                proj = db["containers"][cont_id]
                proj["container_id"] = cont_id
                projects.append(proj)
    return projects

def get_container_info(container_id):
    db = load_db()
    return db["containers"].get(container_id)

def get_container_by_codebase(user_id, codebase_id):
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str in db["users"]:
        for cont_id in db["users"][user_id_str]["active_bots"]:
            if cont_id in db["containers"]:
                if db["containers"][cont_id]["codebase_id"] == codebase_id:
                    # Return info plus the actual container_id
                    info = db["containers"][cont_id]
                    info["container_id"] = cont_id
                    return info
    return None

def update_container_status(container_id, status):
    db = load_db()
    if container_id in db["containers"]:
        db["containers"][container_id]["status"] = status
        save_db(db)
        return True
    return False

def remove_container(container_id):
    db = load_db()
    if container_id in db["containers"]:
        user_id = str(db["containers"][container_id]["user_id"])
        if user_id in db["users"]:
            if container_id in db["users"][user_id]["active_bots"]:
                db["users"][user_id]["active_bots"].remove(container_id)
        del db["containers"][container_id]
        save_db(db)
        return True
    return False
