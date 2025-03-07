from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

@dataclass
class Memory:
    """A memory entry for long-term storage."""
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
class ConversationMemory:
    """A collection of conversation memories."""
    user_id: str
    short_term: List[tuple] = field(default_factory=list)  # List of (role, content) tuples
    last_summarized: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "short_term": self.short_term,
            "last_summarized": self.last_summarized,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMemory':
        """Create from dictionary."""
        if not data:
            raise ValueError("Cannot create ConversationMemory from empty data")
        
        user_id = data.get("user_id")
        if not user_id:
            raise ValueError("ConversationMemory requires a user_id")
        
        return cls(
            user_id=user_id,
            short_term=data.get("short_term", []),
            last_summarized=data.get("last_summarized"),
            last_updated=data.get("last_updated", datetime.now().isoformat())
        )


@dataclass
class MemorySummary:
    """A summary of multiple memories."""
    user_id: str
    summary: str
    source_memories: List[str] = field(default_factory=list)  # List of memory IDs or timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "summary": self.summary,
            "source_memories": self.source_memories,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemorySummary':
        """Create from dictionary."""
        if not data:
            raise ValueError("Cannot create MemorySummary from empty data")
        
        user_id = data.get("user_id")
        if not user_id:
            raise ValueError("MemorySummary requires a user_id")
        
        summary = data.get("summary")
        if not summary:
            raise ValueError("MemorySummary requires a summary")
        
        return cls(
            user_id=user_id,
            summary=summary,
            source_memories=data.get("source_memories", []),
            created_at=data.get("created_at", datetime.now().isoformat())
        )