import json
import os
from datetime import datetime

class ProfileManager:
    def __init__(self, base_folder="profiles"):
        self.base_folder = base_folder
        if not os.path.exists(self.base_folder):
            os.makedirs(self.base_folder)

    def get_profile_path(self, user_id: str) -> str:
        return os.path.join(self.base_folder, f"{user_id}_profile.json")

    def load_profile(self, user_id: str) -> dict:
        """Load or create a profile for a user."""
        path = self.get_profile_path(user_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # Return a default new user profile
            return {
                "character_sheet": {
                    "name": "",
                    "race": "",
                    "class": "",
                    "stats": {},   # e.g. STR, DEX, etc.
                },
                "dm_notes": {
                    "story_arcs": [],
                    "inventory": [],
                },
                "dynamic_attributes": {},  # mood, environment, etc.
                "long_term_memories": [],  # store summarized older convos
            }

    def save_profile(self, user_id: str, data: dict):
        path = self.get_profile_path(user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def update_character_sheet(self, user_id: str, updates: dict):
        profile = self.load_profile(user_id)
        for k, v in updates.items():
            profile["character_sheet"][k] = v
        self.save_profile(user_id, profile)

    def add_long_term_memory(self, user_id: str, summary: str):
        profile = self.load_profile(user_id)
        profile["long_term_memories"].append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary
        })
        self.save_profile(user_id, profile)

    def update_dynamic_attributes(self, user_id: str, updates: dict):
        profile = self.load_profile(user_id)
        dynamic_attrs = profile["dynamic_attributes"]
        for k, v in updates.items():
            dynamic_attrs[k] = v
        self.save_profile(user_id, profile)