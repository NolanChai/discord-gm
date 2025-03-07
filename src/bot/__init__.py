"""Bot module for the Lachesis Discord bot."""

from src.bot.discord_client import create_bot
from src.bot.commands import (
    start_adventure, 
    create_character, 
    update_character, 
    execute_script, 
    continue_adventure, 
    display_profile,
    handle_message
)

__all__ = [
    'create_bot', 
    'start_adventure', 
    'create_character', 
    'update_character', 
    'execute_script', 
    'continue_adventure', 
    'display_profile',
    'handle_message'
]