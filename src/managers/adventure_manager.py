"""
Adventure Manager for Lachesis bot.

This module handles the creation and tracking of adventures.
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger("lachesis.adventure_manager")

class AdventureManager:
    """
    Manager for adventures.
    
    Handles the creation, storage, and retrieval of adventures
    and adventure templates.
    """
    
    def __init__(self, data_dir: str):
        """
        Initialize the adventure manager.
        
        Args:
            data_dir (str): Directory for storing adventure data
        """
        self.data_dir = data_dir
        self.templates_dir = os.path.join(data_dir, "templates")
        self.active_dir = os.path.join(data_dir, "active")
        
        # Create directories if they don't exist
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.active_dir, exist_ok=True)
        
        # Cache for active adventures
        self.active_cache = {}  # adventure_id -> adventure_data
    
    def get_adventure_templates(self) -> List[Dict[str, Any]]:
        """
        Get all available adventure templates.
        
        Returns:
            List[Dict]: List of adventure templates
        """
        templates = []
        
        try:
            for filename in os.listdir(self.templates_dir):
                if filename.endswith(".json"):
                    template_path = os.path.join(self.templates_dir, filename)
                    with open(template_path, 'r', encoding='utf-8') as f:
                        template = json.load(f)
                    templates.append(template)
        except Exception as e:
            logger.error(f"Error loading adventure templates: {e}")
        
        return templates
    
    def get_adventure_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific adventure template.
        
        Args:
            template_id (str): Template ID
            
        Returns:
            Optional[Dict]: Adventure template or None if not found
        """
        template_path = os.path.join(self.templates_dir, f"{template_id}.json")
        
        try:
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading adventure template {template_id}: {e}")
        
        return None
    
    def create_adventure_template(self, template_data: Dict[str, Any]) -> str:
        """
        Create a new adventure template.
        
        Args:
            template_data (Dict): Template data
            
        Returns:
            str: Template ID
        """
        # Generate ID if not provided
        if "id" not in template_data:
            template_data["id"] = f"template_{uuid.uuid4().hex[:8]}"
        
        # Add timestamp
        template_data["created_at"] = datetime.now().isoformat()
        
        # Save to disk
        template_path = os.path.join(self.templates_dir, f"{template_data['id']}.json")
        
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created adventure template: {template_data['id']}")
            return template_data["id"]
        except Exception as e:
            logger.error(f"Error creating adventure template: {e}")
            return ""
    
    def start_adventure(self, user_id: str, template_id: Optional[str] = None) -> str:
        """
        Start a new adventure for a user.
        
        Args:
            user_id (str): User ID
            template_id (Optional[str]): Template ID (if None, create a dynamic adventure)
            
        Returns:
            str: Adventure ID
        """
        # Generate adventure ID
        adventure_id = f"adv_{uuid.uuid4().hex[:8]}"
        
        # Load template if provided
        if template_id:
            template = self.get_adventure_template(template_id)
            if not template:
                logger.error(f"Template {template_id} not found")
                return ""
            
            adventure_data = template.copy()
        else:
            # Create a basic dynamic adventure structure
            adventure_data = {
                "id": adventure_id,
                "title": "Dynamic Adventure",
                "type": "dynamic",
                "created_at": datetime.now().isoformat(),
                "scenes": {},
                "current_scene": "start",
                "next_scene_id": 1,
                "variables": {},
                "history": []
            }
        
        # Add adventure metadata
        adventure_data["adventure_id"] = adventure_id
        adventure_data["user_id"] = user_id
        adventure_data["started_at"] = datetime.now().isoformat()
        adventure_data["last_updated"] = datetime.now().isoformat()
        adventure_data["active"] = True
        
        # Save to disk
        adventure_path = os.path.join(self.active_dir, f"{adventure_id}.json")
        
        try:
            with open(adventure_path, 'w', encoding='utf-8') as f:
                json.dump(adventure_data, f, indent=2, ensure_ascii=False)
            
            # Add to cache
            self.active_cache[adventure_id] = adventure_data
            
            logger.info(f"Started adventure {adventure_id} for user {user_id}")
            return adventure_id
        except Exception as e:
            logger.error(f"Error starting adventure: {e}")
            return ""
    
    def get_adventure(self, adventure_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an active adventure.
        
        Args:
            adventure_id (str): Adventure ID
            
        Returns:
            Optional[Dict]: Adventure data or None if not found
        """
        # Check cache first
        if adventure_id in self.active_cache:
            return self.active_cache[adventure_id]
        
        # Load from disk
        adventure_path = os.path.join(self.active_dir, f"{adventure_id}.json")
        
        try:
            if os.path.exists(adventure_path):
                with open(adventure_path, 'r', encoding='utf-8') as f:
                    adventure_data = json.load(f)
                
                # Add to cache
                self.active_cache[adventure_id] = adventure_data
                
                return adventure_data
        except Exception as e:
            logger.error(f"Error loading adventure {adventure_id}: {e}")
        
        return None
    
    def get_active_adventures_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active adventures for a user.
        
        Args:
            user_id (str): User ID
            
        Returns:
            List[Dict]: List of active adventures
        """
        adventures = []
        
        try:
            for filename in os.listdir(self.active_dir):
                if filename.endswith(".json"):
                    adventure_path = os.path.join(self.active_dir, filename)
                    
                    try:
                        with open(adventure_path, 'r', encoding='utf-8') as f:
                            adventure_data = json.load(f)
                        
                        if (adventure_data.get("user_id") == user_id and 
                                adventure_data.get("active", False)):
                            adventures.append(adventure_data)
                    except Exception:
                        # Skip if error reading adventure
                        pass
        except Exception as e:
            logger.error(f"Error loading user adventures: {e}")
        
        return adventures
    
    def add_scene(self, adventure_id: str, scene_data: Dict[str, Any]) -> str:
        """
        Add a scene to an adventure.
        
        Args:
            adventure_id (str): Adventure ID
            scene_data (Dict): Scene data
            
        Returns:
            str: Scene ID
        """
        adventure = self.get_adventure(adventure_id)
        if not adventure:
            logger.error(f"Adventure {adventure_id} not found")
            return ""
        
        # Generate scene ID if not provided
        if "id" not in scene_data:
            next_id = adventure.get("next_scene_id", 1)
            scene_data["id"] = f"scene_{next_id}"
            adventure["next_scene_id"] = next_id + 1
        
        # Add scene to adventure
        if "scenes" not in adventure:
            adventure["scenes"] = {}
        
        adventure["scenes"][scene_data["id"]] = scene_data
        
        # Add timestamp
        adventure["last_updated"] = datetime.now().isoformat()
        
        # Save to disk
        self._save_adventure(adventure)
        
        return scene_data["id"]
    
    def update_scene(self, adventure_id: str, scene_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a scene in an adventure.
        
        Args:
            adventure_id (str): Adventure ID
            scene_id (str): Scene ID
            updates (Dict): Updates to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        adventure = self.get_adventure(adventure_id)
        if not adventure or "scenes" not in adventure or scene_id not in adventure["scenes"]:
            logger.error(f"Scene {scene_id} not found in adventure {adventure_id}")
            return False
        
        # Update scene
        adventure["scenes"][scene_id].update(updates)
        
        # Add timestamp
        adventure["last_updated"] = datetime.now().isoformat()
        
        # Save to disk
        return self._save_adventure(adventure)
    
    def set_current_scene(self, adventure_id: str, scene_id: str) -> bool:
        """
        Set the current scene for an adventure.
        
        Args:
            adventure_id (str): Adventure ID
            scene_id (str): Scene ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        adventure = self.get_adventure(adventure_id)
        if not adventure:
            logger.error(f"Adventure {adventure_id} not found")
            return False
        
        # Check if scene exists
        if "scenes" in adventure and scene_id in adventure["scenes"]:
            # Set current scene
            adventure["current_scene"] = scene_id
            
            # Add to history
            if "history" not in adventure:
                adventure["history"] = []
            adventure["history"].append({
                "scene": scene_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # Add timestamp
            adventure["last_updated"] = datetime.now().isoformat()
            
            # Save to disk
            return self._save_adventure(adventure)
        else:
            logger.error(f"Scene {scene_id} not found in adventure {adventure_id}")
            return False
    
    def get_current_scene(self, adventure_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current scene for an adventure.
        
        Args:
            adventure_id (str): Adventure ID
            
        Returns:
            Optional[Dict]: Current scene data or None if not found
        """
        adventure = self.get_adventure(adventure_id)
        if not adventure:
            logger.error(f"Adventure {adventure_id} not found")
            return None
        
        current_scene_id = adventure.get("current_scene")
        if not current_scene_id:
            return None
        
        return adventure.get("scenes", {}).get(current_scene_id)
    
    def advance_scene(self, adventure_id: str, choice_key: str) -> Optional[Dict[str, Any]]:
        """
        Advance to the next scene based on a choice.
        
        Args:
            adventure_id (str): Adventure ID
            choice_key (str): Choice key
            
        Returns:
            Optional[Dict]: Next scene data or None if not found
        """
        adventure = self.get_adventure(adventure_id)
        if not adventure:
            logger.error(f"Adventure {adventure_id} not found")
            return None
        
        current_scene_id = adventure.get("current_scene")
        if not current_scene_id:
            return None
        
        current_scene = adventure.get("scenes", {}).get(current_scene_id)
        if not current_scene:
            return None
        
        # Find the option that matches the choice
        next_scene_id = None
        for option in current_scene.get("options", []):
            if option.get("next") == choice_key:
                next_scene_id = choice_key
                break
        
        if not next_scene_id:
            logger.error(f"Choice {choice_key} not found in scene {current_scene_id}")
            return None
        
        # Set the next scene
        self.set_current_scene(adventure_id, next_scene_id)
        
        # Return the next scene
        return adventure.get("scenes", {}).get(next_scene_id)
    
    def complete_adventure(self, adventure_id: str) -> bool:
        """
        Mark an adventure as completed.
        
        Args:
            adventure_id (str): Adventure ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        adventure = self.get_adventure(adventure_id)
        if not adventure:
            logger.error(f"Adventure {adventure_id} not found")
            return False
        
        # Mark as inactive
        adventure["active"] = False
        adventure["completed_at"] = datetime.now().isoformat()
        adventure["last_updated"] = datetime.now().isoformat()
        
        # Save to disk
        return self._save_adventure(adventure)
    
    def _save_adventure(self, adventure: Dict[str, Any]) -> bool:
        """
        Save an adventure to disk.
        
        Args:
            adventure (Dict): Adventure data
            
        Returns:
            bool: True if successful, False otherwise
        """
        adventure_id = adventure.get("adventure_id")
        if not adventure_id:
            logger.error("Adventure missing ID")
            return False
        
        adventure_path = os.path.join(self.active_dir, f"{adventure_id}.json")
        
        try:
            with open(adventure_path, 'w', encoding='utf-8') as f:
                json.dump(adventure, f, indent=2, ensure_ascii=False)
            
            # Update cache
            self.active_cache[adventure_id] = adventure
            
            return True
        except Exception as e:
            logger.error(f"Error saving adventure {adventure_id}: {e}")
            return False