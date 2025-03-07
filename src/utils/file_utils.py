import os
import json
import shutil
from datetime import datetime

def ensure_dir(directory):
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path
        
    Returns:
        bool: Success or failure
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except OSError as e:
        print(f"Error creating directory {directory}: {e}")
        return False

def save_json(data, file_path, indent=2):
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        file_path: Path to save to
        indent: JSON indentation level
        
    Returns:
        bool: Success or failure
    """
    try:
        # Ensure directory exists
        directory = os.path.dirname(file_path)
        ensure_dir(directory)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=indent)
        return True
    except (IOError, TypeError) as e:
        print(f"Error saving JSON to {file_path}: {e}")
        return False

def load_json(file_path, default=None):
    """
    Load data from a JSON file.
    
    Args:
        file_path: Path to load from
        default: Default value if file doesn't exist or is invalid
        
    Returns:
        Data from the file or default value
    """
    if not os.path.exists(file_path):
        return default
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading JSON from {file_path}: {e}")
        return default

def backup_file(file_path, backup_dir=None):
    """
    Create a backup of a file.
    
    Args:
        file_path: Path to the file to backup
        backup_dir: Directory to store backups (defaults to file's directory + '/backups')
        
    Returns:
        str or None: Path to the backup file, or None on failure
    """
    if not os.path.exists(file_path):
        return None
    
    try:
        # Get file components
        file_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        file_base, file_ext = os.path.splitext(file_name)
        
        # Determine backup directory
        if not backup_dir:
            backup_dir = os.path.join(file_dir, "backups")
        
        # Ensure backup directory exists
        ensure_dir(backup_dir)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_base}_{timestamp}{file_ext}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        # Copy the file
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    except (IOError, OSError) as e:
        print(f"Error backing up {file_path}: {e}")
        return None

def list_files(directory, extension=None):
    """
    List files in a directory, optionally filtered by extension.
    
    Args:
        directory: Directory to list files from
        extension: Optional file extension to filter by
        
    Returns:
        list: List of file paths
    """
    if not os.path.exists(directory):
        return []
    
    try:
        files = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
            if os.path.isfile(item_path):
                if extension is None or item.endswith(extension):
                    files.append(item_path)
        
        return files
    
    except OSError as e:
        print(f"Error listing files in {directory}: {e}")
        return []

def create_or_update_file(file_path, content, mode='w'):
    """
    Create or update a text file.
    
    Args:
        file_path: Path to the file
        content: Content to write
        mode: File mode ('w' for write, 'a' for append)
        
    Returns:
        bool: Success or failure
    """
    try:
        # Ensure directory exists
        directory = os.path.dirname(file_path)
        ensure_dir(directory)
        
        with open(file_path, mode) as f:
            f.write(content)
        return True
    
    except IOError as e:
        print(f"Error writing to {file_path}: {e}")
        return False

def create_script_file(script_name, content):
    """
    Create a new script file with the given content.
    Especially useful for Lachesis to extend herself.
    
    Args:
        script_name: Name of the script
        content: Script content
        
    Returns:
        str or None: Path to the created script, or None on failure
    """
    # Define safe script directory
    script_dir = os.path.join("data", "scripts")
    ensure_dir(script_dir)
    
    # Sanitize script name
    safe_name = "".join(c for c in script_name if c.isalnum() or c in "_-").lower()
    if not safe_name.endswith(".py"):
        safe_name += ".py"
    
    script_path = os.path.join(script_dir, safe_name)
    
    # Create the script file
    if create_or_update_file(script_path, content):
        return script_path
    
    return None

def read_file(file_path, default=None):
    """
    Read content from a text file.
    
    Args:
        file_path: Path to the file
        default: Default value if file doesn't exist or can't be read
        
    Returns:
        str: File content or default value
    """
    if not os.path.exists(file_path):
        return default
    
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except IOError as e:
        print(f"Error reading {file_path}: {e}")
        return default
