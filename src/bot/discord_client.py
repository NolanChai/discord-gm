"""
Discord client setup for Lachesis bot.

This module handles the creation and configuration of the Discord bot client.
"""

import discord
from discord.ext import commands
import logging
import asyncio

from src.bot.events import register_events

logger = logging.getLogger("lachesis.discord")

def create_bot(
    discord_token, 
    llm_client, 
    profile_manager, 
    memory_manager, 
    state_manager, 
    adventure_manager,
    function_dispatcher
):
    """
    Create and configure the Discord bot instance.
    
    Args:
        discord_token (str): Discord bot token
        llm_client (LLMClient): LLM client for text generation
        profile_manager (ProfileManager): Manager for user profiles
        memory_manager (MemoryManager): Manager for conversation memory
        state_manager (StateManager): Manager for user state
        adventure_manager (AdventureManager): Manager for adventures
        function_dispatcher (FunctionDispatcher): Function call dispatcher
        
    Returns:
        commands.Bot: Configured Discord bot
    """
    # Set up intents (permissions)
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.reactions = True
    intents.guild_messages = True
    intents.dm_messages = True
    
    # Create bot instance
    bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
    
    # Attach managers and clients to bot for access in event handlers
    bot.llm_client = llm_client
    bot.profile_manager = profile_manager
    bot.memory_manager = memory_manager
    bot.state_manager = state_manager
    bot.adventure_manager = adventure_manager
    bot.function_dispatcher = function_dispatcher
    
    # Dictionary to store user contexts and information
    bot.user_contexts = {}
    
    # Register command error handler
    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            # Silently ignore command not found errors
            return
        
        logger.error(f"Command error: {error}")
        await ctx.send(f"Error: {error}")
    
    # Register basic commands
    @bot.command(name="help")
    async def help_command(ctx):
        """Display help information about Lachesis."""
        help_text = (
            "# Lachesis - Weaver of Fate\n\n"
            "I am Lachesis, one of the three Fates who measure the thread of life. "
            "I can guide you through adventures and help shape your destiny.\n\n"
            
            "**Commands:**\n"
            "- `!character` - Create or view your character\n"
            "- `!adventure` - Start a new adventure\n"
            "- `!profile` - View your character profile\n"
            "- `!help` - Show this help message\n\n"
            
            "You can also simply mention me or talk to me directly to interact."
        )
        await ctx.send(help_text)
    
    @bot.command(name="character")
    async def character_command(ctx):
        """Create or display character."""
        user_id = str(ctx.author.id)
        await bot.function_dispatcher.dispatch(
            {"name": "create_character", "args": {}},
            user_id=user_id,
            message=ctx,
            bot=bot
        )
    
    @bot.command(name="adventure")
    async def adventure_command(ctx):
        """Start an adventure."""
        user_id = str(ctx.author.id)
        await bot.function_dispatcher.dispatch(
            {"name": "start_adventure", "args": {}},
            user_id=user_id,
            message=ctx,
            bot=bot
        )
    
    @bot.command(name="profile")
    async def profile_command(ctx):
        """Display character profile."""
        user_id = str(ctx.author.id)
        await bot.function_dispatcher.dispatch(
            {"name": "display_profile", "args": {}},
            user_id=user_id,
            message=ctx,
            bot=bot
        )
    
    # Register event handlers using setup_hook
    @bot.event
    async def setup_hook():
        """Set up the bot before it starts."""
        await register_events(bot)
    
    return bot