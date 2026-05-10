import configuration as config
from datetime import datetime

TIERS = {
    "free": {
        "ram": config.FREE_TIER_RAM,
        "disk": config.FREE_TIER_DISK,
        "max_bots": 5
    },
    "pro": {
        "ram": config.PRO_TIER_RAM,
        "disk": config.PRO_TIER_DISK,
        "max_bots": 10
    }
}

def is_premium_active(user_state):
    expiry = user_state.get("premium_expiry")
    if not expiry:
        return False
        
    try:
        expiry_dt = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
        return datetime.now() < expiry_dt
    except Exception:
        return False

def can_deploy(user_state, is_admin=False):
    if is_admin:
        return True, "Admin access granted."
        
    tier = user_state.get("tier", "free")
    
    # Check for premium expiry
    if tier == "pro" and not is_premium_active(user_state):
        return False, "Your premium subscription has expired. Please renew to deploy more bots."
        
    limits = TIERS.get(tier, TIERS["free"])
    
    if len(user_state.get("active_bots", [])) >= limits["max_bots"]:
        return False, f"You have reached the maximum number of active bots for the {tier.upper()} tier ({limits['max_bots']})."
    
    return True, "Ready to deploy."

def get_limits(user_state):
    tier = user_state.get("tier", "free")
    if tier == "pro" and not is_premium_active(user_state):
        tier = "free"
    return TIERS.get(tier, TIERS["free"])
