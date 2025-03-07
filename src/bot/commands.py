"""
Command implementations for Lachesis bot.

This module provides implementations for various commands and functions
that can be called by the bot.
"""

import json
import logging
import asyncio
import random
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.utils.message_delay import delay_manager

logger = logging.getLogger("lachesis.commands")

async def start_adventure(user_id: str, message, bot, **kwargs):
    """
    Start a new adventure for a user.
    
    Args:
        user_id (str): User ID
        message: Discord message
        bot: Discord bot instance
        **kwargs: Additional arguments
    """
    channel = message.channel
    
    # Check if user has a character
    if not bot.profile_manager.has_character(user_id):
        await channel.send(
            "Before we embark on an adventure, you must create a character. "
            "Let me help you with that first."
        )
        # Start character creation
        await create_character(user_id=user_id, message=message, bot=bot)
        return
    
    # Check if user is already in an adventure
    current_state = bot.state_manager.get_state(user_id)
    if current_state == "adventure":
        # Get metadata to see if there's an active adventure
        metadata = bot.state_manager.get_state_metadata(user_id)
        adventure_id = metadata.get("current_adventure")
        
        if adventure_id:
            await channel.send(
                "You're already on an adventure. Let's continue from where you left off."
            )
            # Continue the adventure
            await continue_adventure(user_id=user_id, message=message, bot=bot)
            return
    
    # Load user profile
    profile = bot.profile_manager.load_profile(user_id)
    character_sheet = profile.get("character_sheet", {})
    
    # Typing indicator while processing
    async with channel.typing():
        # Start a new adventure
        adventure_id = bot.adventure_manager.start_adventure(user_id)
        
        if not adventure_id:
            await channel.send("Error starting adventure. Please try again later.")
            return
        
        # Update user state
        bot.state_manager.set_state(user_id, "adventure")
        bot.state_manager.update_state_metadata(user_id, {
            "current_adventure": adventure_id,
            "last_channel_id": str(channel.id)
        })
        
        # Create the initial scene prompt
        character_name = character_sheet.get("name", "the adventurer")
        character_class = character_sheet.get("class", "wanderer")
        character_description = character_sheet.get("description", "")
        
        # Build prompt for adventure start
        prompt = (
            f"<|im_start|>system\n"
            f"You are Lachesis, one of the three Fates from ancient mythology, narrating an adventure. "
            f"Create a compelling and vivid start to an adventure for {character_name}, "
            f"a {character_class}. {character_description}\n\n"
            
            f"WRITING STYLE:\n"
            f"- Write in a grand, mythological style befitting a Fate who weaves the threads of destiny\n"
            f"- Use vivid, sensory descriptions that create strong imagery\n"
            f"- Keep the adventure's start mysterious but intriguing\n"
            f"- End with a clear choice or decision point for the character\n"
            f"- Provide 3 distinct options for what the character can do next\n"
            f"- Format the adventure START in multiple paragraphs with clear scene-setting\n"
            f"- VERY IMPORTANT: Your response must end with a clear choice formatted as: \"**What will you do?**\"\n\n"
            
            f"Craft an adventure start that fits with {character_name}'s background. "
            f"The adventure should be dangerous but not immediately deadly.\n"
            f"<|im_end|>\n"
            
            f"<|im_start|>assistant\n"
        )
        
        # Generate adventure start
        intro = await bot.llm_client.generate_response(prompt)
    
    # Process and send the intro in parts
    await send_adventure_message(bot, channel, user_id, intro)
    
    # Create the first scene and store it
    first_scene = {
        "id": "scene_start",
        "type": "start",
        "description": intro,
        "created_at": datetime.now().isoformat()
    }
    
    # Extract options from intro
    options = extract_options(intro)
    if options:
        first_scene["options"] = options
    
    # Add the scene to the adventure
    bot.adventure_manager.add_scene(adventure_id, first_scene)
    bot.adventure_manager.set_current_scene(adventure_id, "scene_start")
    
    # Add to memory
    bot.memory_manager.add_to_short_term(user_id, "assistant", intro)
    
    # If options were extracted, present them with reactions
    if options and "**What will you do?**" in intro:
        # Options will be presented in the send_adventure_message function
        pass
    else:
        # No clear options found, prompt for next action
        await asyncio.sleep(2)  # Small delay
        await channel.send("**What would you like to do?**")

