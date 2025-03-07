"""
Memory Manager for Lachesis bot.

This module handles the storage and management of short-term and long-term
conversation memory.
"""

import os
import json
import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Tuple, Any, Deque

logger = logging.getLogger("lachesis.memory_manager")

class MemoryManager:
    """
    Manager for conversation memory.
    
    Handles the storage and retrieval of short-term and long-term memory
    for conversations with users.
    """
    
    def __init__(self, data_dir: str, max_short_term: int = 20):
        """
        Initialize the memory manager.
        
        Args:
            data_dir (str): Directory for storing memory data
            max_short_term (int): Maximum number of messages in short-term memory
        """
        self.data_dir = data_dir
        self.max_short_term = max_short_term
        
        # In-memory cache of short-term memory
        self.short_term_cache: Dict[str, Deque[Tuple[str, str]]] = {}
        
        os.makedirs(data_dir, exist_ok=True)
    
    def _get_memory_dir(self, user_id: str) -> str:
        """
        Get the directory for a user's memory data.
        
        Args:
            user_id (str): User ID
            
        Returns:
            str: Path to the user's memory directory
        """
        memory_dir = os.path.join(self.data_dir, user_id, "memory")
        os.makedirs(memory_dir, exist_ok=True)
        return memory_dir
    
    def add_to_short_term(self, user_id: str, role: str, content: str) -> None:
        """
        Add a message to short-term memory.
        
        Args:
            user_id (str): User ID
            role (str): Message role (user, assistant)
            content (str): Message content
        """
        # Initialize cache for this user if not exists
        if user_id not in self.short_term_cache:
            self.short_term_cache[user_id] = deque(maxlen=self.max_short_term)
        
        # Add message to cache
        self.short_term_cache[user_id].append((role, content))
        
        # Save to disk
        self._save_short_term(user_id)
    
    def get_short_term_history(self, user_id: str) -> List[Tuple[str, str]]:
        """
        Get the short-term conversation history for a user.
        
        Args:
            user_id (str): User ID
            
        Returns:
            List[Tuple[str, str]]: List of (role, content) tuples
        """
        # Load from cache if available
        if user_id in self.short_term_cache:
            return list(self.short_term_cache[user_id])
        
        # Otherwise, load from disk
        return self._load_short_term(user_id)
    
    def clear_short_term(self, user_id: str) -> None:
        """
        Clear short-term memory for a user.
        
        Args:
            user_id (str): User ID
        """
        # Clear cache
        if user_id in self.short_term_cache:
            self.short_term_cache[user_id].clear()
        
        # Clear disk
        short_term_path = os.path.join(self._get_memory_dir(user_id), "short_term.json")
        if os.path.exists(short_term_path):
            try:
                with open(short_term_path, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            except Exception as e:
                logger.error(f"Error clearing short-term memory for {user_id}: {e}")
    
    def _save_short_term(self, user_id: str) -> None:
        """
        Save short-term memory to disk.
        
        Args:
            user_id (str): User ID
        """
        if user_id not in self.short_term_cache:
            return
        
        memory_dir = self._get_memory_dir(user_id)
        short_term_path = os.path.join(memory_dir, "short_term.json")
        
        try:
            with open(short_term_path, 'w', encoding='utf-8') as f:
                json.dump(list(self.short_term_cache[user_id]), f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving short-term memory for {user_id}: {e}")
    
    def _load_short_term(self, user_id: str) -> List[Tuple[str, str]]:
        """
        Load short-term memory from disk.
        
        Args:
            user_id (str): User ID
            
        Returns:
            List[Tuple[str, str]]: List of (role, content) tuples
        """
        memory_dir = self._get_memory_dir(user_id)
        short_term_path = os.path.join(memory_dir, "short_term.json")
        
        try:
            if os.path.exists(short_term_path):
                with open(short_term_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Initialize cache
                self.short_term_cache[user_id] = deque(data, maxlen=self.max_short_term)
                return list(self.short_term_cache[user_id])
            else:
                # Initialize empty cache
                self.short_term_cache[user_id] = deque(maxlen=self.max_short_term)
                return []
        except Exception as e:
            logger.error(f"Error loading short-term memory for {user_id}: {e}")
            # Initialize empty cache on error
            self.short_term_cache[user_id] = deque(maxlen=self.max_short_term)
            return []
    
    def trim_and_summarize_if_needed(self, user_id: str, profile_manager, llm_client) -> None:
        """
        Check if short-term memory needs to be trimmed and summarized.
        
        Args:
            user_id (str): User ID
            profile_manager: ProfileManager instance
            llm_client: LLMClient instance
        """
        # Get short-term history
        history = self.get_short_term_history(user_id)
        
        # Check if we have enough messages to summarize
        if len(history) >= self.max_short_term * 0.8:
            # Get the oldest messages to summarize (keep the most recent half)
            keep_count = self.max_short_term // 2
            to_summarize = history[:-keep_count]
            
            # Only summarize if there are actually messages to summarize
            if to_summarize:
                # Create summary asynchronously
                self._create_and_store_summary(user_id, to_summarize, profile_manager, llm_client)
                
                # Keep only the most recent messages
                self.short_term_cache[user_id] = deque(history[-keep_count:], maxlen=self.max_short_term)
                self._save_short_term(user_id)
    
    async def _create_and_store_summary(
        self, user_id: str, messages: List[Tuple[str, str]], 
        profile_manager, llm_client
    ) -> None:
        """
        Create a summary of messages and store it in long-term memory.
        
        Args:
            user_id (str): User ID
            messages (List[Tuple[str, str]]): Messages to summarize
            profile_manager: ProfileManager instance
            llm_client: LLMClient instance
        """
        try:
            # Format messages for summarization
            formatted_messages = []
            for role, content in messages:
                formatted_messages.append(f"{role.upper()}: {content}")
            
            conversation_text = "\n".join(formatted_messages)
            
            # Create prompt for summarization
            prompt = (
                "Please summarize the following conversation segment in a concise paragraph. "
                "Focus on key information, decisions, and character development. "
                "This summary will be stored as a long-term memory for the user's character.\n\n"
                f"{conversation_text}\n\n"
                "Summary:"
            )
            
            # Generate summary
            summary = await llm_client.generate_response(prompt)
            
            # Store in long-term memory
            memory = {
                "type": "conversation",
                "summary": summary.strip(),
                "timestamp": datetime.now().isoformat(),
                "source": "auto-summarization"
            }
            
            profile_manager.add_long_term_memory(user_id, memory)
            logger.info(f"Created and stored conversation summary for {user_id}")
            
        except Exception as e:
            logger.error(f"Error creating conversation summary for {user_id}: {e}")