from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class Stats:
    """Character statistics."""
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10


@dataclass
class CharacterSheet:
    """Character sheet data."""
    name: Optional[str] = None
    race: Optional[str] = None
    class_name: Optional[str] = None
    level: int = 1
    stats: Stats = field(default_factory=Stats)
    skills: Dict[str, int] = field(default_factory=dict)
    inventory: List[str] = field(default_factory=list)
    backstory: Optional[str] = None
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "race": self.race,
            "class": self.class_name,  # Note the key change to match expectations
            "level": self.level,
            "stats": {
                "strength": self.stats.strength,
                "dexterity": self.stats.dexterity,
                "constitution": self.stats.constitution,
                "intelligence": self.stats.intelligence,
                "wisdom": self.stats.wisdom,
                "charisma": self.stats.charisma,
            },
            "skills": self.skills,
            "inventory": self.inventory,
            "backstory": self.backstory,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterSheet':
        """Create from dictionary."""
        if not data:
            return cls()
        
        stats_data = data.get("stats", {})
        stats = Stats(
            strength=stats_data.get("strength", 10),
            dexterity=stats_data.get("dexterity", 10),
            constitution=stats_data.get("constitution", 10),
            intelligence=stats_data.get("intelligence", 10),
            wisdom=stats_data.get("wisdom", 10),
            charisma=stats_data.get("charisma", 10),
        )
        
        return cls(
            name=data.get("name"),
            race=data.get("race"),
            class_name=data.get("class"),  # Note the key difference
            level=data.get("level", 1),
            stats=stats,
            skills=data.get("skills", {}),
            inventory=data.get("inventory", []),
            backstory=data.get("backstory"),
        )


@dataclass
class DynamicAttributes:
    """Dynamic attributes that change during adventures."""
    health: int = 100
    experience: int = 0
    gold: int = 0
    reputation: int = 0
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "health": self.health,
            "experience": self.experience,
            "gold": self.gold,
            "reputation": self.reputation,
        }
        result.update(self.custom_attributes)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DynamicAttributes':
        """Create from dictionary."""
        if not data:
            return cls()
        
        # Extract known attributes
        health = data.pop("health", 100)
        experience = data.pop("experience", 0)
        gold = data.pop("gold", 0)
        reputation = data.pop("reputation", 0)
        
        # Remaining keys go into custom_attributes
        return cls(
            health=health,
            experience=experience,
            gold=gold,
            reputation=reputation,
            custom_attributes=data
        )


@dataclass
class Memory:
    """A memory entry."""
    summary: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    type: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "summary": self.summary,
            "timestamp": self.timestamp,
            "type": self.type,
            **self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """Create from dictionary."""
        if not data:
            return cls(summary="Empty memory")
        
        # Extract known fields
        summary = data.pop("summary", "Unknown memory")
        timestamp = data.pop("timestamp", datetime.now().isoformat())
        memory_type = data.pop("type", "general")
        
        # Remaining data becomes metadata
        return cls(
            summary=summary,
            timestamp=timestamp,
            type=memory_type,
            metadata=data
        )


@dataclass
class UserProfile:
    """User profile data."""
    user_id: str
    username: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    introduced: bool = False
    character_sheet: CharacterSheet = field(default_factory=CharacterSheet)
    dynamic_attributes: DynamicAttributes = field(default_factory=DynamicAttributes)
    long_term_memories: List[Memory] = field(default_factory=list)
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "created_at": self.created_at,
            "introduced": self.introduced,
            "character_sheet": self.character_sheet.as_dict,
            "dynamic_attributes": self.dynamic_attributes.as_dict,
            "long_term_memories": [memory.as_dict for memory in self.long_term_memories]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create from dictionary."""
        if not data:
            raise ValueError("Cannot create UserProfile from empty data")
        
        user_id = data.get("user_id")
        if not user_id:
            raise ValueError("UserProfile requires a user_id")
        
        character_data = data.get("character_sheet", {})
        character_sheet = CharacterSheet.from_dict(character_data)
        
        attributes_data = data.get("dynamic_attributes", {})
        dynamic_attributes = DynamicAttributes.from_dict(attributes_data)
        
        memories_data = data.get("long_term_memories", [])
        memories = [Memory.from_dict(m) for m in memories_data]
        
        return cls(
            user_id=user_id,
            username=data.get("username"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            introduced=data.get("introduced", False),
            character_sheet=character_sheet,
            dynamic_attributes=dynamic_attributes,
            long_term_memories=memories
        )
