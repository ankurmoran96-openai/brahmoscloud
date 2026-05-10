from tools import file_manager

def cleanup_deployment(temp_dir):
    """
    Cleans up the temporary extraction directory after deployment.
    """
    print(f"Garbage Collector: Cleaning up {temp_dir}")
    file_manager.cleanup_temp_dir(temp_dir)
