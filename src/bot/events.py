"""Event handlers for Discord events."""

import asyncio
import json
from datetime import datetime, timedelta
from discord.ext import tasks

from src.bot.commands import handle_message, process_character_creation_response

# Dictionary to track user inactivity
INACTIVITY_THRESHOLD_MINUTES = 15

async def register_events(bot):
    """Register all event handlers for the bot."""
    
    @bot.event
    async def on_ready():
        """Called when the bot is ready and connected to Discord."""
        print(f"Bot is online! Logged in as {bot.user}")
        bot.user_inactivity = {}  # user_id -> datetime
        check_inactivity.start()
    
    @bot.event
    async def on_message(message):
        """Called when a message is received."""
        # Process commands first (like !status, !profile)
        await bot.process_commands(message)
        
        # Ignore messages from the bot itself or empty messages
        if message.author == bot.user or not message.content:
            return
        
        user_id = str(message.author.id)
        content = message.content.strip()
        
        # Update inactivity tracker
        bot.user_inactivity[user_id] = datetime.now()
        
        # Add to short-term memory
        bot.memory_manager.add_to_short_term(user_id, "user", content)
        
        # Check if we need to trim and summarize memory
        bot.memory_manager.trim_and_summarize_if_needed(user_id, bot.profile_manager, bot.llm_client)
        
        # Get current state
        state = bot.state_manager.get_state(user_id)
        
        # Handle message based on state
        if state == "character_creation":
            # Process as character creation response
            await process_character_creation_response(user_id, content, message.channel, bot)
            return
        elif state == "adventure":
            # Process as adventure action
            await handle_message(user_id, content, message=message, bot=bot)
            return
        else:
            # Regular conversation - build prompt based on state
            await handle_regular_message(bot, message, user_id, content)
    
    @bot.event
    async def on_member_join(member):
        """Called when a new member joins the server."""
        user_id = str(member.id)
        username = member.display_name
        
        # Create default profile if not exists
        profile = bot.profile_manager.load_profile(user_id)
        
        # Set username
        bot.profile_manager.set_username(user_id, username)
        
        # Send welcome message
        try:
            welcome_message = (
                f"Welcome, {member.mention}! I am Lachesis, an ancient guide with millennia of experience. "
                f"I can help you create a character and embark on adventures. "
                f"Type `!character` to create your character or `!help` to see what I can do."
            )
            
            # Find a general or welcome channel to send to
            general_channel = None
            for channel in member.guild.text_channels:
                if channel.name in ['general', 'welcome', 'introductions', 'lobby']:
                    general_channel = channel
                    break
            
            if general_channel:
                await general_channel.send(welcome_message)
            else:
                # DM if no appropriate channel found
                await member.send(welcome_message)
                
        except Exception as e:
            print(f"Error welcoming new member {user_id}: {e}")
    
    @bot.event
    async def on_reaction_add(reaction, user):
        """Called when a reaction is added to a message."""
        # Ignore bot's own reactions
        if user.bot:
            return
        
        user_id = str(user.id)
        
        # Check if this is a reaction to a bot message
        if reaction.message.author == bot.user:
            # This could be used for menu selection, adventure choices, etc.
            await handle_reaction(bot, reaction, user_id)
    
    @tasks.loop(minutes=2)
    async def check_inactivity():
        """Periodic task to check for inactive users and send reminders."""
        now = datetime.now()
        for user_id, last_time in list(bot.user_inactivity.items()):
            # Check if user has been inactive for threshold period
            if now - last_time > timedelta(minutes=INACTIVITY_THRESHOLD_MINUTES):
                # Only remind users who are in an active adventure
                state = bot.state_manager.get_state(user_id)
                if state in ["adventure", "character_creation"]:
                    try:
                        user = await bot.fetch_user(int(user_id))
                        if user:
                            msg = f"Hey {user.mention}, are you still with us? Let me know when you're ready to continue."
                            # Try to DM first
                            try:
                                await user.send(msg)
                                bot.memory_manager.add_to_short_term(user_id, "assistant", msg)
                            except:
                                # If DM fails, try to find a recent channel
                                metadata = bot.state_manager.get_state_metadata(user_id)
                                last_channel_id = metadata.get("last_channel_id")
                                if last_channel_id:
                                    try:
                                        channel = await bot.fetch_channel(int(last_channel_id))
                                        await channel.send(msg)
                                        bot.memory_manager.add_to_short_term(user_id, "assistant", msg)
                                    except:
                                        pass
                    except Exception as e:
                        print(f"Error reminding inactive user {user_id}: {e}")

