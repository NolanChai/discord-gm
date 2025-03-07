"""
Lachesis Discord Bot - Main Entry Point

This file initializes and runs the Lachesis Discord bot,
loading necessary dependencies and managers.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv

from src.bot.discord_client import create_bot
from src.llm.client import LLMClient
from src.managers.profile_manager import ProfileManager
from src.managers.memory_manager import MemoryManager
from src.managers.state_manager import StateManager
from src.managers.adventure_manager import AdventureManager
from src.utils.function_dispatcher import FunctionDispatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("lachesis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("lachesis")

async def main():
    """Main entry point for the Lachesis Discord bot."""
    
    # Load environment variables
    load_dotenv()
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    llm_api_base = os.getenv("LLM_API_BASE")
    model_name = os.getenv("MODEL_NAME", "mistral-7b-instruct")
    
    if not discord_token:
        logger.error("Missing DISCORD_BOT_TOKEN in environment variables!")
        raise ValueError("Missing DISCORD_BOT_TOKEN in environment variables!")
    
    # Create data directories if they don't exist
    os.makedirs("data/users", exist_ok=True)
    os.makedirs("data/adventures", exist_ok=True)
    os.makedirs("data/schemas", exist_ok=True)
    
    # Initialize managers
    logger.info("Initializing managers and clients...")
    
    llm_client = LLMClient(api_base=llm_api_base, model_name=model_name)
    profile_manager = ProfileManager("data/users")
    memory_manager = MemoryManager("data/users")
    state_manager = StateManager("data/users")
    adventure_manager = AdventureManager("data/adventures")
    function_dispatcher = FunctionDispatcher()
    
    # Register function handlers
    register_function_handlers(function_dispatcher)
    
    # Create and run bot
    logger.info("Starting Discord bot...")
    bot = create_bot(
        discord_token=discord_token,
        llm_client=llm_client,
        profile_manager=profile_manager,
        memory_manager=memory_manager,
        state_manager=state_manager,
        adventure_manager=adventure_manager,
        function_dispatcher=function_dispatcher
    )
    
    try:
        await bot.start(discord_token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        await bot.close()
    except Exception as e:
        logger.error(f"Bot crashed with error: {e}")
        await bot.close()

def register_function_handlers(dispatcher):
    """Register all function handlers with the dispatcher."""
    
    from src.bot.commands import (
        start_adventure, create_character, update_character,
        execute_script, continue_adventure, display_profile
    )
    
    dispatcher.register_function("start_adventure", start_adventure)
    dispatcher.register_function("create_character", create_character)
    dispatcher.register_function("update_character", update_character)
    dispatcher.register_function("execute_script", execute_script)
    dispatcher.register_function("continue_adventure", continue_adventure)
    dispatcher.register_function("display_profile", display_profile)

if __name__ == "__main__":
    asyncio.run(main())