async def continue_adventure(user_id: str, message, bot, **kwargs):
    """
    Continue an existing adventure.
    
    Args:
        user_id (str): User ID
        message: Discord message
        bot: Discord bot instance
        **kwargs: Additional arguments
    """
    channel = message.channel
    
    # Get state metadata
    metadata = bot.state_manager.get_state_metadata(user_id)
    adventure_id = metadata.get("current_adventure")
    
    if not adventure_id:
        await channel.send("You don't have an active adventure. Let's start a new one!")
        await start_adventure(user_id=user_id, message=message, bot=bot)
        return
    
    # Get the adventure
    adventure = bot.adventure_manager.get_adventure(adventure_id)
    if not adventure:
        await channel.send("Error retrieving your adventure. Let's start a new one.")
        await start_adventure(user_id=user_id, message=message, bot=bot)
        return
    
    # Get current scene
    current_scene = bot.adventure_manager.get_current_scene(adventure_id)
    
    if not current_scene:
        await channel.send("Error retrieving your current scene. Let's start a new one.")
        await start_adventure(user_id=user_id, message=message, bot=bot)
        return
    
    # Send the current scene description
    scene_desc = current_scene.get("description", "You continue your adventure...")
    await send_adventure_message(bot, channel, user_id, scene_desc)
    
    # If the scene has options, present them
    options = current_scene.get("options", [])
    if options:
        await present_options(bot, user_id, channel, options)
    else:
        # No clear options, prompt for next action
        await asyncio.sleep(1)
        await channel.send("**What would you like to do now?**")

async def handle_message(user_id: str, content: str, message, bot, **kwargs):
    """
    Handle a user message during an adventure.
    
    Args:
        user_id (str): User ID
        content (str): Message content
        message: Discord message
        bot: Discord bot instance
        **kwargs: Additional arguments
    """
    channel = message.channel
    
    # Get state metadata
    metadata = bot.state_manager.get_state_metadata(user_id)
    adventure_id = metadata.get("current_adventure")
    
    if not adventure_id:
        # No active adventure, send error
        await channel.send("You don't have an active adventure. Let's start a new one!")
        await start_adventure(user_id=user_id, message=message, bot=bot)
        return
    
    # Load user profile
    profile = bot.profile_manager.load_profile(user_id)
    character_sheet = profile.get("character_sheet", {})
    
    # Get the adventure and current scene
    adventure = bot.adventure_manager.get_adventure(adventure_id)
    current_scene = bot.adventure_manager.get_current_scene(adventure_id)
    
    # Get the recent conversation history
    short_term = bot.memory_manager.get_short_term_history(user_id)
    
    # Format conversation history
    conversation_history = ""
    for i, (role, msg) in enumerate(short_term[-5:]):  # Last 5 messages
        conversation_history += f"{role.upper()}: {msg}\n\n"
    
    # Build prompt for next scene
    prompt = (
        f"<|im_start|>system\n"
        f"You are Lachesis, one of the three Fates from ancient mythology, narrating an adventure. "
        f"The user is playing as {character_sheet.get('name', 'the adventurer')}, "
        f"a {character_sheet.get('class', 'wanderer')}.\n\n"
        
        f"Current Adventure State:\n"
        f"- Adventure ID: {adventure_id}\n"
        f"- Current Scene: {current_scene.get('id', 'unknown')}\n\n"
        
        f"WRITING STYLE:\n"
        f"- Write in a grand, mythological style befitting a Fate who weaves the threads of destiny\n"
        f"- Use vivid, sensory descriptions that create strong imagery\n"
        f"- Respond to the user's actions with appropriate consequences\n"
        f"- Keep the adventure moving forward in an engaging way\n"
        f"- End your response with a clear situation and implicit or explicit options\n\n"
        
        f"RESPONSE FORMAT:\n"
        f"- Respond to the user's action with 2-4 paragraphs of narrative\n"
        f"- Be consistent with the established world and narrative\n"
        f"- For major decision points, end with \"**What will you do?**\" and include options\n"
        f"- For minor actions, respond naturally without explicit options\n\n"
        
        f"Recent conversation history:\n{conversation_history}\n\n"
        
        f"The user (in character as {character_sheet.get('name', 'the adventurer')}) has just said or done: \"{content}\"\n"
        f"Respond as Lachesis, narrating what happens next in the adventure.\n"
        f"<|im_end|>\n"
        
        f"<|im_start|>assistant\n"
    )
    
    # Typing indicator while generating
    async with channel.typing():
        # Generate response
        response = await bot.llm_client.generate_response(prompt)
    
    # Create a new scene
    scene_id = f"scene_{adventure.get('next_scene_id', 1)}"
    next_scene = {
        "id": scene_id,
        "type": "response",
        "description": response,
        "parent_scene": current_scene.get("id"),
        "user_action": content,
        "created_at": datetime.now().isoformat()
    }
    
    # Extract options if present
    options = extract_options(response)
    if options:
        next_scene["options"] = options
    
    # Add scene to adventure and set as current
    bot.adventure_manager.add_scene(adventure_id, next_scene)
    bot.adventure_manager.set_current_scene(adventure_id, scene_id)
    
    # Process and send the response
    await send_adventure_message(bot, channel, user_id, response)
    
    # If options were extracted and formatted, present them
    if options and "**What will you do?**" in response:
        # Options will be presented in the send_adventure_message function
        pass
    
    # Add to memory
    bot.memory_manager.add_to_short_term(user_id, "assistant", response)