async def handle_regular_message(bot, message, user_id, content):
    """Handle a regular message in default/menu state."""
    channel = message.channel
    
    # Store the channel ID for future reference
    bot.state_manager.update_state_metadata(user_id, {"last_channel_id": str(channel.id)})
    
    # Build prompt based on user state
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    short_term = bot.memory_manager.get_short_term_history(user_id)
    profile = bot.profile_manager.load_profile(user_id)
    
    # Get long-term memories
    memories = profile.get("long_term_memories", [])
    memories_text = "\n".join([f"- {m.get('summary', '')}" for m in memories])
    
    # Define available functions
    available_functions = bot.function_dispatcher.get_function_descriptions()
    
    # Check if user has been introduced
    introduced = profile.get("introduced", False)
    
    # Get the appropriate system prompt
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
    
    # If the user has not been introduced, include a note about introduction
    if not introduced:
        system_instructions += "\n\nThis is your first interaction with this user. Introduce yourself briefly."
    
    # Construct the full prompt with message history
    prompt = f"<|im_start|>system\n{system_instructions}\n<|im_end|>\n"
    for role, msg_content in short_term:
        prompt += f"<|im_start|>{role}\n{msg_content}\n<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"
    
    try:
        async with channel.typing():
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
            await send_message_in_parts(bot, channel, user_id, response)
            
            # If this is the first time interacting, mark as introduced
            if not introduced:
                bot.profile_manager.mark_introduction_done(user_id)
    
    except Exception as e:
        print(f"Error generating response: {e}")
        await channel.send("Oops, something went wrong. Please try again later.")

async def handle_reaction(bot, reaction, user_id):
    """Handle a reaction to a bot message."""
    # This could be extended for interactive menus, decision points, etc.
    # For now, just log the reaction
    emoji = reaction.emoji
    message_id = reaction.message.id
    channel_id = reaction.message.channel.id
    
    print(f"User {user_id} reacted with {emoji} to message {message_id} in channel {channel_id}")
    
    # Example: Adventure choice selection via reactions
    state = bot.state_manager.get_state(user_id)
    if state == "adventure":
        metadata = bot.state_manager.get_state_metadata(user_id)
        
        # Check if this message is a choice message
        waiting_for_choice = metadata.get("waiting_for_choice", False)
        choice_message_id = metadata.get("choice_message_id")
        
        if waiting_for_choice and str(message_id) == str(choice_message_id):
            # Get the choices and their reactions
            choices = metadata.get("choices", {})
            
            # Find which choice this reaction corresponds to
            choice_key = None
            for key, choice_emoji in choices.items():
                if str(emoji) == choice_emoji:
                    choice_key = key
                    break
            
            if choice_key:
                # Process the choice
                adventure_id = metadata.get("current_adventure")
                if adventure_id:
                    adventure_manager = bot.adventure_manager
                    next_scene = adventure_manager.advance_scene(adventure_id, choice_key)
                    
                    if next_scene:
                        # Clear the choice state
                        bot.state_manager.update_state_metadata(user_id, {
                            "waiting_for_choice": False,
                            "choice_message_id": None,
                            "choices": {}
                        })
                        
                        # Send the new scene description
                        channel = reaction.message.channel
                        await channel.send(next_scene.get("description", "You continue your adventure..."))
                        
                        # If this scene has options, present them
                        options = next_scene.get("options", [])
                        if options:
                            await present_options(bot, user_id, channel, options)

async def present_options(bot, user_id, channel, options):
    """Present adventure options to the user."""
    # Create a message with the options
    options_text = "**What will you do?**\n\n"
    choices = {}
    
    # Define some emojis for choices
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    
    for i, option in enumerate(options):
        if i < len(emojis):
            emoji = emojis[i]
            options_text += f"{emoji} {option['text']}\n"
            choices[option['next']] = emoji
    
    # Send the options message
    msg = await channel.send(options_text)
    
    # Add reactions for each option
    for emoji in choices.values():
        await msg.add_reaction(emoji)
    
    # Update state to record that we're waiting for a choice
    bot.state_manager.update_state_metadata(user_id, {
        "waiting_for_choice": True,
        "choice_message_id": str(msg.id),
        "choices": choices
    })

async def send_message_in_parts(bot, channel, user_id, full_text):
    """Split and send a message in parts if it's too long."""
    # Split on two or more newlines to separate into messages
    segments = [seg.strip() for seg in full_text.split("\n\n") if seg.strip()]
    for seg in segments:
        bot.memory_manager.add_to_short_term(user_id, "assistant", seg)
        await channel.send(seg)
        # Small delay to make messages appear more natural
        await asyncio.sleep(0.5)