import os
import json
from datetime import datetime
import random

class AdventureManager:
    """
    Manages adventure data, state, and progression.
    """
    def __init__(self, data_dir):
        """
        Initialize the adventure manager.
        
        Args:
            data_dir: Directory for storing adventure files
        """
        self.data_dir = data_dir
        self.adventures_dir = os.path.join(data_dir, "adventures")
        self.templates_dir = os.path.join(self.adventures_dir, "templates")
        
        # Ensure directories exist
        os.makedirs(self.adventures_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Load adventure templates
        self.templates = self._load_templates()
    
    def _load_templates(self):
        """
        Load all adventure templates.
        
        Returns:
            dict: Dictionary of template_id -> template
        """
        templates = {}
        
        # Try to load templates from files
        if os.path.exists(self.templates_dir):
            for filename in os.listdir(self.templates_dir):
                if filename.endswith(".json"):
                    template_path = os.path.join(self.templates_dir, filename)
                    try:
                        with open(template_path, 'r') as f:
                            template_data = json.load(f)
                            template_id = template_data.get("id", filename[:-5])
                            templates[template_id] = template_data
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"Error loading template {filename}: {e}")
        
        # If no templates found, create some default ones
        if not templates:
            templates = self._create_default_templates()
        
        return templates
    
    def _create_default_templates(self):
        """
        Create default adventure templates.
        
        Returns:
            dict: Dictionary of template_id -> template
        """
        templates = {
            "forest_quest": {
                "id": "forest_quest",
                "title": "Mystery of the Enchanted Forest",
                "description": "Strange occurrences have been reported in the ancient forest. Investigate the source of the disturbances.",
                "difficulty": "beginner",
                "min_level": 1,
                "recommended_players": 1,
                "scenes": [
                    {
                        "id": "forest_entrance",
                        "description": "You stand at the entrance to the ancient forest. Twisted trees form a dark canopy overhead, and strange sounds echo from within.",
                        "options": [
                            {"text": "Enter the forest cautiously", "next": "forest_path"},
                            {"text": "Look for tracks or signs", "next": "forest_tracks"},
                            {"text": "Call out to anyone who might be nearby", "next": "forest_call"}
                        ]
                    },
                    # More scenes would be defined here
                ]
            },
            "dungeon_crawl": {
                "id": "dungeon_crawl",
                "title": "The Forgotten Catacombs",
                "description": "A network of ancient catacombs has been discovered beneath the city. Explore and uncover its secrets.",
                "difficulty": "intermediate",
                "min_level": 3,
                "recommended_players": 2,
                "scenes": [
                    {
                        "id": "catacomb_entrance",
                        "description": "You stand before a crumbling stone archway, steps leading down into darkness. The air is damp and cold.",
                        "options": [
                            {"text": "Light a torch and proceed down the steps", "next": "main_chamber"},
                            {"text": "Check the entrance for traps", "next": "entrance_check"},
                            {"text": "Listen for sounds from below", "next": "entrance_listen"}
                        ]
                    },
                    # More scenes would be defined here
                ]
            }
        }
        
        # Save the default templates
        for template_id, template in templates.items():
            self._save_template(template)
        
        return templates
    
    def _save_template(self, template):
        """
        Save an adventure template to disk.
        
        Args:
            template: Template data to save
            
        Returns:
            bool: Success or failure
        """
        template_id = template.get("id", f"template_{int(datetime.now().timestamp())}")
        template_path = os.path.join(self.templates_dir, f"{template_id}.json")
        
        try:
            with open(template_path, 'w') as f:
                json.dump(template, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving template {template_id}: {e}")
            return False
    
    def _get_adventure_dir(self, adventure_id):
        """Get the directory for a specific adventure, creating it if it doesn't exist."""
        adventure_dir = os.path.join(self.adventures_dir, adventure_id)
        os.makedirs(adventure_dir, exist_ok=True)
        return adventure_dir
    
    def _get_adventure_path(self, adventure_id):
        """Get the path to an adventure's main file."""
        return os.path.join(self._get_adventure_dir(adventure_id), "adventure.json")
    
    def create_adventure(self, user_id, template_id=None, participants=None):
        """
        Create a new adventure for a user.
        
        Args:
            user_id: Discord user ID of the creator
            template_id: Optional template to use (random if not specified)
            participants: Optional list of participant user IDs
            
        Returns:
            str: Adventure ID
        """
        # Generate a unique adventure ID
        adventure_id = f"adv_{user_id}_{int(datetime.now().timestamp())}"
        
        # Choose a template if not specified
        if template_id is None or template_id not in self.templates:
            template_id = random.choice(list(self.templates.keys()))
        
        template = self.templates[template_id]
        
        # Create the adventure data
        adventure = {
            "id": adventure_id,
            "template_id": template_id,
            "title": template.get("title", "Untitled Adventure"),
            "description": template.get("description", ""),
            "created_at": datetime.now().isoformat(),
            "creator_id": user_id,
            "participants": participants or [user_id],
            "status": "active",
            "current_scene": template.get("scenes", [])[0].get("id") if template.get("scenes") else None,
            "visited_scenes": [],
            "state": {
                "variables": {},
                "inventory": {},
                "npcs": {},
                "quests": {}
            }
        }
        
        # Save the adventure
        adventure_path = self._get_adventure_path(adventure_id)
        try:
            with open(adventure_path, 'w') as f:
                json.dump(adventure, f, indent=2)
        except IOError as e:
            print(f"Error saving adventure {adventure_id}: {e}")
            return None
        
        return adventure_id
    
    def load_adventure(self, adventure_id):
        """
        Load an adventure by ID.
        
        Args:
            adventure_id: Adventure ID
            
        Returns:
            dict: Adventure data or None if not found
        """
        adventure_path = self._get_adventure_path(adventure_id)
        if not os.path.exists(adventure_path):
            return None
        
        try:
            with open(adventure_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading adventure {adventure_id}: {e}")
            return None
    
    def save_adventure(self, adventure_id, adventure_data):
        """
        Save adventure data.
        
        Args:
            adventure_id: Adventure ID
            adventure_data: Adventure data to save
            
        Returns:
            bool: Success or failure
        """
        adventure_path = self._get_adventure_path(adventure_id)
        
        try:
            with open(adventure_path, 'w') as f:
                json.dump(adventure_data, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving adventure {adventure_id}: {e}")
            return False
    
    def get_user_adventures(self, user_id):
        """
        Get all adventures a user is participating in.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            list: List of adventure data
        """
        adventures = []
        
        # Check all adventures in the directory
        if os.path.exists(self.adventures_dir):
            for item in os.listdir(self.adventures_dir):
                adventure_dir = os.path.join(self.adventures_dir, item)
                if os.path.isdir(adventure_dir):
                    adventure_path = os.path.join(adventure_dir, "adventure.json")
                    if os.path.exists(adventure_path):
                        try:
                            with open(adventure_path, 'r') as f:
                                adventure = json.load(f)
                                if user_id in adventure.get("participants", []):
                                    adventures.append(adventure)
                        except (json.JSONDecodeError, IOError):
                            continue
        
        return adventures
    
    def get_active_adventure(self, user_id):
        """
        Get the user's currently active adventure.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            tuple: (adventure_id, adventure_data) or (None, None) if no active adventure
        """
        adventures = self.get_user_adventures(user_id)
        
        # Filter to active adventures
        active_adventures = [adv for adv in adventures if adv.get("status") == "active"]
        
        if not active_adventures:
            return None, None
        
        # If multiple active adventures, use the most recent one
        active_adventures.sort(key=lambda adv: adv.get("created_at", ""), reverse=True)
        adventure = active_adventures[0]
        
        return adventure.get("id"), adventure
    
    def update_adventure_state(self, adventure_id, updates):
        """
        Update an adventure's state variables.
        
        Args:
            adventure_id: Adventure ID
            updates: Dictionary of state updates
            
        Returns:
            bool: Success or failure
        """
        adventure = self.load_adventure(adventure_id)
        if not adventure:
            return False
        
        # Update state variables
        if "variables" in updates:
            adventure["state"]["variables"].update(updates["variables"])
        
        if "inventory" in updates:
            adventure["state"]["inventory"].update(updates["inventory"])
        
        if "npcs" in updates:
            adventure["state"]["npcs"].update(updates["npcs"])
        
        if "quests" in updates:
            adventure["state"]["quests"].update(updates["quests"])
        
        # Save updated adventure
        return self.save_adventure(adventure_id, adventure)
    
    def advance_scene(self, adventure_id, next_scene_id):
        """
        Advance to the next scene in an adventure.
        
        Args:
            adventure_id: Adventure ID
            next_scene_id: ID of the next scene
            
        Returns:
            dict: New scene data or None on failure
        """
        adventure = self.load_adventure(adventure_id)
        if not adventure:
            return None
        
        # Get the template for this adventure
        template_id = adventure.get("template_id")
        template = self.templates.get(template_id)
        if not template:
            return None
        
        # Find the next scene in the template
        scenes = template.get("scenes", [])
        next_scene = None
        for scene in scenes:
            if scene.get("id") == next_scene_id:
                next_scene = scene
                break
        
        if not next_scene:
            return None
        
        # Update adventure with new scene
        adventure["current_scene"] = next_scene_id
        adventure["visited_scenes"].append(next_scene_id)
        
        # Save updated adventure
        if not self.save_adventure(adventure_id, adventure):
            return None
        
        return next_scene
    
    def end_adventure(self, adventure_id, status="completed"):
        """
        End an adventure.
        
        Args:
            adventure_id: Adventure ID
            status: End status (completed, failed, abandoned)
            
        Returns:
            bool: Success or failure
        """
        adventure = self.load_adventure(adventure_id)
        if not adventure:
            return False
        
        # Update status and end time
        adventure["status"] = status
        adventure["ended_at"] = datetime.now().isoformat()
        
        # Save updated adventure
        return self.save_adventure(adventure_id, adventure)
    
    def create_custom_template(self, template_data):
        """
        Create a custom adventure template.
        
        Args:
            template_data: Template data
            
        Returns:
            str: Template ID
        """
        # Generate a unique template ID if not provided
        if "id" not in template_data:
            template_data["id"] = f"custom_{int(datetime.now().timestamp())}"
        
        # Save the template
        if self._save_template(template_data):
            # Update the in-memory templates
            self.templates[template_data["id"]] = template_data
            return template_data["id"]
        
        return None
    
    def get_adventure_summary(self, adventure_id):
        """
        Get a summary of an adventure.
        
        Args:
            adventure_id: Adventure ID
            
        Returns:
            str: Adventure summary
        """
        adventure = self.load_adventure(adventure_id)
        if not adventure:
            return "Adventure not found."
        
        template_id = adventure.get("template_id")
        template = self.templates.get(template_id)
        
        title = adventure.get("title", "Untitled Adventure")
        status = adventure.get("status", "unknown")
        creator_id = adventure.get("creator_id", "unknown")
        participant_count = len(adventure.get("participants", []))
        visited_count = len(adventure.get("visited_scenes", []))
        
        summary = (
            f"**{title}**\n"
            f"Status: {status}\n"
            f"Creator: <@{creator_id}>\n"
            f"Participants: {participant_count}\n"
            f"Progress: {visited_count} scenes visited\n"
        )
        
        if template:
            scene_count = len(template.get("scenes", []))
            summary += f"Total scenes: {scene_count}\n"
        
        if status == "completed":
            ended_at = adventure.get("ended_at", "unknown")
            if ended_at != "unknown":
                try:
                    ended_date = datetime.fromisoformat(ended_at)
                    ended_str = ended_date.strftime("%Y-%m-%d %H:%M")
                    summary += f"Completed on: {ended_str}\n"
                except ValueError:
                    summary += f"Completed on: {ended_at}\n"
        
        return summary