async def create_character(user_id: str, message, bot, **kwargs):
    """
    Start the character creation process.
    
    Args:
        user_id (str): User ID
        message: Discord message
        bot: Discord bot instance
        **kwargs: Additional arguments
    """
    channel = message.channel
    
    # Check if user already has a character
    if bot.profile_manager.has_character(user_id):
        # Ask if they want to create a new character or use existing
        profile = bot.profile_manager.load_profile(user_id)
        character_sheet = profile.get("character_sheet", {})
        character_name = character_sheet.get("name", "your character")
        
        confirm_msg = await channel.send(
            f"You already have a character ({character_name}). "
            f"Do you want to create a new character instead? (yes/no)"
        )
        
        # Set state to await confirmation
        bot.state_manager.set_state(user_id, "character_creation_confirm")
        bot.state_manager.update_state_metadata(user_id, {
            "last_channel_id": str(channel.id)
        })
        
        # Add to memory
        bot.memory_manager.add_to_short_term(user_id, "assistant", confirm_msg.content)
        
        return
    
    # Set state to character creation
    bot.state_manager.set_state(user_id, "character_creation")
    bot.state_manager.update_state_metadata(user_id, {
        "creation_step": "name",
        "last_channel_id": str(channel.id),
        "character_data": {}
    })
    
    # Start with name prompt
    prompt = (
        f"<|im_start|>system\n"
        f"You are Lachesis, one of the three Fates from ancient mythology, guiding a user in creating "
        f"a character for an adventure. Be mysterious, otherworldly, and speak of destiny and fate.\n\n"
        
        f"WRITING STYLE:\n"
        f"- Write in a grand, mythological style befitting an ancient Fate\n"
        f"- Use vivid, evocative language that creates an atmosphere of mystery\n"
        f"- Be concise but impactful\n\n"
        
        f"Ask the user for their character's name in a mystical, fate-oriented way. "
        f"Make it feel momentous and significant, as if their name is a thread in the tapestry of fate.\n"
        f"<|im_end|>\n"
        
        f"<|im_start|>assistant\n"
    )
    
    # Generate name prompt
    async with channel.typing():
        name_prompt = await bot.llm_client.generate_response(prompt)
    
    # Send the name prompt
    await channel.send(name_prompt)
    
    # Add to memory
    bot.memory_manager.add_to_short_term(user_id, "assistant", name_prompt)

