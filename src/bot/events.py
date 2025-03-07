"""
Event handlers for Discord events.

This module provides handlers for various Discord events
like message receiving, reactions, etc.
"""

import asyncio
import json
import random
import math
import re
from datetime import datetime, timedelta
from discord.ext import tasks

from src.bot.commands import handle_message, process_character_creation_response
from src.utils.message_delay import delay_manager

# Threshold for user inactivity (in minutes)
INACTIVITY_THRESHOLD_MINUTES = 15

async def register_events(bot):
    """
    Register all event handlers for the bot.
    
    Args:
        bot: Discord bot instance
    """
    
    @bot.event
    async def on_ready():
        """Called when the bot is ready and connected to Discord."""
        print(f"Bot is online! Logged in as {bot.user}")
        bot.user_inactivity = {}  # user_id -> datetime
        check_inactivity.start()
    
    @bot.event
    async def on_message(message):
        """
        Called when a message is received.
        
        Args:
            message: Discord message
        """
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
        bot.memory_manager.trim_and_summarize_if_needed(
            user_id, bot.profile_manager, bot.llm_client
        )
        
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
        """
        Called when a new member joins the server.
        
        Args:
            member: Discord member
        """
        user_id = str(member.id)
        username = member.display_name
        
        # Create default profile if not exists
        profile = bot.profile_manager.load_profile(user_id)
        
        # Set username
        bot.profile_manager.set_username(user_id, username)
        
        # Send welcome message
        try:
            welcome_message = (
                f"Welcome, {member.mention}! I am Lachesis, one of the three Fates who spin the threads of destiny. "
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
        """
        Called when a reaction is added to a message.
        
        Args:
            reaction: Discord reaction
            user: Discord user
        """
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
    """
    Handle a regular message in default/menu state.
    
    Args:
        bot: Discord bot instance
        message: Discord message
        user_id (str): User ID
        content (str): Message content
    """
    channel = message.channel
    
    print(f"\n[DEBUG] === RECEIVED MESSAGE ===")
    print(f"[DEBUG] User: {user_id}, Content: '{content}'")
    
    # Store the channel ID for future reference
    bot.state_manager.update_state_metadata(
        user_id, {"last_channel_id": str(channel.id)}
    )
    
    # Direct trigger words - immediately execute corresponding functions
    # This ensures critical functions work even if LLM doesn't output proper JSON
    content_lower = content.lower().strip()
    print(f"[DEBUG] Checking direct triggers against: '{content_lower}'")
    
    # Check for adventure keywords
    adventure_keywords = ["adventure", "quest", "journey"]
    if any(keyword in content_lower for keyword in adventure_keywords):
        print(f"[DEBUG] ❗ KEYWORD OVERRIDE: User mentioned adventure keywords")
        print(f"[DEBUG] Response does not contain function call - forcing start_adventure")
        await bot.function_dispatcher.dispatch(
            {"name": "start_adventure", "args": {}},
            user_id=user_id,
            message=message,
            bot=bot
        )
        return
    
    # Check for character keywords
    character_keywords = ["character", "create character"]
    if any(keyword in content_lower for keyword in character_keywords):
        print(f"[DEBUG] ❗ KEYWORD OVERRIDE: User mentioned character keywords")
        print(f"[DEBUG] Response does not contain function call - forcing create_character")
        await bot.function_dispatcher.dispatch(
            {"name": "create_character", "args": {}},
            user_id=user_id,
            message=message,
            bot=bot
        )
        return
    
    print(f"[DEBUG] ❌ No character triggers matched")
    
    # Check for profile keywords
    profile_triggers = ["profile", "show profile", "display profile", "character sheet", "stats"]
    for trigger in profile_triggers:
        if trigger in content_lower:
            print(f"[DEBUG] ✅ DIRECT TRIGGER MATCHED: '{trigger}' in '{content_lower}'")
            print(f"[DEBUG] Dispatching display_profile function directly")
            # Directly dispatch to profile function
            await bot.function_dispatcher.dispatch(
                {"name": "display_profile", "args": {}},
                user_id=user_id,
                message=message,
                bot=bot
            )
            return
    
    print(f"[DEBUG] ❌ No profile triggers matched")
    
    # Build prompt based on user state
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    short_term = bot.memory_manager.get_short_term_history(user_id)
    profile = bot.profile_manager.load_profile(user_id)
    
    # Get long-term memories
    memories = profile.get("long_term_memories", [])
    memories_text = "\n".join([f"- {m.get('summary', '')}" for m in memories])
    
    # Define available functions with clear examples
    function_descriptions = (
        "CRITICAL FUNCTION INSTRUCTIONS - READ CAREFULLY:\n\n"
        "When ANY of these exact phrases or close variations appear in the user's message, you MUST respond ONLY with the corresponding function call JSON, no other text:\n\n"
        
        "1. For phrases like: 'adventure', 'start adventure', 'begin an adventure', 'let's adventure', 'quest', 'journey'\n"
        "   RESPOND ONLY WITH: {\"name\": \"start_adventure\", \"args\": {}}\n\n"
        
        "2. For phrases like: 'character', 'create character', 'make character', 'new character'\n"
        "   RESPOND ONLY WITH: {\"name\": \"create_character\", \"args\": {}}\n\n"
        
        "3. For phrases like: 'profile', 'show profile', 'character sheet', 'stats'\n"
        "   RESPOND ONLY WITH: {\"name\": \"display_profile\", \"args\": {}}\n\n"
        
        "4. For phrases like: 'update character', 'change name', 'set class', 'modify stats'\n"
        "   RESPOND ONLY WITH: {\"name\": \"update_character\", \"args\": {\"field\": \"[field]\", \"value\": \"[value]\"}}\n\n"
        
        "EXAMPLES:\n"
        "User: 'I want an adventure'\n"
        "You: {\"name\": \"start_adventure\", \"args\": {}}\n\n"
        
        "User: 'Let's make a character'\n"
        "You: {\"name\": \"create_character\", \"args\": {}}\n\n"
        
        "User: 'Show my profile'\n"
        "You: {\"name\": \"display_profile\", \"args\": {}}\n\n"
        
        "IMPORTANT: DO NOT respond conversationally about adventures, characters, etc. - CALL THE FUNCTION INSTEAD"
    )
    
    # Check if user has been introduced
    introduced = profile.get("introduced", False)
    
    # Get the appropriate system prompt
    system_instructions = (
        f"You are Lachesis, one of the three Fates from ancient mythology. As a divine weaver of destiny, "
        f"you measure and determine the length of the thread of life. You speak with the authority of a deity who has "
        f"witnessed countless lifetimes and shaped the course of history. Today's date/time: {current_time}.\n\n"
        
        f"CHARACTER PERSONA:\n"
        f"- You embody ancient divine power and wisdom, speaking in a commanding but intriguing tone\n"
        f"- You refer to mortals' lives as threads in the grand tapestry of fate\n"
        f"- You are primarily a NARRATOR and GUIDE for adventures, not a counselor\n"
        f"- You use vivid, evocative language to describe scenes and settings\n"
        f"- You ALWAYS encourage users toward adventure and action rather than introspection\n"
        f"- You occasionally make subtle references to your divine nature and ability to see threads of fate\n\n"
        
        f"MESSAGING STYLE:\n"
        f"- Keep messages concise and impactful - avoid walls of text\n"
        f"- Split lengthy responses into multiple messages naturally\n"
        f"- Use dynamic pacing with shorter messages for tension and longer ones for description\n"
        f"- Write with vivid, sensory language that creates strong imagery\n\n"
    )
    
    # Add character sheet if available
    character_sheet = profile.get("character_sheet", {})
    if character_sheet:
        system_instructions += f"User's Character Sheet:\n{json.dumps(character_sheet, indent=2)}\n\n"
    
    # Add dynamic attributes if available
    dynamic_attributes = profile.get("dynamic_attributes", {})
    if dynamic_attributes:
        system_instructions += f"Dynamic Attributes:\n{json.dumps(dynamic_attributes, indent=2)}\n\n"
    
    # Add memories if available
    if memories_text:
        system_instructions += f"Relevant Memories:\n{memories_text}\n\n"
    
    # Add function descriptions
    system_instructions += f"{function_descriptions}\n\n"
    
    system_instructions += (
        "FUNCTION CALL RULES:\n"
        "1. NEVER explain or discuss adventures, characters, profiles - CALL THE FUNCTION INSTEAD.\n"
        "2. If user mentions 'adventure', ALWAYS call start_adventure function, not a conversation.\n"
        "3. If user mentions 'character', ALWAYS call create_character function, not a conversation.\n"
        "4. If user mentions 'profile', ALWAYS call display_profile function, not a conversation.\n"
        "5. Output ONLY the JSON for function calls - NO descriptive text before or after.\n"
    )
    
    # If the user has not been introduced, include a note about introduction
    if not introduced:
        system_instructions += (
            "\n\nThis is your first interaction with this user. Introduce yourself as a powerful deity "
            "who guides adventures and weaves the threads of fate. Be dramatic and compelling in your introduction. "
            "After introducing yourself, IMMEDIATELY encourage them to embark on an adventure or create a character, "
            "presenting these as exciting opportunities to have their story woven into the tapestry of fate."
        )
    else:
        # If they've been introduced, tell Lachesis not to re-introduce herself if pinged
        if message.content.strip() == f"<@{bot.user.id}>" or "@Lachesis" in message.content:
            system_instructions += (
                "\n\nThe user has just pinged you. DO NOT introduce yourself again. "
                "Instead, acknowledge their call in a deity-like manner and encourage them "
                "toward adventure or action. Suggest they start an adventure if they haven't yet."
            )
    
    # Construct the full prompt with message history
    prompt = f"<|im_start|>system\n{system_instructions}\n<|im_end|>\n"
    for role, msg_content in short_term:
        prompt += f"<|im_start|>{role}\n{msg_content}\n<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"
    
    try:
        # Show typing indicator while generating response
        print(f"[DEBUG] Generating LLM response...")
        async with channel.typing():
            response = await bot.llm_client.generate_response(prompt)
        
        # Log the response for debugging
        print(f"[DEBUG] LLM Response first 150 chars: {response[:150].replace(chr(10), ' ')}")
        
        # Check for function calls - first see if the entire response is a JSON object
        function_call = None
        clean_response = response.strip()
        
        # If the response looks like just JSON, try to parse it directly
        if clean_response.startswith('{') and clean_response.endswith('}'):
            try:
                print(f"[DEBUG] Attempting direct JSON parse")
                potential_call = json.loads(clean_response)
                print(f"[DEBUG] JSON parsed successfully: {potential_call}")
                if "name" in potential_call and "args" in potential_call:
                    function_call = potential_call
                    print(f"[DEBUG] ✅ Valid function call found via direct JSON: {function_call}")
                else:
                    print(f"[DEBUG] ❌ JSON parsed but missing name/args: {potential_call}")
            except json.JSONDecodeError as e:
                print(f"[DEBUG] ❌ JSON parse failed: {e}")
        else:
            print(f"[DEBUG] Response is not a JSON object")
        
        # If no function call found via direct JSON, try extraction methods
        if not function_call:
            print(f"[DEBUG] Attempting function call extraction")
            function_call = bot.function_dispatcher.extract_function_call(response)
            if function_call:
                print(f"[DEBUG] ✅ Function call extracted: {function_call}")
            else:
                print(f"[DEBUG] ❌ No function call could be extracted")
        
        if function_call:
            print(f"[DEBUG] Executing function: {function_call['name']} with args: {function_call['args']}")
            await bot.function_dispatcher.dispatch(
                function_call,
                user_id=user_id,
                message=message,
                bot=bot
            )
        else:
            # Strict keyword override for adventure
            if "adventure" in content_lower and "adventure" not in response.lower():
                print(f"[DEBUG] ❗ KEYWORD OVERRIDE: User mentioned 'adventure' but response doesn't")
                print(f"[DEBUG] Forcing start_adventure function call")
                await bot.function_dispatcher.dispatch(
                    {"name": "start_adventure", "args": {}},
                    user_id=user_id,
                    message=message,
                    bot=bot
                )
                return
            
            # Send regular message response
            print(f"[DEBUG] Sending regular message response")
            await send_message_in_parts(bot, channel, user_id, response)
            
            # If this is the first time interacting, mark as introduced
            if not introduced:
                bot.profile_manager.mark_introduction_done(user_id)
    
    except Exception as e:
        print(f"[DEBUG] ❌ ERROR generating response: {e}")
        print(f"[DEBUG] Error type: {type(e)}")
        await channel.send("Oops, something went wrong. Please try again later.")

async def handle_reaction(bot, reaction, user_id):
    """
    Handle a reaction to a bot message.
    
    Args:
        bot: Discord bot instance
        reaction: Discord reaction
        user_id (str): User ID
    """
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
    """
    Present adventure options to the user.
    
    Args:
        bot: Discord bot instance
        user_id (str): User ID
        channel: Discord channel
        options (list): Options to present
    """
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
    """
    Split and send a message in parts with natural typing and timing delays.
    
    Args:
        bot: Discord bot instance
        channel: Discord channel
        user_id (str): User ID
        full_text (str): Full message text
    """
    # Split on two or more newlines to separate into messages
    segments = [seg.strip() for seg in re.split(r'\n\n+', full_text) if seg.strip()]
    previous_segment = None
    
    for i, segment in enumerate(segments):
        # Add to memory before sending
        bot.memory_manager.add_to_short_term(user_id, "assistant", segment)
        
        # If this isn't the first segment, delay between messages
        if i > 0:
            await delay_manager.delay_between_segments(segment, previous_segment)
        
        # Simulate typing before sending the message
        # Get a typing time based on message length (longer messages = longer typing)
        typing_time = min(1.0 + (len(segment) / delay_manager.typing_speed), 10.0)
        
        # Ensure minimum typing time and add variation
        typing_time = max(1.0, typing_time * random.uniform(0.8, 1.2))
        
        # Show typing indicator and wait
        async with channel.typing():
            # For longer messages, periodically refresh the typing indicator
            if typing_time > 5.0:
                for _ in range(math.ceil(typing_time / 5.0)):
                    await asyncio.sleep(min(5.0, typing_time))
                    typing_time -= 5.0
                    if typing_time <= 0:
                        break
            else:
                await asyncio.sleep(typing_time)
        
        # Send the message
        await channel.send(segment)
        
        # Add a substantial delay between segments (2-4 seconds)
        # This makes multiple messages appear more naturally spaced out
        if i < len(segments) - 1:
            delay_time = random.uniform(2.0, 4.0)
            await asyncio.sleep(delay_time)
        
        # Store for context in the next iteration
        previous_segment = segment