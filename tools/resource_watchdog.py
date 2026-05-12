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
                
                # Disk Usage (Estimated from container size)
                # Note: Docker stats doesn't give disk I/O easily, but we can check the RW layer
                try:
                    container_info = client.api.inspect_container(container.id)
                    disk_usage = container_info.get('SizeRw', 0) / (1024 * 1024) # MB
                except Exception:
                    disk_usage = 0

                # Find owner and tier
                # Name format: brahmos_cont_{user_id}_{codebase_id}
                parts = container.name.split("_")
                if len(parts) >= 4:
                    user_id = parts[2]
                    user_state = state_manager.get_user(user_id)
                    limits = subscription_manager.get_limits(user_state)
                    
                    if mem_usage > limits["ram"]:
                        print(f"Container {container.name} exceeded RAM limit ({mem_usage:.2f}MB > {limits['ram']}MB). Killing...")
                        container.stop()
                    
                    if disk_usage > limits["disk"]:
                        print(f"Container {container.name} exceeded Disk limit ({disk_usage:.2f}MB > {limits['disk']}MB). Killing...")
                        container.stop()
                        
            time.sleep(60) # Check every 60 seconds to reduce Docker Daemon load
        except Exception as e:
            print(f"Watchdog error: {e}")
            time.sleep(30)
