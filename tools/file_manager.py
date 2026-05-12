import os
import shutil
import zipfile
import subprocess
import tempfile
import uuid

BASE_TEMP_DIR = os.path.join(os.path.dirname(__file__), '..', 'temp_deployments')
os.makedirs(BASE_TEMP_DIR, exist_ok=True)

def get_temp_dir():
    dir_name = str(uuid.uuid4())
    path = os.path.join(BASE_TEMP_DIR, dir_name)
    os.makedirs(path, exist_ok=True)
    return path

def extract_zip(zip_path, extract_to):
    extract_to = os.path.abspath(extract_to)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.infolist():
            target_path = os.path.abspath(os.path.join(extract_to, member.filename))
            if not target_path.startswith(extract_to):
                raise Exception(f"Potential Zip Slip attack detected: {member.filename}")
        zip_ref.extractall(extract_to)
    return extract_to

def clone_repo(repo_url, extract_to, pat=None):
    # Burn After Reading: PAT is injected into the URL for cloning and then forgotten
    if pat:
        # Format: https://<pat>@github.com/user/repo.git
        if "github.com" in repo_url and "://" in repo_url:
            parts = repo_url.split("://")
            auth_url = f"{parts[0]}://{pat}@{parts[1]}"
        else:
            auth_url = repo_url # Fallback if URL is weird
    else:
        auth_url = repo_url

    try:
        subprocess.run(['git', 'clone', auth_url, extract_to], check=True, capture_output=True)
        # Cleanup: Remove .git folder to prevent leak of credentials if they were cached
        git_folder = os.path.join(extract_to, '.git')
        if os.path.exists(git_folder):
            shutil.rmtree(git_folder)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Clone failed: {e.stderr.decode()}")
        return False

def cleanup_temp_dir(path):
    if os.path.exists(path) and path.startswith(BASE_TEMP_DIR):
        shutil.rmtree(path)