async def process_character_creation_response(user_id: str, content: str, channel, bot):
    """
    Process a response during character creation.
    
    Args:
        user_id (str): User ID
        content (str): User's response
        channel: Discord channel
        bot: Discord bot instance
    """
    # Get current creation step
    metadata = bot.state_manager.get_state_metadata(user_id)
    step = metadata.get("creation_step", "name")
    character_data = metadata.get("character_data", {})
    
    # Handle based on current step
    if step == "name":
        # Process name
        character_data["name"] = content.strip()
        
        # Update metadata
        bot.state_manager.update_state_metadata(user_id, {
            "creation_step": "class",
            "character_data": character_data
        })
        
        # Generate class prompt
        prompt = (
            f"<|im_start|>system\n"
            f"You are Lachesis, one of the three Fates from ancient mythology, guiding a user in creating "
            f"a character named {character_data['name']} for an adventure.\n\n"
            
            f"WRITING STYLE:\n"
            f"- Write in a grand, mythological style befitting an ancient Fate\n"
            f"- Use vivid, evocative language that creates an atmosphere of mystery\n"
            f"- Be concise but impactful\n\n"
            
            f"Ask the user to choose a class/profession for their character. "
            f"Offer 5-6 interesting class suggestions that would fit in a fantasy world, "
            f"but make it clear they can choose something not on the list as well.\n"
            f"<|im_end|>\n"
            
            f"<|im_start|>assistant\n"
        )
        
        # Generate class prompt
        async with channel.typing():
            class_prompt = await bot.llm_client.generate_response(prompt)
        
        # Send the class prompt
        await channel.send(class_prompt)
        
        # Add to memory
        bot.memory_manager.add_to_short_term(user_id, "assistant", class_prompt)
    
    elif step == "class":
        # Process class
        character_data["class"] = content.strip()
        
        # Update metadata
        bot.state_manager.update_state_metadata(user_id, {
            "creation_step": "background",
            "character_data": character_data
        })
        
        # Generate background prompt
        prompt = (
            f"<|im_start|>system\n"
            f"You are Lachesis, one of the three Fates from ancient mythology, guiding a user in creating "
            f"a character named {character_data['name']}, a {character_data['class']} for an adventure.\n\n"
            
            f"WRITING STYLE:\n"
            f"- Write in a grand, mythological style befitting an ancient Fate\n"
            f"- Use vivid, evocative language that creates an atmosphere of mystery\n"
            f"- Be concise but impactful\n\n"
            
            f"Ask the user for a brief background or motivation for their character. "
            f"What drives them? What is their past? What are their goals? "
            f"Encourage them to be brief but descriptive.\n"
            f"<|im_end|>\n"
            
            f"<|im_start|>assistant\n"
        )
        
        # Generate background prompt
        async with channel.typing():
            background_prompt = await bot.llm_client.generate_response(prompt)
        
        # Send the background prompt
        await channel.send(background_prompt)
        
        # Add to memory
        bot.memory_manager.add_to_short_term(user_id, "assistant", background_prompt)
    
    elif step == "background":
        # Process background
        character_data["background"] = content.strip()
        
        # Update metadata
        bot.state_manager.update_state_metadata(user_id, {
            "creation_step": "traits",
            "character_data": character_data
        })
        
        # Generate traits prompt
        prompt = (
            f"<|im_start|>system\n"
            f"You are Lachesis, one of the three Fates from ancient mythology, guiding a user in creating "
            f"a character named {character_data['name']}, a {character_data['class']} with the following background: "
            f"{character_data['background']}\n\n"
            
            f"WRITING STYLE:\n"
            f"- Write in a grand, mythological style befitting an ancient Fate\n"
            f"- Use vivid, evocative language that creates an atmosphere of mystery\n"
            f"- Be concise but impactful\n\n"
            
            f"Ask the user to provide 2-3 key personality traits for their character. "
            f"What makes them unique? What are their strengths and flaws?\n"
            f"<|im_end|>\n"
            
            f"<|im_start|>assistant\n"
        )
        
        # Generate traits prompt
        async with channel.typing():
            traits_prompt = await bot.llm_client.generate_response(prompt)
        
        # Send the traits prompt
        await channel.send(traits_prompt)
        
        # Add to memory
        bot.memory_manager.add_to_short_term(user_id, "assistant", traits_prompt)
    
    elif step == "traits":
        # Process traits
        character_data["traits"] = content.strip()
        
        # Update metadata
        bot.state_manager.update_state_metadata(user_id, {
            "creation_step": "complete",
            "character_data": character_data
        })
        
        # Generate stats based on responses
        # This is where we apply the "natural language to numerical data" approach
        stats = await generate_character_stats(character_data, bot.llm_client)
        character_data.update(stats)
        
        # Create a full character description
        description = (
            f"{character_data['name']} is a {character_data['class']} with the following background: "
            f"{character_data['background']}\n\n"
            f"Key traits: {character_data['traits']}"
        )
        character_data["description"] = description
        
        # Save character
        bot.profile_manager.create_character(user_id, character_data)
        
        # Generate completion message
        prompt = (
            f"<|im_start|>system\n"
            f"You are Lachesis, one of the three Fates from ancient mythology. "
            f"The user has just completed creating a character with these details:\n"
            f"- Name: {character_data['name']}\n"
            f"- Class: {character_data['class']}\n"
            f"- Background: {character_data['background']}\n"
            f"- Traits: {character_data['traits']}\n"
            f"- Stats: Strength {character_data.get('strength', 10)}, "
            f"Dexterity {character_data.get('dexterity', 10)}, "
            f"Constitution {character_data.get('constitution', 10)}, "
            f"Intelligence {character_data.get('intelligence', 10)}, "
            f"Wisdom {character_data.get('wisdom', 10)}, "
            f"Charisma {character_data.get('charisma', 10)}\n\n"
            
            f"WRITING STYLE:\n"
            f"- Write in a grand, mythological style befitting an ancient Fate\n"
            f"- Use vivid, evocative language that creates an atmosphere of mystery\n"
            f"- Be concise but impactful\n\n"
            
            f"Write a dramatic and mystical completion message that announces the character "
            f"is now ready for adventures. Describe how you've measured the thread of their fate "
            f"and how they are now ready to have their story woven into the grand tapestry. "
            f"End by explicitly suggesting they start an adventure with a phrase like "
            f"\"Shall we begin your adventure now?\"\n"
            f"<|im_end|>\n"
            
            f"<|im_start|>assistant\n"
        )
        
        # Generate completion message
        async with channel.typing():
            completion_message = await bot.llm_client.generate_response(prompt)
        
        # Send the completion message
        await channel.send(completion_message)
        
        # Add to memory
        bot.memory_manager.add_to_short_term(user_id, "assistant", completion_message)
        
        # Set state back to menu
        bot.state_manager.set_state(user_id, "menu")
    
    elif step == "complete":
        # Character creation is complete, check if they want to start an adventure
        if any(word in content.lower() for word in ["yes", "start", "begin", "adventure", "sure", "okay"]):
            await start_adventure(user_id=user_id, message=channel, bot=bot)
        else:
            await channel.send(
                "Very well. Your character is ready when you wish to begin your adventure. "
                "Simply say 'adventure' when you wish to start."
            )
            # Set state back to menu
            bot.state_manager.set_state(user_id, "menu")

