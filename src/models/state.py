from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime

@dataclass
class UserState:
    """The state of a user in the system."""
    user_id: str
    current_state: str = "introduction"  # Default state
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    last_channel_id: Optional[str] = None
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "current_state": self.current_state,
            "metadata": self.metadata,
            "last_updated": self.last_updated,
            "last_channel_id": self.last_channel_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserState':
        """Create from dictionary."""
        if not data:
            raise ValueError("Cannot create UserState from empty data")
        
        user_id = data.get("user_id")
        if not user_id:
            raise ValueError("UserState requires a user_id")
        
        return cls(
            user_id=user_id,
            current_state=data.get("current_state", "introduction"),
            metadata=data.get("metadata", {}),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
            last_channel_id=data.get("last_channel_id")
        )

@dataclass
class AdventureState:
    """The state of an adventure."""
    adventure_id: str
    user_id: str
    template_id: str
    current_scene: str
    visited_scenes: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    inventory: Dict[str, Any] = field(default_factory=dict)
    npcs: Dict[str, Any] = field(default_factory=dict)
    quests: Dict[str, Any] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "adventure_id": self.adventure_id,
            "user_id": self.user_id,
            "template_id": self.template_id,
            "current_scene": self.current_scene,
            "visited_scenes": self.visited_scenes,
            "variables": self.variables,
            "inventory": self.inventory,
            "npcs": self.npcs,
            "quests": self.quests,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdventureState':
        """Create from dictionary."""
        if not data:
            raise ValueError("Cannot create AdventureState from empty data")
        
        adventure_id = data.get("adventure_id")
        if not adventure_id:
            raise ValueError("AdventureState requires an adventure_id")
        
        user_id = data.get("user_id")
        if not user_id:
            raise ValueError("AdventureState requires a user_id")
        
        template_id = data.get("template_id")
        if not template_id:
            raise ValueError("AdventureState requires a template_id")
        
        current_scene = data.get("current_scene")
        if not current_scene:
            raise ValueError("AdventureState requires a current_scene")
        
        return cls(
            adventure_id=adventure_id,
            user_id=user_id,
            template_id=template_id,
            current_scene=current_scene,
            visited_scenes=data.get("visited_scenes", []),
            variables=data.get("variables", {}),
            inventory=data.get("inventory", {}),
            npcs=data.get("npcs", {}),
            quests=data.get("quests", {}),
            last_updated=data.get("last_updated", datetime.now().isoformat())
        )

@dataclass
class CharacterCreationState:
    """The state of character creation."""
    user_id: str
    step: int = 0
    responses: Dict[str, str] = field(default_factory=dict)
    current_question: Optional[str] = None
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "step": self.step,
            "responses": self.responses,
            "current_question": self.current_question,
            "start_time": self.start_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterCreationState':
        """Create from dictionary."""
        if not data:
            raise ValueError("Cannot create CharacterCreationState from empty data")
        
        user_id = data.get("user_id")
        if not user_id:
            raise ValueError("CharacterCreationState requires a user_id")
        
        return cls(
            user_id=user_id,
            step=data.get("step", 0),
            responses=data.get("responses", {}),
            current_question=data.get("current_question"),
            start_time=data.get("start_time", datetime.now().isoformat())
        )