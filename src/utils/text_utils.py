import re

def force_lowercase_minimal(text):
    """
    Convert text to lowercase and remove special characters.
    
    Args:
        text: Text to process
        
    Returns:
        str: Processed text
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def remove_stage_directions(text):
    """
    Remove content in parentheses, brackets, or asterisks
    that might be stage directions or meta-commentary.
    
    Args:
        text: Text to process
        
    Returns:
        str: Processed text
    """
    if not text:
        return ""
    
    # Remove content in parentheses
    text = re.sub(r'\([^)]*\)', '', text)
    
    # Remove content in brackets
    text = re.sub(r'\[[^\]]*\]', '', text)
    
    # Remove content with asterisks (like *laughs*)
    text = re.sub(r'\*[^*]*\*', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def split_messages(text, max_length=2000):
    """
    Split a long message into multiple shorter messages for Discord's limit.
    
    Args:
        text: Text to split
        max_length: Maximum message length
        
    Returns:
        list: List of message parts
    """
    if not text:
        return []
    
    if len(text) <= max_length:
        return [text]
    
    # Try to split on paragraph breaks first
    parts = []
    paragraphs = text.split('\n\n')
    current_part = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed max length, start a new part
        if len(current_part) + len(paragraph) + 2 > max_length:
            if current_part:
                parts.append(current_part)
            
            # If the paragraph itself is too long, split it
            if len(paragraph) > max_length:
                paragraph_parts = split_on_sentences(paragraph, max_length)
                parts.extend(paragraph_parts[:-1])
                current_part = paragraph_parts[-1]
            else:
                current_part = paragraph
        else:
            if current_part:
                current_part += "\n\n" + paragraph
            else:
                current_part = paragraph
    
    if current_part:
        parts.append(current_part)
    
    return parts

def split_on_sentences(text, max_length):
    """
    Split text on sentence boundaries.
    
    Args:
        text: Text to split
        max_length: Maximum part length
        
    Returns:
        list: List of text parts
    """
    if not text:
        return []
    
    parts = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    current_part = ""
    
    for sentence in sentences:
        # If the sentence itself is too long, split it on words
        if len(sentence) > max_length:
            if current_part:
                parts.append(current_part)
            
            words = sentence.split()
            current_part = words[0]
            
            for word in words[1:]:
                if len(current_part) + len(word) + 1 > max_length:
                    parts.append(current_part)
                    current_part = word
                else:
                    current_part += " " + word
        
        # If adding this sentence would exceed max length, start a new part
        elif len(current_part) + len(sentence) + 1 > max_length:
            parts.append(current_part)
            current_part = sentence
        else:
            if current_part:
                current_part += " " + sentence
            else:
                current_part = sentence
    
    if current_part:
        parts.append(current_part)
    
    return parts

def extract_mentions(message):
    """
    Extract mentioned user IDs from a Discord message.
    
    Args:
        message: Discord message object
        
    Returns:
        list: List of mentioned user IDs
    """
    return [str(mention.id) for mention in message.mentions]

def format_character_sheet(character_sheet):
    """
    Format a character sheet for display.
    
    Args:
        character_sheet: Character sheet data
        
    Returns:
        str: Formatted character sheet
    """
    if not character_sheet:
        return "No character data available."
    
    name = character_sheet.get("name", "Unknown")
    race = character_sheet.get("race", "Unknown")
    class_name = character_sheet.get("class", "Unknown")
    level = character_sheet.get("level", 1)
    
    stats = character_sheet.get("stats", {})
    str_val = stats.get("strength", 10)
    dex_val = stats.get("dexterity", 10)
    con_val = stats.get("constitution", 10)
    int_val = stats.get("intelligence", 10)
    wis_val = stats.get("wisdom", 10)
    cha_val = stats.get("charisma", 10)
    
    skills = character_sheet.get("skills", {})
    skill_str = "\n".join([f"  - {skill}: {value}" for skill, value in skills.items()])
    
    inventory = character_sheet.get("inventory", [])
    inventory_str = "\n".join([f"  - {item}" for item in inventory])
    
    backstory = character_sheet.get("backstory", "No backstory available.")
    
    sheet = (
        f"# {name}\n"
        f"**Level {level} {race} {class_name}**\n\n"
        f"## Stats\n"
        f"- Strength: {str_val}\n"
        f"- Dexterity: {dex_val}\n"
        f"- Constitution: {con_val}\n"
        f"- Intelligence: {int_val}\n"
        f"- Wisdom: {wis_val}\n"
        f"- Charisma: {cha_val}\n\n"
    )
    
    if skills:
        sheet += f"## Skills\n{skill_str}\n\n"
    
    if inventory:
        sheet += f"## Inventory\n{inventory_str}\n\n"
    
    sheet += f"## Backstory\n{backstory}"
    
    return sheet
