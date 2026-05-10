import docker
import os
import shutil
import configuration as config

client = docker.from_env()

def create_dockerfile(directory):
    dockerfile_content = """
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
RUN chmod +x start.sh
CMD ["./start.sh"]
"""
    with open(os.path.join(directory, 'Dockerfile'), 'w') as f:
        f.write(dockerfile_content)

def deploy_project(user_id, directory, codebase_id):
    create_dockerfile(directory)
    
    image_tag = f"brahmos_{user_id}_{codebase_id}".lower()
    container_name = f"brahmos_cont_{user_id}_{codebase_id}".lower()
    
    try:
        # Build Image
        print(f"Building image {image_tag}...")
        image, logs = client.images.build(path=directory, tag=image_tag, rm=True)
        
        # Remove existing container if any
        try:
            old_container = client.containers.get(container_name)
            old_container.stop()
            old_container.remove()
        except docker.errors.NotFound:
            pass
            
        # Run Container
        # Note: We'll set limits in the watchdog or here
        print(f"Starting container {container_name}...")
        container = client.containers.run(
            image_tag,
            detach=True,
            name=container_name,
            mem_limit=f"{config.FREE_TIER_RAM}m", # Initial limit, watchdog will refine
            restart_policy={"Name": "always"}
        )
        
        return True, container.id
    except Exception as e:
        print(f"Deployment failed: {e}")
        return False, str(e)

def stop_container(container_id):
    try:
        container = client.containers.get(container_id)
        container.stop()
        container.remove()
        return True
    except Exception:
        return False
