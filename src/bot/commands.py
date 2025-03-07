import json
import asyncio
import discord
from datetime import datetime

async def start_adventure(user_id, mentions=None, message=None, bot=None, **kwargs):
    """
    Start a new adventure for the user and optionally mentioned users.
    
    Args:
        user_id: Discord user ID
        mentions: List of mentioned user IDs (optional)
        message: Discord message object
        bot: Discord bot instance
        
    Returns:
        bool: Success or failure
    """
    if not message or not bot:
        return False
    
    channel = message.channel
    
    # Convert to list if not already
    if mentions and not isinstance(mentions, list):
        mentions = [mentions]
    elif not mentions:
        mentions = []
    
    # Update state
    bot.state_manager.transition_to(user_id, "adventure", {
        "start_time": datetime.now().isoformat(),
        "participants": [user_id] + mentions
    })
    
    # Save the adventure start in memory
    profile = bot.profile_manager.load_profile(user_id)
    user_name = profile.get("username") or f"<@{user_id}>"
    
    memory_entry = {
        "summary": f"Started an adventure with {user_name} and {len(mentions)} other participants",
        "type": "adventure_start",
        "participants": [user_id] + mentions
    }
    bot.profile_manager.add_long_term_memory(user_id, memory_entry)
    
    # Add to short-term memory
    mention_str = ", ".join([f"<@{uid}>" for uid in mentions]) if mentions else "no one else"
    bot.memory_manager.add_to_short_term(
        user_id, 
        "system", 
        f"Adventure started with {user_name} and {mention_str}."
    )
    
    # Send a message
    if mentions:
        await channel.send(f"An adventure begins with {user_name} and {mention_str}! Let the journey unfold...")
    else:
        await channel.send(f"A solo adventure begins for {user_name}! Let the journey unfold...")
    
    # Prompt the LLM for an adventure introduction
    prompt = (
        "<|im_start|>system\n"
        "You are Lachesis, the guide of an epic adventure. "
        "Create a brief, engaging introduction for a new adventure, "
        "setting the scene and initial situation. Be concise but evocative. "
        "Your goal is to hook the player immediately.\n"
        "<|im_end|>\n"
        f"<|im_start|>user\nCreate an adventure introduction for {user_name}\n<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    
    try:
        intro = await bot.llm_client.generate_response(prompt, max_tokens=200)
        await channel.send(intro)
        bot.memory_manager.add_to_short_term(user_id, "assistant", intro)
    except Exception as e:
        print(f"Error generating adventure intro: {e}")
        await channel.send("The mists swirl as your adventure begins...")
    
    return True

async def create_character(user_id, message=None, bot=None, **kwargs):
    """
    Begin character creation for a user.
    
    Args:
        user_id: Discord user ID
        message: Discord message object
        bot: Discord bot instance
        
    Returns:
        bool: Success or failure
    """
    if not message or not bot:
        return False
    
    channel = message.channel
    
    # Update state
    bot.state_manager.transition_to(user_id, "character_creation", {
        "start_time": datetime.now().isoformat(),
        "step": 0,
        "responses": {}
    })
    
    # Let the user know we're starting character creation
    await channel.send(f"<@{user_id}>, let's create your character! I'll ask you a series of questions to shape your hero.")
    
    # Ask the first question
    await ask_character_creation_question(user_id, channel, bot)
    
    return True

async def ask_character_creation_question(user_id, channel, bot):
    """
    Ask the next character creation question.
    
    Args:
        user_id: Discord user ID
        channel: Discord channel
        bot: Discord bot instance
    """
    # Get current state metadata
    metadata = bot.state_manager.get_state_metadata(user_id)
    step = metadata.get("step", 0)
    responses = metadata.get("responses", {})
    
    # Define questions or use LLM to generate questions
    if step == 0:
        question = "What is your character's name?"
    elif step == 1:
        question = "What race would you like your character to be? (e.g., Human, Elf, Dwarf, etc.)"
    elif step == 2:
        question = "What class or profession does your character have? (e.g., Warrior, Mage, Rogue, etc.)"
    elif step == 3:
        question = "Describe your character's appearance in a few sentences."
    elif step == 4:
        question = "What is your character's greatest strength or skill?"
    elif step == 5:
        question = "What is your character's greatest weakness or flaw?"
    elif step == 6:
        question = "What motivates your character? What are they seeking in their adventures?"
    elif step == 7:
        # Final step - generate character sheet
        await generate_character_sheet(user_id, channel, bot, responses)
        return
    else:
        # Use LLM to generate dynamic questions after the basic ones
        prompt = (
            "<|im_start|>system\n"
            "You are helping create a character for an RPG. "
            "Based on the user's previous responses, generate a creative and open-ended "
            "question that will further develop their character. The question should be "
            "engaging and reveal something interesting about the character.\n"
            "<|im_end|>\n"
            "<|im_start|>user\n"
            f"Previous responses:\n{json.dumps(responses, indent=2)}\n\n"
            "Generate the next character creation question.\n"
            "<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        
        try:
            question = await bot.llm_client.generate_response(prompt, max_tokens=100)
        except Exception as e:
            print(f"Error generating question: {e}")
            question = "Tell me something interesting about your character's past."
    
    # Update state metadata
    bot.state_manager.update_state_metadata(user_id, {
        "step": step,
        "current_question": question
    })
    
    # Send the question
    await channel.send(question)

async def generate_character_sheet(user_id, channel, bot, responses):
    """
    Generate a character sheet based on user responses.
    
    Args:
        user_id: Discord user ID
        channel: Discord channel
        bot: Discord bot instance
        responses: Dictionary of question:answer pairs
    """
    await channel.send("Thank you for answering all the questions! I'm generating your character sheet now...")
    
    try:
        # Use LLM to generate character stats
        character_data = await bot.llm_client.generate_character_stats(responses)
        
        # Update profile with character sheet
        profile = bot.profile_manager.load_profile(user_id)
        profile["character_sheet"] = character_data
        bot.profile_manager.save_profile(user_id, profile)
        
        # Format character sheet for display
        character_json = json.dumps(character_data, indent=2)
        
        # Send the character sheet
        await channel.send(f"**Your Character Is Ready!**\n\n```json\n{character_json}\n```")
        
        # Add summary to memory
        memory_entry = {
            "summary": f"Created character '{character_data.get('name', 'Unknown')}', a {character_data.get('race', 'Unknown')} {character_data.get('class', 'Unknown')}",
            "type": "character_creation"
        }
        bot.profile_manager.add_long_term_memory(user_id, memory_entry)
        
        # Transition back to menu state
        bot.state_manager.transition_to(user_id, "menu")
        
        # Ask if they want to start an adventure
        await channel.send("Your character is ready for adventure! Would you like to start one now?")
        
    except Exception as e:
        print(f"Error generating character sheet: {e}")
        await channel.send("I encountered an issue creating your character. Let's try again later.")

async def process_character_creation_response(user_id, response, channel, bot):
    """
    Process a user's response during character creation.
    
    Args:
        user_id: Discord user ID
        response: User's response text
        channel: Discord channel
        bot: Discord bot instance
        
    Returns:
        bool: Whether this was a character creation response
    """
    # Check if user is in character creation state
    state = bot.state_manager.get_state(user_id)
    if state != "character_creation":
        return False
    
    # Get current state metadata
    metadata = bot.state_manager.get_state_metadata(user_id)
    step = metadata.get("step", 0)
    current_question = metadata.get("current_question", "")
    responses = metadata.get("responses", {})
    
    # Save the response
    responses[current_question] = response
    
    # Update state
    bot.state_manager.update_state_metadata(user_id, {
        "responses": responses,
        "step": step + 1
    })
    
    # Ask the next question
    await ask_character_creation_question(user_id, channel, bot)
    
    return True

async def update_character(user_id, field, value, message=None, bot=None, **kwargs):
    """
    Update a character sheet field.
    
    Args:
        user_id: Discord user ID
        field: Field to update
        value: New value
        message: Discord message object
        bot: Discord bot instance
        
    Returns:
        bool: Success or failure
    """
    if not message or not bot:
        return False
    
    channel = message.channel
    
    # Update the character sheet
    update_result = bot.profile_manager.update_character_sheet(user_id, {field: value})
    
    if update_result:
        await channel.send(f"Updated your character's {field} to: {value}")
    else:
        await channel.send(f"Failed to update your character's {field}. Please try again.")
    
    return update_result

async def execute_script(script_name, args=None, message=None, bot=None, user_id=None, **kwargs):
    """
    Execute a custom script.
    
    Args:
        script_name: Script to execute
        args: Script arguments
        message: Discord message object
        bot: Discord bot instance
        user_id: Discord user ID
        
    Returns:
        bool: Success or failure
    """
    if not message or not bot or not user_id:
        return False
    
    channel = message.channel
    
    # This is a placeholder for custom script execution
    # In a real implementation, you would have a scripts folder and logic to run them
    await channel.send(f"Executing script: {script_name} with args: {args}")
    
    # For demonstration, we'll just log this
    print(f"Script execution requested: {script_name} with args: {args}")
    
    # After 2 seconds, simulate script completion
    await asyncio.sleep(2)
    await channel.send(f"Script {script_name} executed successfully!")
    
    return True

async def continue_adventure(user_id, message=None, bot=None, **kwargs):
    """
    Continue an ongoing adventure.
    
    Args:
        user_id: Discord user ID
        message: Discord message object
        bot: Discord bot instance
        
    Returns:
        bool: Success or failure
    """
    if not message or not bot:
        return False
    
    channel = message.channel
    
    # Check if the user is in an adventure
    state = bot.state_manager.get_state(user_id)
    
    if state != "adventure":
        # If not in an adventure, start one
        await start_adventure(user_id, message=message, bot=bot)
        return True
    
    # Get adventure metadata
    metadata = bot.state_manager.get_state_metadata(user_id)
    
    # Get recent messages for context
    history = bot.memory_manager.get_short_term_history(user_id)
    history_text = "\n".join([f"{role}: {content}" for role, content in history[-5:]])
    
    # Generate continuation
    prompt = (
        "<|im_start|>system\n"
        "You are Lachesis, the guide of an ongoing adventure. "
        "Continue the adventure narrative based on recent interactions. "
        "Be responsive to the player's actions and create an engaging scene "
        "that moves the story forward. Be concise but evocative.\n"
        "<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Recent history:\n{history_text}\n\n"
        f"Continue the adventure for the player.\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    
    try:
        continuation = await bot.llm_client.generate_response(prompt, max_tokens=200)
        await channel.send(continuation)
        bot.memory_manager.add_to_short_term(user_id, "assistant", continuation)
    except Exception as e:
        print(f"Error generating adventure continuation: {e}")
        await channel.send("The adventure continues... [Error: Unable to generate continuation]")
    
    return True

async def display_profile(user_id, message=None, bot=None, **kwargs):
    """
    Display a user's character profile.
    
    Args:
        user_id: Discord user ID
        message: Discord message object
        bot: Discord bot instance
        
    Returns:
        bool: Success or failure
    """
    if not message or not bot:
        return False
    
    channel = message.channel
    
    # Get the profile
    profile = bot.profile_manager.load_profile(user_id)
    character_sheet = profile.get("character_sheet", {})
    
    # Format for display
    if not character_sheet or not character_sheet.get("name"):
        await channel.send(f"<@{user_id}>, you don't have a character yet! Use `!character` to create one.")
        return False
    
    # Format character sheet
    character_json = json.dumps(character_sheet, indent=2)
    
    # Send the profile
    await channel.send(f"### Character Profile for <@{user_id}>\n\n```json\n{character_json}\n```")
    
    return True

async def handle_message(user_id, content, message=None, bot=None, **kwargs):
    """
    Handle a regular message during an adventure or character creation.
    
    Args:
        user_id: Discord user ID
        content: Message content
        message: Discord message object
        bot: Discord bot instance
        
    Returns:
        bool: Whether the message was handled
    """
    if not message or not bot:
        return False
    
    channel = message.channel
    
    # Check the user's state
    state = bot.state_manager.get_state(user_id)
    
    # If in character creation, process as a response
    if state == "character_creation":
        return await process_character_creation_response(user_id, content, channel, bot)
    
    # If in adventure, process as an adventure action
    elif state == "adventure":
        # Add to short-term memory
        bot.memory_manager.add_to_short_term(user_id, "user", content)
        
        # Generate a response
        return await continue_adventure(user_id, message=message, bot=bot)
    
    # Otherwise, just a regular message - handled by the main event handler
    return False
