"""LLM integration module for the Lachesis Discord bot."""

from src.llm.client import LLMClient
from src.llm.prompts import (
    build_system_prompt,
    build_full_prompt,
    build_character_creation_prompt,
    build_memory_summarization_prompt,
    build_adventure_continuation_prompt,
    build_dynamic_question_prompt
)

__all__ = [
    'LLMClient',
    'build_system_prompt',
    'build_full_prompt',
    'build_character_creation_prompt',
    'build_memory_summarization_prompt',
    'build_adventure_continuation_prompt',
    'build_dynamic_question_prompt'
]