import asyncio
import os
from dotenv import load_dotenv

from src.bot.discord_client import create_bot
from src.llm.client import LLMClient
from src.managers.profile_manager import ProfileManager
from src.managers.memory_manager import MemoryManager
from src.managers.state_manager import StateManager
from src.utils.function_dispatcher import FunctionDispatcher

async def main():
    """Main entry point for the Lachesis Discord bot."""
    # Load environment variables
    load_dotenv()
    
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    llm_api_base = os.getenv("LM_API_BASE", "http://localhost:1234/v1")
    model_name = os.getenv("MODEL_NAME", "YourModelNameHere")
    
    if not discord_token:
        raise ValueError("Missing DISCORD_BOT_TOKEN in environment variables!")
    
    # Initialize managers
    llm_client = LLMClient(api_base=llm_api_base, model_name=model_name)
    profile_manager = ProfileManager("data/users")
    memory_manager = MemoryManager("data/users")
    state_manager = StateManager("data/users")
    function_dispatcher = FunctionDispatcher()
    
    # Register function handlers
    register_function_handlers(function_dispatcher, profile_manager, memory_manager, state_manager)
    
    # Create and run bot
    bot = create_bot(
        discord_token=discord_token,
        llm_client=llm_client,
        profile_manager=profile_manager,
        memory_manager=memory_manager,
        state_manager=state_manager,
        function_dispatcher=function_dispatcher
    )
    
    await bot.start(discord_token)

def register_function_handlers(dispatcher, profile_manager, memory_manager, state_manager):
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
