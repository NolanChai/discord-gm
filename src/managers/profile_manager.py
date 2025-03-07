import os
import json
from datetime import datetime

class ProfileManager:
    """
    Manages user profiles, character sheets, and related persistent data.
    """
    def __init__(self, data_dir):
        """
        Initialize the profile manager.
        
        Args:
            data_dir: Directory for storing profile files
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def _get_user_dir(self, user_id):
        """Get the directory for a specific user, creating it if it doesn't exist."""
        user_dir = os.path.join(self.data_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def _get_profile_path(self, user_id):
        """Get the path to a user's profile file."""
        return os.path.join(self._get_user_dir(user_id), "profile.json")
    
    def load_profile(self, user_id):
        """
        Load a user's profile, creating a default one if it doesn't exist.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            dict: The user's profile
        """
        profile_path = self._get_profile_path(user_id)
        
        if os.path.exists(profile_path):
            try:
                with open(profile_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading profile for {user_id}: {e}")
                # If there's an error, return a default profile
        
        # Default profile
        return self._create_default_profile(user_id)
    
    def _create_default_profile(self, user_id):
        """Create a default profile for a new user."""
        default_profile = {
            "user_id": user_id,
            "username": None,  # Will be filled in when they first interact
            "created_at": datetime.now().isoformat(),
            "introduced": False,
            "character_sheet": {
                "name": None,
                "race": None,
                "class": None,
                "level": 1,
                "stats": {
                    "strength": 10,
                    "dexterity": 10,
                    "constitution": 10,
                    "intelligence": 10,
                    "wisdom": 10,
                    "charisma": 10
                },
                "skills": {},
                "inventory": [],
                "backstory": None
            },
            "dynamic_attributes": {
                "health": 100,
                "experience": 0,
                "gold": 0,
                "reputation": 0
            },
            "long_term_memories": []
        }
        
        self.save_profile(user_id, default_profile)
        return default_profile
    
    def save_profile(self, user_id, profile):
        """
        Save a user's profile to disk.
        
        Args:
            user_id: Discord user ID
            profile: Profile data to save
            
        Returns:
            bool: Success or failure
        """
        profile_path = self._get_profile_path(user_id)
        try:
            with open(profile_path, 'w') as f:
                json.dump(profile, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving profile for {user_id}: {e}")
            return False
    
    def update_character_sheet(self, user_id, updates):
        """
        Update specific fields in a character sheet.
        
        Args:
            user_id: Discord user ID
            updates: Dictionary of field:value pairs to update
            
        Returns:
            bool: Success or failure
        """
        profile = self.load_profile(user_id)
        
        for field, value in updates.items():
            # Handle nested fields with dot notation
            if "." in field:
                parts = field.split(".")
                target = profile["character_sheet"]
                
                # Navigate to the correct nested field
                for part in parts[:-1]:
                    if part not in target:
                        target[part] = {}
                    target = target[part]
                
                # Set the value
                target[parts[-1]] = value
            else:
                # Direct field
                profile["character_sheet"][field] = value
        
        return self.save_profile(user_id, profile)
    
    def update_dynamic_attributes(self, user_id, updates):
        """
        Update dynamic attributes.
        
        Args:
            user_id: Discord user ID
            updates: Dictionary of attribute:value pairs to update
            
        Returns:
            bool: Success or failure
        """
        profile = self.load_profile(user_id)
        
        for field, value in updates.items():
            profile["dynamic_attributes"][field] = value
        
        return self.save_profile(user_id, profile)
    
    def mark_introduction_done(self, user_id):
        """
        Mark a user as having been introduced to the bot.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            bool: Success or failure
        """
        profile = self.load_profile(user_id)
        profile["introduced"] = True
        return self.save_profile(user_id, profile)
    
    def add_long_term_memory(self, user_id, memory):
        """
        Add a new long-term memory.
        
        Args:
            user_id: Discord user ID
            memory: Memory data to add
            
        Returns:
            bool: Success or failure
        """
        profile = self.load_profile(user_id)
        
        if "long_term_memories" not in profile:
            profile["long_term_memories"] = []
        
        memory["timestamp"] = datetime.now().isoformat()
        profile["long_term_memories"].append(memory)
        
        return self.save_profile(user_id, profile)
    
    def set_username(self, user_id, username):
        """
        Set the username for a user.
        
        Args:
            user_id: Discord user ID
            username: Discord username
            
        Returns:
            bool: Success or failure
        """
        profile = self.load_profile(user_id)
        profile["username"] = username
        return self.save_profile(user_id, profile)
