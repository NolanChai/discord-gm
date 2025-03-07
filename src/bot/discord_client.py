import discord
from discord.ext import commands, tasks
import json
from datetime import datetime, timedelta
import asyncio

def create_bot(discord_token, llm_client, profile_manager, memory_manager, state_manager, function_dispatcher):
    """Create and configure the Discord bot."""
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)
    
    # Store managers as bot attributes
    bot.llm_client = llm_client
    bot.profile_manager = profile_manager
    bot.memory_manager = memory_manager
    bot.state_manager = state_manager
    bot.function_dispatcher = function_dispatcher
    
    # For inactivity tracking per user
    bot.user_inactivity = {}  # user_id -> datetime
    bot.INACTIVITY_THRESHOLD_MINUTES = 15
    
    # Register event handlers
    @bot.event
    async def on_ready():
        """Event fired when the bot is ready and connected."""
        print(f"Bot is online! Logged in as {bot.user}")
        periodic_tasks.start()
    
    @bot.event
    async def on_message(message):
        """Event fired when a message is received."""
        await bot.process_commands(message)
        if message.author == bot.user or not message.content:
            return
            
        user_id = str(message.author.id)
        content = message.content.strip()
        
        # Update inactivity tracker
        bot.user_inactivity[user_id] = datetime.now()
        
        # Add message to short-term memory
        bot.memory_manager.add_to_short_term(user_id, "user", content)
        
        # Get the current state for this user
        state = bot.state_manager.get_state(user_id)
        
        # Build prompt based on state
        prompt = build_prompt(bot, user_id, state)
        
        try:
            async with message.channel.typing():
                response = await bot.llm_client.generate_response(prompt)
            
            # Check for function calls
            function_call = bot.function_dispatcher.extract_function_call(response)
            if function_call:
                await bot.function_dispatcher.dispatch(
                    function_call,
                    user_id=user_id,
                    message=message,
                    bot=bot
                )
            else:
                # Send regular message response
                await send_message_in_parts(bot, message.channel, user_id, response)
                
                # If this is the first time interacting, mark as introduced
                profile = bot.profile_manager.load_profile(user_id)
                if not profile.get("introduced", False):
                    bot.profile_manager.mark_introduction_done(user_id)
                
        except Exception as e:
            print(f"Error generating response: {e}")
            await message.channel.send("Oops, something went wrong. Please try again later.")
    
    # Register commands
    @bot.command(name="status")
    async def status_command(ctx):
        """Command to show the user's current status."""
        user_id = str(ctx.author.id)
        profile = bot.profile_manager.load_profile(user_id)
        char_sheet = profile.get("character_sheet", {})
        dynamic = profile.get("dynamic_attributes", {})
        ltm_count = len(profile.get("long_term_memories", []))
        
        await ctx.send(
            f"**Your Character**\nName: {char_sheet.get('name', 'Not set')}\n"
            f"Race: {char_sheet.get('race', 'Not set')}\n"
            f"Class: {char_sheet.get('class', 'Not set')}\n"
            f"Stats: {char_sheet.get('stats', {})}\n\n"
            f"**Dynamic Attributes:** {dynamic}\n"
            f"**Long-Term Memories:** {ltm_count} stored."
        )
    
    @bot.command(name="profile")
    async def profile_command(ctx):
        """Command to display the user's character profile."""
        user_id = str(ctx.author.id)
        await display_profile(bot, user_id, ctx.channel)
    
    @bot.command(name="adventure")
    async def adventure_command(ctx):
        """Command to start or continue an adventure."""
        user_id = str(ctx.author.id)
        await bot.function_dispatcher.dispatch(
            {"name": "start_adventure", "args": {}},
            user_id=user_id,
            message=ctx,
            bot=bot
        )
    
    @bot.command(name="character")
    async def character_command(ctx):
        """Command to start character creation."""
        user_id = str(ctx.author.id)
        await bot.function_dispatcher.dispatch(
            {"name": "create_character", "args": {}},
            user_id=user_id,
            message=ctx,
            bot=bot
        )
    
    # Utility functions
    async def display_profile(bot, user_id, channel):
        """Display a user's character profile in a channel."""
        profile = bot.profile_manager.load_profile(user_id)
        profile_json = json.dumps(profile.get("character_sheet", {}), indent=2)
        message_text = (
            f"### Your Character Profile\n\n"
            f"```json\n{profile_json}\n```"
        )
        await send_message_in_parts(bot, channel, user_id, message_text)
    
    async def send_message_in_parts(bot, channel, user_id, full_text):
        """Split and send a message in parts if it's too long."""
        # Split on two or more newlines to separate into messages
        segments = [seg.strip() for seg in full_text.split("\n\n") if seg.strip()]
        for seg in segments:
            bot.memory_manager.add_to_short_term(user_id, "assistant", seg)
            await channel.send(seg)
            # Small delay to make messages appear more natural
            await asyncio.sleep(0.5)
    
    def build_prompt(bot, user_id, state):
        """Build a prompt based on the user's state."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        short_term = bot.memory_manager.get_short_term_history(user_id)
        profile = bot.profile_manager.load_profile(user_id)
        
        # Get long-term memories
        memories = profile.get("long_term_memories", [])
        memories_text = "\n".join([f"- {m.get('summary', '')}" for m in memories])
        
        # Define available functions
        available_functions = (
            "Available functions:\n"
            "1. start_adventure(user_id, mentions): start a new adventure\n"
            "2. create_character(user_id): initiate character creation\n"
            "3. update_character(user_id, field, value): update character sheet\n"
            "4. execute_script(script_name, args): run a local script\n"
            "5. continue_adventure(user_id): continue the adventure\n"
            "6. display_profile(user_id): show character profile\n"
        )
        
        # Check if user has been introduced
        introduced = profile.get("introduced", False)
        
        # Get the appropriate system prompt based on state
        if state == "introduction":
            system_instructions = (
                f"You are Lachesis, an ancient, somber, and introspective guide with millennia of experience. "
                f"Today's date/time: {current_time}.\n\n"
                "You've just been pinged by a user in a Discord server. "
                "Please reply with a brief introduction of yourself and your purpose.\n\n"
                "Be concise and natural. Discord is a chat platform, so you can send multiple short messages instead of one long one."
            )
        elif state == "character_creation":
            system_instructions = (
                f"You are Lachesis, guiding {profile.get('username', 'a user')} through character creation. "
                f"Today's date/time: {current_time}.\n\n"
                "Ask creative and open-ended questions to build their character sheet. "
                "Based on their answers, gauge their personality and capabilities to determine stats.\n\n"
                "Send one question at a time and wait for their response. "
                "After a few questions, generate a character sheet with stats, race, class, and other details."
            )
        elif state == "adventure":
            system_instructions = (
                f"You are Lachesis, running an adventure for {profile.get('username', 'a user')}. "
                f"Today's date/time: {current_time}.\n\n"
                "Act as a dynamic narrator, describing scenes and responding to the user's actions. "
                "Be concise but evocative in your descriptions.\n\n"
                f"Character Sheet:\n{json.dumps(profile.get('character_sheet', {}), indent=2)}\n\n"
                f"Current Attributes:\n{json.dumps(profile.get('dynamic_attributes', {}), indent=2)}"
            )
        else:  # Default/menu state
            system_instructions = (
                f"You are Lachesis, an ancient, somber, and introspective guide with millennia of experience. "
                f"Today's date/time: {current_time}.\n\n"
                "When replying, split your answer into multiple messages if needed.\n"
                "Do not include any function call markers in your plain text reply. "
                "If a function call is needed, output it enclosed in <|function_call|> and <|end_function_call|>.\n\n"
                f"User's Character Sheet:\n{json.dumps(profile.get('character_sheet', {}), indent=2)}\n\n"
                f"Dynamic Attributes:\n{json.dumps(profile.get('dynamic_attributes', {}), indent=2)}\n\n"
                f"Relevant Memories:\n{memories_text}\n\n"
                f"{available_functions}\n\n"
                "If a user's message implies an action (for example, starting a game or updating their character), "
                "output a JSON function call. Otherwise, produce plain-text messages."
            )
        
        # Construct the full prompt with message history
        prompt = f"<|im_start|>system\n{system_instructions}\n<|im_end|>\n"
        for role, content in short_term:
            prompt += f"<|im_start|>{role}\n{content}\n<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"
        
        return prompt
    
    # Periodic tasks
    @tasks.loop(minutes=2)
    async def periodic_tasks():
        """Periodic tasks that run on a schedule."""
        await handle_inactivity_check(bot)
    
    async def handle_inactivity_check(bot):
        """Check for inactive users and remind them."""
        now = datetime.now()
        for user_id, last_time in list(bot.user_inactivity.items()):
            if now - last_time > timedelta(minutes=bot.INACTIVITY_THRESHOLD_MINUTES):
                try:
                    user = await bot.fetch_user(int(user_id))
                    if user:
                        msg = f"Hey {user.mention}, are you still with us? Let me know when you're ready to continue our adventure!"
                        await user.send(msg)
                        bot.memory_manager.add_to_short_term(user_id, "assistant", msg)
                except Exception as e:
                    print(f"Error DMing user {user_id}: {e}")
    
    return bot
