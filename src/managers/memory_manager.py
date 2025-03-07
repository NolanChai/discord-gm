import os
import json
from datetime import datetime
from collections import deque

class MemoryManager:
    """
    Manages short-term and long-term memory for conversations.
    """
    def __init__(self, data_dir, short_term_limit=20):
        """
        Initialize the memory manager.
        
        Args:
            data_dir: Directory for storing memory files
            short_term_limit: Maximum number of messages to keep in short-term memory
        """
        self.data_dir = data_dir
        self.short_term_limit = short_term_limit
        self.short_term_memory = {}  # user_id -> deque of (role, content) tuples
        os.makedirs(data_dir, exist_ok=True)
    
    def _get_user_dir(self, user_id):
        """Get the directory for a specific user, creating it if it doesn't exist."""
        user_dir = os.path.join(self.data_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def _get_memory_path(self, user_id):
        """Get the path to a user's memory file."""
        return os.path.join(self._get_user_dir(user_id), "memory.json")
    
    def add_to_short_term(self, user_id, role, content):
        """
        Add a message to short-term memory.
        
        Args:
            user_id: Discord user ID
            role: Message role (user, assistant, system)
            content: Message content
            
        Returns:
            bool: Success or failure
        """
        if user_id not in self.short_term_memory:
            self.short_term_memory[user_id] = deque(maxlen=self.short_term_limit)
        
        self.short_term_memory[user_id].append((role, content))
        return True
    
    def get_short_term_history(self, user_id):
        """
        Get the short-term history for a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            list: List of (role, content) tuples
        """
        if user_id not in self.short_term_memory:
            self.short_term_memory[user_id] = deque(maxlen=self.short_term_limit)
        
        return list(self.short_term_memory[user_id])
    
    def trim_and_summarize_if_needed(self, user_id, profile_manager, llm_client=None):
        """
        Check if short-term memory exceeds limit, and if so, summarize
        the oldest messages and move them to long-term memory.
        
        Args:
            user_id: Discord user ID
            profile_manager: ProfileManager instance
            llm_client: Optional LLMClient for generating summaries
            
        Returns:
            bool: Whether a summary was generated
        """
        if user_id not in self.short_term_memory:
            return False
        
        if len(self.short_term_memory[user_id]) >= self.short_term_limit * 0.8:
            # Get the oldest messages (first half)
            old_messages = list(self.short_term_memory[user_id])[:self.short_term_limit // 2]
            
            # Generate a summary of these messages
            if llm_client:
                # Use LLM to generate a summary
                summary = self._generate_llm_summary(old_messages, llm_client)
            else:
                # Use simple summarization
                summary = self._summarize_messages(old_messages)
            
            # Add to long-term memory
            profile_manager.add_long_term_memory(user_id, {
                "summary": summary,
                "timestamp": datetime.now().isoformat(),
                "type": "conversation"
            })
            
            # Remove the summarized messages from short-term memory
            self.short_term_memory[user_id] = deque(
                list(self.short_term_memory[user_id])[self.short_term_limit // 2:],
                maxlen=self.short_term_limit
            )
            
            return True
        
        return False
    
    async def _generate_llm_summary(self, messages, llm_client):
        """
        Use the LLM to generate a summary of messages.
        
        Args:
            messages: List of (role, content) tuples
            llm_client: LLMClient instance
            
        Returns:
            str: Summary of the messages
        """
        # Convert messages to a single text block
        messages_text = "\n".join([f"{role}: {content}" for role, content in messages])
        
        # Build a prompt for summarization
        prompt = (
            "<|im_start|>system\n"
            "Summarize the following conversation concisely, "
            "focusing on key points, decisions, and character development.\n"
            "<|im_end|>\n"
            f"<|im_start|>user\n{messages_text}\n<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        
        try:
            # Generate summary
            summary = await llm_client.generate_response(prompt, max_tokens=100)
            return summary
        except Exception as e:
            print(f"Error generating summary: {e}")
            return self._summarize_messages(messages)  # Fallback to simple summary
    
    def _summarize_messages(self, messages):
        """
        Create a simple summary of messages without using LLM.
        
        Args:
            messages: List of (role, content) tuples
            
        Returns:
            str: Summary of the messages
        """
        if not messages:
            return "No conversation."
        
        # Simple summary approach: extract key parts from the first and last messages
        first_role, first_content = messages[0]
        last_role, last_content = messages[-1]
        
        # Count message types
        user_msgs = sum(1 for role, _ in messages if role == "user")
        assistant_msgs = sum(1 for role, _ in messages if role == "assistant")
        
        # Get topics (very simple approach - extract the first few words of user messages)
        topics = []
        for role, content in messages:
            if role == "user" and content:
                words = content.split()[:3]
                if words:
                    topics.append(" ".join(words) + "...")
                if len(topics) >= 3:
                    break
        
        topic_str = ", ".join(topics[:3]) if topics else "unknown topics"
        
        return (
            f"Conversation with {user_msgs} user messages and {assistant_msgs} assistant replies "
            f"about {topic_str}. Started with {first_role} saying '{first_content[:30]}...' "
            f"and ended with {last_role} saying '{last_content[:30]}...'"
        )
    
    def clear_short_term(self, user_id):
        """
        Clear the short-term memory for a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            bool: Success or failure
        """
        if user_id in self.short_term_memory:
            self.short_term_memory[user_id].clear()
        return True
    
    def save_memory_to_disk(self, user_id):
        """
        Save the current memory state to disk.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            bool: Success or failure
        """
        memory_path = self._get_memory_path(user_id)
        
        try:
            memory_data = {
                "user_id": user_id,
                "short_term": list(self.short_term_memory.get(user_id, [])),
                "last_updated": datetime.now().isoformat()
            }
            
            with open(memory_path, 'w') as f:
                json.dump(memory_data, f, indent=2)
            
            return True
        except IOError as e:
            print(f"Error saving memory for {user_id}: {e}")
            return False
    
    def load_memory_from_disk(self, user_id):
        """
        Load memory from disk.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            bool: Success or failure
        """
        memory_path = self._get_memory_path(user_id)
        
        if os.path.exists(memory_path):
            try:
                with open(memory_path, 'r') as f:
                    memory_data = json.load(f)
                
                self.short_term_memory[user_id] = deque(
                    memory_data.get("short_term", []),
                    maxlen=self.short_term_limit
                )
                
                return True
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading memory for {user_id}: {e}")
        
        return False
