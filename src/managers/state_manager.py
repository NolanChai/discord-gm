import os
import json
from datetime import datetime

class StateManager:
    """
    Manages the state of users in different contexts (introduction, character creation, adventure, etc.).
    """
    def __init__(self, data_dir):
        """
        Initialize the state manager.
        
        Args:
            data_dir: Directory for storing state files
        """
        self.data_dir = data_dir
        self.states = {}  # Cache of user states: user_id -> state
        self.metadata = {}  # Additional state metadata: user_id -> dict
        os.makedirs(data_dir, exist_ok=True)
    
    def _get_user_dir(self, user_id):
        """Get the directory for a specific user, creating it if it doesn't exist."""
        user_dir = os.path.join(self.data_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def _get_state_path(self, user_id):
        """Get the path to a user's state file."""
        return os.path.join(self._get_user_dir(user_id), "state.json")
    
    def get_state(self, user_id):
        """
        Get the current state for a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            str: The current state
        """
        # Check cache first
        if user_id in self.states:
            return self.states[user_id]
        
        # Check file
        state_path = self._get_state_path(user_id)
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r') as f:
                    state_data = json.load(f)
                    state = state_data.get("current_state", "introduction")
                    metadata = state_data.get("metadata", {})
                    
                    self.states[user_id] = state
                    self.metadata[user_id] = metadata
                    return state
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading state for {user_id}: {e}")
        
        # Default to introduction
        self.states[user_id] = "introduction"
        self.metadata[user_id] = {}
        self.save_state(user_id, "introduction")
        return "introduction"
    
    def get_state_metadata(self, user_id, key=None, default=None):
        """
        Get metadata for a user's state.
        
        Args:
            user_id: Discord user ID
            key: Optional key to get specific metadata
            default: Default value if key not found
            
        Returns:
            The metadata value or default
        """
        if user_id not in self.metadata:
            # Load the state to populate metadata
            self.get_state(user_id)
        
        if key is None:
            return self.metadata.get(user_id, {})
        
        return self.metadata.get(user_id, {}).get(key, default)
    
    def save_state(self, user_id, state, metadata=None):
        """
        Save the state for a user.
        
        Args:
            user_id: Discord user ID
            state: State to save
            metadata: Optional metadata to save with the state
            
        Returns:
            bool: Success or failure
        """
        # Update cache
        self.states[user_id] = state
        
        # Update metadata
        if metadata:
            if user_id not in self.metadata:
                self.metadata[user_id] = {}
            self.metadata[user_id].update(metadata)
        
        # Save to file
        state_path = self._get_state_path(user_id)
        state_data = {
            "user_id": user_id,
            "current_state": state,
            "metadata": self.metadata.get(user_id, {}),
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            with open(state_path, 'w') as f:
                json.dump(state_data, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving state for {user_id}: {e}")
            return False
    
    def transition_to(self, user_id, new_state, metadata=None):
        """
        Transition a user to a new state.
        
        Args:
            user_id: Discord user ID
            new_state: New state to transition to
            metadata: Optional metadata to save with the state
            
        Returns:
            bool: Success or failure
        """
        # Get current state for logging transitions
        current_state = self.get_state(user_id)
        
        # Log the transition
        print(f"State transition for user {user_id}: {current_state} -> {new_state}")
        
        return self.save_state(user_id, new_state, metadata)
    
    def update_state_metadata(self, user_id, updates):
        """
        Update metadata for a user's state.
        
        Args:
            user_id: Discord user ID
            updates: Dictionary of metadata updates
            
        Returns:
            bool: Success or failure
        """
        # Get current state to ensure metadata is loaded
        current_state = self.get_state(user_id)
        
        # Update metadata
        if user_id not in self.metadata:
            self.metadata[user_id] = {}
        self.metadata[user_id].update(updates)
        
        # Save state with updated metadata
        return self.save_state(user_id, current_state)
    
    def update_state_after_message(self, user_id, event_type):
        """
        Update state based on an event. This is a simple implementation -
        in a real system, you might use more complex logic.
        
        Args:
            user_id: Discord user ID
            event_type: Type of event that occurred
            
        Returns:
            bool: Whether the state was changed
        """
        current_state = self.get_state(user_id)
        
        # Simple state transitions
        if event_type == "start_adventure" and current_state != "adventure":
            return self.transition_to(user_id, "adventure")
        elif event_type == "create_character" and current_state != "character_creation":
            return self.transition_to(user_id, "character_creation")
        elif event_type == "character_created" and current_state == "character_creation":
            return self.transition_to(user_id, "menu")
        elif event_type == "adventure_ended" and current_state == "adventure":
            return self.transition_to(user_id, "menu")
        
        # No state change
        return False
    
    def get_available_states(self):
        """
        Get a list of available states.
        
        Returns:
            list: List of available states
        """
        return [
            "introduction",
            "menu",
            "character_creation",
            "adventure",
            "combat",
            "dialogue",
            "inventory",
            "quest_log"
        ]