async def update_character(user_id: str, message, bot, field: str = None, value: str = None, **kwargs):
    """
    Update a field in a user's character sheet.
    
    Args:
        user_id (str): User ID
        message: Discord message
        bot: Discord bot instance
        field (str, optional): Field to update
        value (str, optional): New value
        **kwargs: Additional arguments
    """
    channel = message.channel
    
    # Check if user has a character
    if not bot.profile_manager.has_character(user_id):
        await channel.send(
            "You don't have a character yet. Let's create one first."
        )
        # Start character creation
        await create_character(user_id=user_id, message=message, bot=bot)
        return
    
    # If field and value are provided, update directly
    if field and value:
        success = bot.profile_manager.update_character(user_id, field, value)
        
        if success:
            await channel.send(f"Your character's {field} has been updated to: {value}")
        else:
            await channel.send(f"Error updating your character's {field}.")
        
        return
    
    # If no field specified, enter interactive update mode
    profile = bot.profile_manager.load_profile(user_id)
    character_sheet = profile.get("character_sheet", {})
    
    # Show current character sheet
    char_info = "**Current Character Information:**\n"
    for key, val in character_sheet.items():
        if key != "description" and not isinstance(val, dict):
            char_info += f"- **{key}**: {val}\n"
    
    await channel.send(
        f"{char_info}\n"
        "What would you like to update? Please use the format: `field: new value`\n"
        "For example: `name: Aragorn` or `class: Ranger`"
    )
    
    # Set state to await update input
    bot.state_manager.set_state(user_id, "character_update")
    bot.state_manager.update_state_metadata(user_id, {
        "last_channel_id": str(channel.id)
    })

