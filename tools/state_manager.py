import json
import os

DB_FILE = os.path.join(os.path.dirname(__file__), '..', 'database.json')

def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "containers": {}}
    with open(DB_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"users": {}, "containers": {}}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user(user_id):
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str not in db["users"]:
        # Initialize default user state
        db["users"][user_id_str] = {
            "tier": "free",
            "active_bots": [],
            "resource_usage": {"ram": 0, "disk": 0}
        }
        save_db(db)
    return db["users"][user_id_str]

def update_user_tier(user_id, tier):
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str in db["users"]:
        db["users"][user_id_str]["tier"] = tier
        save_db(db)
        return True
    return False

def add_container(user_id, container_id, codebase_id):
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str not in db["users"]:
        get_user(user_id) # Initialize
        db = load_db()
    
    db["users"][user_id_str]["active_bots"].append(container_id)
    db["containers"][container_id] = {
        "user_id": user_id,
        "codebase_id": codebase_id,
        "status": "running"
    }
    save_db(db)

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
