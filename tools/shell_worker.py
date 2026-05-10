import docker
import os
import shutil
import configuration as config

client = docker.from_env()

def create_dockerfile(directory):
    dockerfile_content = """
FROM python:3.10-slim
# Create a non-root user
RUN groupadd -r brahmos && useradd -r -g brahmos brahmos
WORKDIR /app
COPY . .
RUN chown -R brahmos:brahmos /app
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi
RUN chmod +x start.sh
USER brahmos
CMD ["./start.sh"]
"""
    with open(os.path.join(directory, 'Dockerfile'), 'w') as f:
        f.write(dockerfile_content)

STORAGE_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'storage'))

def deploy_project(user_id, directory, codebase_id):
    # 1. Prepare persistent storage
    user_storage = os.path.join(STORAGE_BASE, str(user_id), codebase_id)
    os.makedirs(user_storage, exist_ok=True)
    
    # 2. Copy files to persistent storage (excluding Dockerfile if we generate it there)
    for item in os.listdir(directory):
        s = os.path.join(directory, item)
        d = os.path.join(user_storage, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

    create_dockerfile(user_storage)
    
    image_tag = f"brahmos_{user_id}_{codebase_id}".lower()
    container_name = f"brahmos_cont_{user_id}_{codebase_id}".lower()
    
    try:
        # Build Image using the storage directory
        print(f"Building image {image_tag}...")
        image, logs = client.images.build(path=user_storage, tag=image_tag, rm=True)
        
        # Remove existing container if any
        try:
            old_container = client.containers.get(container_name)
            old_container.stop()
            old_container.remove()
        except docker.errors.NotFound:
            pass
            
        # Run Container
        print(f"Starting container {container_name}...")
        container = client.containers.run(
            image_tag,
            detach=True,
            name=container_name,
            mem_limit=f"{config.FREE_TIER_RAM}m",
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

def rebuild_container(user_id, codebase_id):
    user_storage = os.path.join(STORAGE_BASE, str(user_id), codebase_id)
    if not os.path.exists(user_storage):
        return False, "Project storage not found"
        
    image_tag = f"brahmos_{user_id}_{codebase_id}".lower()
    container_name = f"brahmos_cont_{user_id}_{codebase_id}".lower()
    
    try:
        print(f"Rebuilding image {image_tag}...")
        client.images.build(path=user_storage, tag=image_tag, rm=True)
        
        try:
            old_container = client.containers.get(container_name)
            old_container.stop()
            old_container.remove()
        except docker.errors.NotFound:
            pass
            
        print(f"Starting container {container_name}...")
        container = client.containers.run(
            image_tag,
            detach=True,
            name=container_name,
            mem_limit=f"{config.FREE_TIER_RAM}m",
            restart_policy={"Name": "always"}
        )
        return True, container.id
    except Exception as e:
        return False, str(e)