async def display_profile(user_id: str, message, bot, **kwargs):
    """
    Display a user's character profile.
    
    Args:
        user_id (str): User ID
        message: Discord message
        bot: Discord bot instance
        **kwargs: Additional arguments
    """
    channel = message.channel
    
    # Check if user has a character
    if not bot.profile_manager.has_character(user_id):
        await channel.send(
            "You don't have a character yet. Let's create one first."
        )
        # Start character creation
        await create_character(user_id=user_id, message=message, bot=bot)
        return
    
    # Load profile
    profile = bot.profile_manager.load_profile(user_id)
    character_sheet = profile.get("character_sheet", {})
    dynamic_attrs = profile.get("dynamic_attributes", {})
    
    # Format profile display
    name = character_sheet.get("name", "Unknown")
    char_class = character_sheet.get("class", "Unknown")
    
    profile_text = f"# {name}, the {char_class}\n\n"
    
    # Add description if available
    description = character_sheet.get("description", "")
    if description:
        profile_text += f"**Background:** {description}\n\n"
    
    # Add traits if available
    traits = character_sheet.get("traits", "")
    if traits:
        profile_text += f"**Traits:** {traits}\n\n"
    
    # Add stats
    profile_text += "## Stats\n"
    stats = [
        ("Strength", character_sheet.get("strength", 10)),
        ("Dexterity", character_sheet.get("dexterity", 10)),
        ("Constitution", character_sheet.get("constitution", 10)),
        ("Intelligence", character_sheet.get("intelligence", 10)),
        ("Wisdom", character_sheet.get("wisdom", 10)),
        ("Charisma", character_sheet.get("charisma", 10))
    ]
    
    for stat_name, stat_value in stats:
        profile_text += f"- **{stat_name}:** {stat_value}\n"
    
    # Add dynamic attributes
    profile_text += "\n## Current Status\n"
    if dynamic_attrs:
        for attr, value in dynamic_attrs.items():
            profile_text += f"- **{attr.title()}:** {value}\n"
    
    # Add adventures if any
    adventures = bot.adventure_manager.get_active_adventures_for_user(user_id)
    if adventures:
        profile_text += "\n## Active Adventures\n"
        for adv in adventures:
            title = adv.get("title", "Untitled Adventure")
            started = adv.get("started_at", "Unknown")
            profile_text += f"- **{title}** (Started: {started[:10]})\n"
    
    # Send the profile
    await channel.send(profile_text)

async def execute_script(user_id: str, message, bot, script: str = "", **kwargs):
    """
    Execute a custom script.
    
    Args:
        user_id (str): User ID
        message: Discord message
        bot: Discord bot instance
        script (str): Script to execute
        **kwargs: Additional arguments
    """
    channel = message.channel
    
    # Only allow this for admins
    if not is_admin(message.author):
        await channel.send("You don't have permission to execute scripts.")
        return
    
    if not script:
        await channel.send("No script provided.")
        return
    
    try:
        # Very limited script execution for admins only
        # This would need proper sandboxing in a real application
        result = str(eval(script))
        await channel.send(f"Script executed. Result: {result}")
    except Exception as e:
        await channel.send(f"Error executing script: {str(e)}")

def is_admin(user):
    """
    Check if a user is an admin.
    
    Args:
        user: Discord user
        
    Returns:
        bool: True if admin, False otherwise
    """
    # In a real application, you would check against a list of admin IDs
    # For now, always return False for safety
    return False

