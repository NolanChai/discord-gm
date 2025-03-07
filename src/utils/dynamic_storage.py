"""
Dynamic storage utilities for Lachesis bot.

This module provides utilities for creating and managing dynamic files and data.
"""

import os
import json
import time
import logging
import importlib.util
import sys
from typing import Dict, Any, Optional, List, Callable, Union

logger = logging.getLogger("lachesis.dynamic_storage")

class DynamicStorage:
    """
    Manager for dynamic file creation and storage.
    
    Allows the bot to create new data files, modules, or functions on the fly
    to adapt to new requirements.
    """
    
    def __init__(self, data_dir: str):
        """
        Initialize the dynamic storage manager.
        
        Args:
            data_dir (str): Base directory for storing dynamic data
        """
        self.base_dir = data_dir
        self.modules_dir = os.path.join(data_dir, "modules")
        self.data_dir = os.path.join(data_dir, "data")
        
        # Ensure directories exist
        os.makedirs(self.modules_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Track loaded modules
        self.loaded_modules = {}
    
    def create_json_file(self, filename: str, data: Dict[str, Any]) -> str:
        """
        Create a new JSON data file.
        
        Args:
            filename (str): Filename (without .json extension)
            data (Dict): Data to store
            
        Returns:
            str: Path to the created file
        """
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        file_path = os.path.join(self.data_dir, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created dynamic JSON file: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Error creating JSON file {filename}: {e}")
            return ""
    
    def read_json_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Read a JSON data file.
        
        Args:
            filename (str): Filename (without .json extension)
            
        Returns:
            Optional[Dict]: Data from the file or None if error
        """
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        file_path = os.path.join(self.data_dir, filename)
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"JSON file does not exist: {file_path}")
                return None
        except Exception as e:
            logger.error(f"Error reading JSON file {filename}: {e}")
            return None
    
    def update_json_file(self, filename: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing JSON data file.
        
        Args:
            filename (str): Filename (without .json extension)
            updates (Dict): Data updates to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        file_path = os.path.join(self.data_dir, filename)
        
        try:
            data = {}
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Apply updates
            data.update(updates)
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Updated dynamic JSON file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error updating JSON file {filename}: {e}")
            return False
    
    def create_python_module(self, module_name: str, code: str) -> str:
        """
        Create a new Python module.
        
        Args:
            module_name (str): Module name (without .py extension)
            code (str): Python code for the module
            
        Returns:
            str: Path to the created module
        """
        if not module_name.endswith('.py'):
            module_name = f"{module_name}.py"
        
        module_path = os.path.join(self.modules_dir, module_name)
        
        try:
            with open(module_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            logger.info(f"Created dynamic Python module: {module_path}")
            return module_path
        except Exception as e:
            logger.error(f"Error creating Python module {module_name}: {e}")
            return ""
    
    def load_python_module(self, module_name: str) -> Optional[Any]:
        """
        Load a dynamic Python module.
        
        Args:
            module_name (str): Module name (without .py extension)
            
        Returns:
            Optional[Any]: Loaded module or None if error
        """
        if module_name.endswith('.py'):
            module_name = module_name[:-3]
        
        # Check if already loaded
        if module_name in self.loaded_modules:
            return self.loaded_modules[module_name]
        
        module_path = os.path.join(self.modules_dir, f"{module_name}.py")
        
        try:
            if not os.path.exists(module_path):
                logger.warning(f"Python module does not exist: {module_path}")
                return None
            
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if not spec or not spec.loader:
                logger.error(f"Failed to get spec for module: {module_name}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Cache the loaded module
            self.loaded_modules[module_name] = module
            
            logger.info(f"Loaded dynamic Python module: {module_name}")
            return module
        except Exception as e:
            logger.error(f"Error loading Python module {module_name}: {e}")
            return None
    
    def create_function(self, function_code: str) -> Optional[Callable]:
        """
        Create a callable function from code.
        
        Args:
            function_code (str): Python code defining a function
            
        Returns:
            Optional[Callable]: Compiled function or None if error
        """
        try:
            # Add a timestamp to make the module name unique
            module_name = f"dynamic_function_{int(time.time())}"
            
            # Create a temporary module
            module_path = self.create_python_module(module_name, function_code)
            if not module_path:
                return None
            
            # Load the module
            module = self.load_python_module(module_name)
            if not module:
                return None
            
            # Find and return the function
            # Assume the function is the first callable in the module
            for item_name in dir(module):
                item = getattr(module, item_name)
                if callable(item) and not item_name.startswith('__'):
                    logger.info(f"Created and loaded dynamic function: {item_name}")
                    return item
            
            logger.error("No function found in the provided code")
            return None
        except Exception as e:
            logger.error(f"Error creating function: {e}")
            return None
    
    def list_json_files(self) -> List[str]:
        """
        List all JSON data files.
        
        Returns:
            List[str]: List of filenames
        """
        files = []
        try:
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.json'):
                    files.append(filename)
        except Exception as e:
            logger.error(f"Error listing JSON files: {e}")
        
        return files
    
    def list_python_modules(self) -> List[str]:
        """
        List all Python modules.
        
        Returns:
            List[str]: List of module names
        """
        modules = []
        try:
            for filename in os.listdir(self.modules_dir):
                if filename.endswith('.py'):
                    modules.append(filename[:-3])  # Remove .py extension
        except Exception as e:
            logger.error(f"Error listing Python modules: {e}")
        
        return modules
    
    def delete_file(self, filename: str) -> bool:
        """
        Delete a file (either JSON or Python).
        
        Args:
            filename (str): Filename to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Check if JSON file
        if filename.endswith('.json'):
            file_path = os.path.join(self.data_dir, filename)
        # Check if Python module
        elif filename.endswith('.py'):
            file_path = os.path.join(self.modules_dir, filename)
            # Remove from loaded modules if present
            module_name = filename[:-3]
            if module_name in self.loaded_modules:
                del self.loaded_modules[module_name]
        else:
            # Try both with extensions
            json_path = os.path.join(self.data_dir, f"{filename}.json")
            py_path = os.path.join(self.modules_dir, f"{filename}.py")
            
            if os.path.exists(json_path):
                file_path = json_path
            elif os.path.exists(py_path):
                file_path = py_path
                # Remove from loaded modules if present
                if filename in self.loaded_modules:
                    del self.loaded_modules[filename]
            else:
                logger.warning(f"File not found: {filename}")
                return False
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
                return True
            else:
                logger.warning(f"File not found: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
            return False