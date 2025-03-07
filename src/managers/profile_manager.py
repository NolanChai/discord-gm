"""
Profile Manager for Lachesis bot.

This module handles the storage and retrieval of user profiles.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("lachesis.profile_manager")

class ProfileManager:
    """
    Manager for user profiles.
    
    Handles the storage and retrieval of user profile data,
    including character sheets and user preferences.
    """
    
    def __init__(self, data_dir: str):
        """
        Initialize the profile manager.
        
        Args:
            data_dir (str): Directory for storing user profile data
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def _get_profile_path(self, user_id: str) -> str:
        """
        Get the file path for a user's profile.
        
        Args:
            user_id (str): User ID
            
        Returns:
            str: Path to the user's profile file
        """
        return os.path.join(self.data_dir, f"{user_id}/profile.json")
    
    def load_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Load a user's profile.
        
        Args:
            user_id (str): User ID
            
        Returns:
            Dict: User profile data
        """
        profile_path = self._get_profile_path(user_id)
        
        # Create user directory if it doesn't exist
        os.makedirs(os.path.dirname(profile_path), exist_ok=True)
        
        try:
            if os.path.exists(profile_path):
                with open(profile_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Create a default profile
                default_profile = self._create_default_profile()
                self.save_profile(user_id, default_profile)
                return default_profile
        except Exception as e:
            logger.error(f"Error loading profile for {user_id}: {e}")
            # Return a default profile if loading fails
            return self._create_default_profile()
    
    def save_profile(self, user_id: str, profile: Dict[str, Any]) -> bool:
        """
        Save a user's profile.
        
        Args:
            user_id (str): User ID
            profile (Dict): Profile data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        profile_path = self._get_profile_path(user_id)
        
        # Create user directory if it doesn't exist
        os.makedirs(os.path.dirname(profile_path), exist_ok=True)
        
        try:
            # Update last modified timestamp
            profile["last_modified"] = datetime.now().isoformat()
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving profile for {user_id}: {e}")
            return False
    
    def _create_default_profile(self) -> Dict[str, Any]:
        """
        Create a default user profile.
        
        Returns:
            Dict: Default profile data
        """
        return {
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat(),
            "username": None,
            "introduced": False,
            "character_sheet": {},
            "dynamic_attributes": {
                "health": 100,
                "energy": 100,
                "mood": "neutral"
            },
            "preferences": {
                "adventure_style": "balanced",
                "notification_frequency": "normal"
            },
            "long_term_memories": []
        }
    
    def has_character(self, user_id: str) -> bool:
        """
        Check if a user has created a character.
        
        Args:
            user_id (str): User ID
            
        Returns:
            bool: True if the user has a character, False otherwise
        """
        profile = self.load_profile(user_id)
        character_sheet = profile.get("character_sheet", {})
        
        # Check if the character sheet has the minimum required fields
        required_fields = ["name", "class", "level"]
        return all(field in character_sheet for field in required_fields)
    
    def create_character(self, user_id: str, character_data: Dict[str, Any]) -> bool:
        """
        Create a character for a user.
        
        Args:
            user_id (str): User ID
            character_data (Dict): Character data
            
        Returns:
            bool: True if successful, False otherwise
        """
        profile = self.load_profile(user_id)
        
        # Set character sheet data
        profile["character_sheet"] = character_data
        
        # Reset dynamic attributes
        profile["dynamic_attributes"] = {
            "health": 100,
            "energy": 100,
            "mood": "neutral"
        }
        
        # Save the updated profile
        return self.save_profile(user_id, profile)
    
    def update_character(self, user_id: str, field: str, value: Any) -> bool:
        """
        Update a specific field in a user's character sheet.
        
        Args:
            user_id (str): User ID
            field (str): Field to update
            value (Any): New value
            
        Returns:
            bool: True if successful, False otherwise
        """
        profile = self.load_profile(user_id)
        
        # Make sure character sheet exists
        if "character_sheet" not in profile:
            profile["character_sheet"] = {}
        
        # Update the field
        profile["character_sheet"][field] = value
        
        # Save the updated profile
        return self.save_profile(user_id, profile)
    
    def update_dynamic_attribute(self, user_id: str, attribute: str, value: Any) -> bool:
        """
        Update a dynamic attribute for a user's character.
        
        Args:
            user_id (str): User ID
            attribute (str): Attribute to update
            value (Any): New value
            
        Returns:
            bool: True if successful, False otherwise
        """
        profile = self.load_profile(user_id)
        
        # Make sure dynamic attributes exist
        if "dynamic_attributes" not in profile:
            profile["dynamic_attributes"] = {}
        
        # Update the attribute
        profile["dynamic_attributes"][attribute] = value
        
        # Save the updated profile
        return self.save_profile(user_id, profile)
    
    def set_username(self, user_id: str, username: str) -> bool:
        """
        Set a user's username.
        
        Args:
            user_id (str): User ID
            username (str): Username to set
            
        Returns:
            bool: True if successful, False otherwise
        """
        profile = self.load_profile(user_id)
        profile["username"] = username
        return self.save_profile(user_id, profile)
    
    def mark_introduction_done(self, user_id: str) -> bool:
        """
        Mark that the user has been introduced to Lachesis.
        
        Args:
            user_id (str): User ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        profile = self.load_profile(user_id)
        profile["introduced"] = True
        return self.save_profile(user_id, profile)
    
    def add_long_term_memory(self, user_id: str, memory: Dict[str, Any]) -> bool:
        """
        Add a long-term memory for a user.
        
        Args:
            user_id (str): User ID
            memory (Dict): Memory data to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        profile = self.load_profile(user_id)
        
        # Make sure long-term memories exist
        if "long_term_memories" not in profile:
            profile["long_term_memories"] = []
        
        # Add timestamp if not present
        if "timestamp" not in memory:
            memory["timestamp"] = datetime.now().isoformat()
        
        # Add the memory
        profile["long_term_memories"].append(memory)
        
        # Sort memories by timestamp (newest first)
        profile["long_term_memories"].sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        # Keep only the most recent N memories
        MAX_MEMORIES = 100
        if len(profile["long_term_memories"]) > MAX_MEMORIES:
            profile["long_term_memories"] = profile["long_term_memories"][:MAX_MEMORIES]
        
        # Save the updated profile
        return self.save_profile(user_id, profile)
    
    def get_relevant_memories(self, user_id: str, query: str, limit: int = 5) -> list:
        """
        Get relevant memories for a user based on a query.
        
        Args:
            user_id (str): User ID
            query (str): Query to match against memories
            limit (int): Maximum number of memories to return
            
        Returns:
            list: List of relevant memories
        """
        profile = self.load_profile(user_id)
        memories = profile.get("long_term_memories", [])
        
        # Simple keyword matching for now
        # This would ideally use embeddings for better semantic matching
        query_words = set(query.lower().split())
        
        # Score memories by number of matching words
        scored_memories = []
        for memory in memories:
            summary = memory.get("summary", "").lower()
            score = sum(1 for word in query_words if word in summary)
            if score > 0:
                scored_memories.append((score, memory))
        
        # Sort by score (highest first)
        scored_memories.sort(reverse=True)
        
        # Return the top N memories
        return [memory for _, memory in scored_memories[:limit]]