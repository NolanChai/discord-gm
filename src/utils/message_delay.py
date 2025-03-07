"""
Message delay utilities for Lachesis bot.

This module provides functions for calculating natural typing and
message delays to make the bot's responses feel more human-like.
"""

import asyncio
import random
import math
import re
from typing import Optional

class MessageDelayManager:
    """
    Manager for message delays.
    
    Calculates and provides natural typing and message delays
    to make the bot's responses feel more human-like.
    """
    
    def __init__(self):
        """Initialize the message delay manager."""
        # Typing speed in characters per second
        self.typing_speed = 50
        
        # Delay constants
        self.min_typing_delay = 0.5
        self.max_typing_delay = 5.0
        self.min_segment_delay = 0.5
        self.max_segment_delay = 3.0
        
        # For emotion-based timing variations
        self.emotion_modifiers = {
            "excited": 1.2,
            "angry": 1.3,
            "sad": 0.8,
            "thoughtful": 0.7,
            "neutral": 1.0
        }

    def calculate_typing_delay(self, message: str) -> float:
        """
        Calculate a natural typing delay for a message.
        
        Args:
            message (str): Message to calculate delay for
            
        Returns:
            float: Typing delay in seconds
        """
        # Base delay on message length
        char_count = len(message)
        delay = char_count / self.typing_speed
        
        # Add variation
        delay *= random.uniform(0.8, 1.2)
        
        # Ensure within bounds
        delay = min(max(delay, self.min_typing_delay), self.max_typing_delay)
        
        return delay
    
    def calculate_reading_delay(self, message: str) -> float:
        """
        Calculate a natural reading delay for a message.
        
        Args:
            message (str): Message to calculate delay for
            
        Returns:
            float: Reading delay in seconds
        """
        # Estimate word count (roughly 5 characters per word)
        word_count = len(message) / 5
        
        # Assume reading speed of 3 words per second
        delay = word_count / 3
        
        # Add variation
        delay *= random.uniform(0.9, 1.1)
        
        # Ensure minimum delay
        delay = max(delay, 0.5)
        
        return delay
    
    def calculate_response_delay(self, message: str, emotion: str = "neutral") -> float:
        """
        Calculate a natural response delay for a message.
        
        Args:
            message (str): Message to calculate delay for
            emotion (str): Emotion modifier
            
        Returns:
            float: Response delay in seconds
        """
        # Base delay on complexity
        complexity = self._estimate_complexity(message)
        delay = 1.0 + (complexity * 0.5)
        
        # Apply emotion modifier
        modifier = self.emotion_modifiers.get(emotion, 1.0)
        delay *= modifier
        
        # Add variation
        delay *= random.uniform(0.8, 1.2)
        
        return delay
    
    def _estimate_complexity(self, message: str) -> float:
        """
        Estimate the complexity of a message.
        
        Args:
            message (str): Message to estimate complexity for
            
        Returns:
            float: Complexity score (0-5)
        """
        # Simple heuristics for complexity
        words = message.split()
        
        # Length factor (longer messages are more complex)
        length_factor = min(len(words) / 20, 2.5)
        
        # Vocabulary factor (longer words = more complex)
        avg_word_length = sum(len(word) for word in words) / max(len(words), 1)
        vocabulary_factor = min((avg_word_length - 3) / 2, 1.5)
        if vocabulary_factor < 0:
            vocabulary_factor = 0
        
        # Question factor (questions need more thinking)
        question_factor = 1.0 if '?' in message else 0.0
        
        # Combine factors
        complexity = length_factor + vocabulary_factor + question_factor
        return min(complexity, 5.0)
    
    async def delay_typing(self, message: str) -> None:
        """
        Wait for a natural typing delay.
        
        Args:
            message (str): Message to calculate delay for
        """
        delay = self.calculate_typing_delay(message)
        await asyncio.sleep(delay)
    
    async def delay_reading(self, message: str) -> None:
        """
        Wait for a natural reading delay.
        
        Args:
            message (str): Message to calculate delay for
        """
        delay = self.calculate_reading_delay(message)
        await asyncio.sleep(delay)
    
    async def delay_response(self, message: str, emotion: str = "neutral") -> None:
        """
        Wait for a natural response delay.
        
        Args:
            message (str): Message to calculate delay for
            emotion (str): Emotion modifier
        """
        delay = self.calculate_response_delay(message, emotion)
        await asyncio.sleep(delay)
    
    async def delay_between_segments(
        self, current_segment: str, previous_segment: Optional[str] = None
    ) -> None:
        """
        Wait for a natural delay between message segments.
        
        Args:
            current_segment (str): Current message segment
            previous_segment (Optional[str]): Previous message segment
        """
        # Base delay on segment transitions
        delay = 1.0
        
        # If previous segment exists, analyze the transition
        if previous_segment:
            # Longer delay after questions or exclamations
            if re.search(r'[?!]$', previous_segment):
                delay += 0.5
            
            # Longer delay for topic changes (estimated by lack of common words)
            prev_words = set(re.findall(r'\w+', previous_segment.lower()))
            curr_words = set(re.findall(r'\w+', current_segment.lower()))
            
            common_words = prev_words.intersection(curr_words)
            if len(common_words) < min(len(prev_words), len(curr_words)) * 0.3:
                delay += 0.5
        
        # Add variation
        delay *= random.uniform(0.8, 1.2)
        
        # Ensure within bounds
        delay = min(max(delay, self.min_segment_delay), self.max_segment_delay)
        
        await asyncio.sleep(delay)

# Create a global instance for easy import
delay_manager = MessageDelayManager()