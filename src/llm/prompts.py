"""
Prompt building functions for the LLM interactions.
These functions construct prompts for various contexts and states.
"""

import json
from datetime import datetime

def build_system_prompt(state, profile, memories, function_descriptions=None):
    """
    Build a system prompt based on the user's state.
    
    Args:
        state: Current user state
        profile: User profile data
        memories: List of memory summaries
        function_descriptions: Optional descriptions of available functions
        
    Returns:
        str: System prompt
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    username = profile.get("username", "Adventurer")
    
    # Format memories text
    memories_text = "\n".join([f"- {m}" for m in memories])
    
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
            f"You are Lachesis, guiding {username} through character creation. "
            f"Today's date/time: {current_time}.\n\n"
            "Ask creative and open-ended questions to build their character sheet. "
            "Based on their answers, gauge their personality and capabilities to determine stats.\n\n"
            "Send one question at a time and wait for their response. "
            "After a few questions, generate a character sheet with stats, race, class, and other details."
        )
    elif state == "adventure":
        system_instructions = (
            f"You are Lachesis, running an adventure for {username}. "
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
        )
        
        # Add memories if available
        if memories_text:
            system_instructions += f"Relevant Memories:\n{memories_text}\n\n"
            
        # Add function descriptions if available
        if function_descriptions:
            system_instructions += f"{function_descriptions}\n\n"
            
        system_instructions += (
            "If a user's message implies an action (for example, starting a game or updating their character), "
            "output a JSON function call. Otherwise, produce plain-text messages."
        )
    
    # Check if user has been introduced
    introduced = profile.get("introduced", False)
    if not introduced and state != "introduction":
        system_instructions += "\n\nThis is your first interaction with this user. Introduce yourself briefly."
    
    return system_instructions

def build_full_prompt(system_prompt, conversation_history):
    """
    Build a full prompt with system instructions and conversation history.
    
    Args:
        system_prompt: System instructions
        conversation_history: List of (role, content) tuples
        
    Returns:
        str: Full prompt
    """
    prompt = f"<|im_start|>system\n{system_prompt}\n<|im_end|>\n"
    
    for role, content in conversation_history:
        prompt += f"<|im_start|>{role}\n{content}\n<|im_end|>\n"
    
    prompt += "<|im_start|>assistant\n"
    return prompt

def build_character_creation_prompt(questions_and_answers):
    """
    Build a prompt for generating character stats based on user responses.
    
    Args:
        questions_and_answers: Dictionary of question:answer pairs
        
    Returns:
        str: Prompt for character generation
    """
    # Format Q&A pairs
    qa_text = "\n".join([f"Q: {q}\nA: {a}" for q, a in questions_and_answers.items()])
    
    prompt = (
        "<|im_start|>system\n"
        "Based on the user's responses during character creation, generate appropriate "
        "D&D-style character stats. Respond with valid JSON that includes name, race, class, "
        "stats (strength, dexterity, constitution, intelligence, wisdom, charisma), "
        "and a brief backstory. Ensure all stats are between 8 and 18, with an emphasis on "
        "stats that match the character concept.\n"
        "<|im_end|>\n"
        f"<|im_start|>user\n{qa_text}\n<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    
    return prompt

def build_memory_summarization_prompt(messages):
    """
    Build a prompt for summarizing conversation messages.
    
    Args:
        messages: List of (role, content) tuples to summarize
        
    Returns:
        str: Summarization prompt
    """
    # Convert messages to a single text block
    messages_text = "\n".join([f"{role}: {content}" for role, content in messages])
    
    prompt = (
        "<|im_start|>system\n"
        "Summarize the following conversation concisely, "
        "focusing on key points, decisions, and character development.\n"
        "<|im_end|>\n"
        f"<|im_start|>user\n{messages_text}\n<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    
    return prompt

def build_adventure_continuation_prompt(recent_history):
    """
    Build a prompt for continuing an adventure narrative.
    
    Args:
        recent_history: Recent conversation history
        
    Returns:
        str: Adventure continuation prompt
    """
    # Convert recent history to text
    history_text = "\n".join([f"{role}: {content}" for role, content in recent_history])
    
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
    
    return prompt

def build_dynamic_question_prompt(previous_responses):
    """
    Build a prompt for generating a dynamic question during character creation.
    
    Args:
        previous_responses: Dictionary of previous question:answer pairs
        
    Returns:
        str: Question generation prompt
    """
    prompt = (
        "<|im_start|>system\n"
        "You are helping create a character for an RPG. "
        "Based on the user's previous responses, generate a creative and open-ended "
        "question that will further develop their character. The question should be "
        "engaging and reveal something interesting about the character.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        f"Previous responses:\n{json.dumps(previous_responses, indent=2)}\n\n"
        "Generate the next character creation question.\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )
    
    return prompt