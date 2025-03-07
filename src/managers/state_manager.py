"""
State Manager for Lachesis bot.

This module handles the tracking and management of user states.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("lachesis.state_manager")

class StateManager:
    """
    Manager for user states.
    
    Handles the storage and retrieval of user states,
    which determine how the bot interacts with the user.
    """
    
    def __init__(self, data_dir: str):
        """
        Initialize the state manager.
        
        Args:
            data_dir (str): Directory for storing state data
        """
        self.data_dir = data_dir
        self.states_cache = {}  # user_id -> state
        self.metadata_cache = {}  # user_id -> metadata
        
        os.makedirs(data_dir, exist_ok=True)
    
    def _get_state_path(self, user_id: str) -> str:
        """
        Get the file path for a user's state.
        
        Args:
            user_id (str): User ID
            
        Returns:
            str: Path to the user's state file
        """
        user_dir = os.path.join(self.data_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, "state.json")
    
    def get_state(self, user_id: str) -> str:
        """
        Get the current state for a user.
        
        Args:
            user_id (str): User ID
            
        Returns:
            str: Current state
        """
        # Check cache first
        if user_id in self.states_cache:
            return self.states_cache[user_id]
        
        # Load from disk
        state_path = self._get_state_path(user_id)
        
        try:
            if os.path.exists(state_path):
                with open(state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Cache state and metadata
                self.states_cache[user_id] = data.get("state", "menu")
                self.metadata_cache[user_id] = data.get("metadata", {})
                
                return self.states_cache[user_id]
            else:
                # Initialize with default state
                self.states_cache[user_id] = "menu"
                self.metadata_cache[user_id] = {}
                self._save_state(user_id)
                return "menu"
        except Exception as e:
            logger.error(f"Error loading state for {user_id}: {e}")
            # Return default state on error
            return "menu"
    
    def set_state(self, user_id: str, state: str) -> None:
        """
        Set the state for a user.
        
        Args:
            user_id (str): User ID
            state (str): New state
        """
        # Update cache
        self.states_cache[user_id] = state
        
        # Make sure metadata exists
        if user_id not in self.metadata_cache:
            self.metadata_cache[user_id] = {}
        
        # Save to disk
        self._save_state(user_id)
        
        logger.info(f"User {user_id} state set to: {state}")
    
    def get_state_metadata(self, user_id: str) -> Dict[str, Any]:
        """
        Get metadata for a user's state.
        
        Args:
            user_id (str): User ID
            
        Returns:
            Dict: State metadata
        """
        # Make sure state is loaded
        if user_id not in self.states_cache:
            self.get_state(user_id)
        
        # Return metadata from cache
        return self.metadata_cache.get(user_id, {})
    
    def update_state_metadata(self, user_id: str, metadata_update: Dict[str, Any]) -> None:
        """
        Update metadata for a user's state.
        
        Args:
            user_id (str): User ID
            metadata_update (Dict): Metadata updates
        """
        # Make sure state is loaded
        if user_id not in self.states_cache:
            self.get_state(user_id)
        
        # Initialize metadata if not exists
        if user_id not in self.metadata_cache:
            self.metadata_cache[user_id] = {}
        
        # Update metadata
        self.metadata_cache[user_id].update(metadata_update)
        
        # Save to disk
        self._save_state(user_id)
    
    def clear_state_metadata(self, user_id: str) -> None:
        """
        Clear metadata for a user's state.
        
        Args:
            user_id (str): User ID
        """
        # Clear metadata
        self.metadata_cache[user_id] = {}
        
        # Save to disk
        self._save_state(user_id)
    
    def _save_state(self, user_id: str) -> None:
        """
        Save state to disk.
        
        Args:
            user_id (str): User ID
        """
        state_path = self._get_state_path(user_id)
        
        # Make sure caches are initialized
        if user_id not in self.states_cache:
            self.states_cache[user_id] = "menu"
        if user_id not in self.metadata_cache:
            self.metadata_cache[user_id] = {}
        
        # Prepare data
        data = {
            "state": self.states_cache[user_id],
            "metadata": self.metadata_cache[user_id]
        }
        
        try:
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving state for {user_id}: {e}")
    
    def get_all_users_in_state(self, state: str) -> list:
        """
        Get all users that are in a specific state.
        
        Args:
            state (str): State to check
            
        Returns:
            list: List of user IDs
        """
        result = []
        
        # Check cache for quick matches
        for user_id, cached_state in self.states_cache.items():
            if cached_state == state:
                result.append(user_id)
        
        # Check disk for any users not in cache
        try:
            for user_dir in os.listdir(self.data_dir):
                # Skip if not a directory
                if not os.path.isdir(os.path.join(self.data_dir, user_dir)):
                    continue
                
                # Skip if already in result
                if user_dir in result:
                    continue
                
                # Check state
                state_path = os.path.join(self.data_dir, user_dir, "state.json")
                if os.path.exists(state_path):
                    try:
                        with open(state_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        if data.get("state") == state:
                            result.append(user_dir)
                    except Exception:
                        # Skip if error reading state
                        pass
        except Exception as e:
            logger.error(f"Error listing users in state {state}: {e}")
        
        return result