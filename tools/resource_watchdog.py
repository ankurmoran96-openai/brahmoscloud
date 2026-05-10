import time
import docker
import configuration as config
from tools import state_manager
from utils import subscription_manager

client = docker.from_env()

def monitor_resources():
    while True:
        try:
            containers = client.containers.list()
            for container in containers:
                if not container.name.startswith("brahmos_cont_"):
                    continue
                
                # Get stats
                stats = container.stats(stream=False)
                
                # RAM Usage
                mem_usage = stats['memory_stats'].get('usage', 0) / (1024 * 1024) # MB
                
                # Find owner and tier
                # Name format: brahmos_cont_{user_id}_{codebase_id}
                parts = container.name.split("_")
                if len(parts) >= 4:
                    user_id = parts[2]
                    user_state = state_manager.get_user(user_id)
                    tier = user_state.get("tier", "free")
                    limits = subscription_manager.get_limits(tier)
                    
                    if mem_usage > limits["ram"]:
                        print(f"Container {container.name} exceeded RAM limit ({mem_usage:.2f}MB > {limits['ram']}MB). Killing...")
                        container.stop()
                        # Notify user logic can be added here (via bot instance)
                        
            time.sleep(10) # Check every 10 seconds
        except Exception as e:
            print(f"Watchdog error: {e}")
            time.sleep(5)