async def generate_character_stats(character_data, llm_client):
    """
    Generate character stats based on character data.
    
    Args:
        character_data (Dict): Character data
        llm_client: LLM client
        
    Returns:
        Dict: Generated stats
    """
    # Build prompt for stat generation
    prompt = (
        f"<|im_start|>system\n"
        f"Generate appropriate D&D-style stats (Strength, Dexterity, Constitution, Intelligence, Wisdom, Charisma) "
        f"for a character with these attributes:\n\n"
        f"- Name: {character_data.get('name', 'Unknown')}\n"
        f"- Class: {character_data.get('class', 'Unknown')}\n"
        f"- Background: {character_data.get('background', 'Unknown')}\n"
        f"- Traits: {character_data.get('traits', 'Unknown')}\n\n"
        
        f"Generate stats on a scale of 1-20, where 10 is average human capability. Base the stats on the "
        f"character's class and described traits and background. For example, a warrior might have higher "
        f"Strength, while a wizard would have higher Intelligence.\n\n"
        
        f"Return ONLY a JSON object with the stats, like this:\n"
        f"{{\"strength\": 14, \"dexterity\": 12, \"constitution\": 13, \"intelligence\": 10, \"wisdom\": 8, \"charisma\": 15}}\n"
        f"<|im_end|>\n"
        
        f"<|im_start|>assistant\n"
    )
    
    # Generate stats
    response = await llm_client.generate_response(prompt)
    
    try:
        # Extract JSON if needed
        json_str = extract_json(response)
        if json_str:
            stats = json.loads(json_str)
        else:
            stats = json.loads(response)
        
        # Validate stats
        valid_stats = {
            "strength": 10,
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10
        }
        
        # Update valid stats with generated ones
        for key in valid_stats:
            if key in stats:
                value = int(stats[key])
                # Ensure within range
                valid_stats[key] = max(1, min(20, value))
        
        return valid_stats
    
    except Exception as e:
        logger.error(f"Error parsing stats: {e}")
        # Return default stats on error
        return {
            "strength": 10,
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10
        }

def extract_json(text):
    """
    Extract JSON from text.
    
    Args:
        text (str): Text to extract JSON from
        
    Returns:
        str: Extracted JSON or None
    """
    # Find JSON object in text
    match = re.search(r'({.*})', text, re.DOTALL)
    if match:
        return match.group(1)
    return None

def extract_options(text):
    """
    Extract options from adventure text.
    
    Args:
        text (str): Text to extract options from
        
    Returns:
        List: List of option dictionaries
    """
    options = []
    
    # Check if the text contains the options marker
    if "**What will you do?**" in text:
        # Get the text after the marker
        options_text = text.split("**What will you do?**", 1)[1]
        
        # Look for numbered options
        numbered_pattern = r'(\d+[\)\.]\s*|\*\s*|-\s*|[a-zA-Z][\)\.]\s*)(.+?)(?=\n\d+[\)\.]\s*|\n\*\s*|\n-\s*|\n[a-zA-Z][\)\.]\s*|\n\n|$)'
        matches = re.findall(numbered_pattern, options_text, re.DOTALL)
        
        # Create option objects
        for i, (_, option_text) in enumerate(matches):
            clean_text = option_text.strip()
            option_id = f"option_{i + 1}"
            
            options.append({
                "text": clean_text,
                "next": option_id
            })
    
    return options

async def present_options(bot, user_id, channel, options):
    """
    Present options to the user with reactions.
    
    Args:
        bot: Discord bot instance
        user_id (str): User ID
        channel: Discord channel
        options (List): List of options
    """
    from src.bot.events import present_options as events_present_options
    await events_present_options(bot, user_id, channel, options)

async def send_adventure_message(bot, channel, user_id, full_text):
    """
    Send an adventure message in parts with natural pacing.
    
    Args:
        bot: Discord bot instance
        channel: Discord channel
        user_id (str): User ID
        full_text (str): Full message text
    """
    from src.bot.events import send_message_in_parts
    await send_message_in_parts(bot, channel, user_id, full_text)