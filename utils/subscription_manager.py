import configuration as config

TIERS = {
    "free": {
        "ram": config.FREE_TIER_RAM,
        "disk": config.FREE_TIER_DISK,
        "max_bots": 1
    },
    "pro": {
        "ram": config.PRO_TIER_RAM,
        "disk": config.PRO_TIER_DISK,
        "max_bots": 5
    }
}

def can_deploy(user_state):
    tier = user_state.get("tier", "free")
    limits = TIERS.get(tier, TIERS["free"])
    
    if len(user_state.get("active_bots", [])) >= limits["max_bots"]:
        return False, f"You have reached the maximum number of active bots for the {tier.upper()} tier ({limits['max_bots']})."
    
    return True, "Ready to deploy."

def get_limits(tier):
    return TIERS.get(tier, TIERS["free"])
