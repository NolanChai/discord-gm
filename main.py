import os
import random
import asyncio
import re
from datetime import datetime, timedelta

import discord
from discord.ext import tasks, commands
from dotenv import load_dotenv
import openai

from profile_manager import ProfileManager
from memory_manager import MemoryManager, force_lowercase_minimal, remove_stage_directions
from function_dispatcher import extract_function_call

# ----------------------------
# 1. Load Environment Variables
# ----------------------------
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LM_API_BASE = os.getenv("LM_API_BASE", "http://localhost:1234/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "YourModelNameHere")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.8))
TOP_P = float(os.getenv("TOP_P", 0.95))
TOP_K = int(os.getenv("TOP_K", 40))
STOP_STRINGS = [os.getenv("STOP_STRINGS", "<|im_end|>")]

if not DISCORD_TOKEN:
    raise ValueError("Missing DISCORD_BOT_TOKEN in environment variables!")

openai.api_key = "None"  # Not used for local LM Studio
openai.api_base = LM_API_BASE

# ----------------------------
# 2. Discord Bot Setup
# ----------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------------------
# 3. Instantiate Managers
# ----------------------------
profile_manager = ProfileManager()
memory_manager = MemoryManager()

# For inactivity tracking per user
user_inactivity = {}  # user_id -> datetime
INACTIVITY_THRESHOLD_MINUTES = 15

# ----------------------------
# 4. Utility Functions
# ----------------------------
def build_system_prompt(user_id: str) -> str:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    short_term = memory_manager.get_short_term_history(user_id)
    user_text = ""
    for role, txt in reversed(short_term):
        if role == "user":
            user_text = txt
            break

    # Get long-term memories (if any)
    profile = profile_manager.load_profile(user_id)
    memories = profile.get("long_term_memories", [])
    memories_text = "\n".join([f"- {m.get('summary', '')}" for m in memories])

    # Prepare the available functions list for the LLM
    available_functions = (
        "Available functions:\n"
        "1. start_game(user_id, mentions): start a new game session\n"
        "2. create_character(user_id): initiate a character creation conversation\n"
        "3. update_character(user_id, field, value): update a character sheet field\n"
        "4. execute_script(script_name, args): run a local script\n"
        "5. continue_adventure(user_id): continue the ongoing adventure\n"
    )

    # Updated personality instructions:
    system_instructions = (
        f"You are Lachesis, one of the three weavers of destiny, a mysterious guide who leads adventurers on epic quests. "
        f"Today's date/time: {current_time}.\n\n"
        "When a user greets you or pings you, first ask them what their intent is rather than immediately starting a process. "
        "If they imply a desire to create a character, ask if they'd like to create one, and then proceed with a guided conversation. \n\n"
        "Use markdown formatting in your replies (for example, use headers, bullet lists, and code blocks if needed) and preserve proper capitalization. \n\n"
        "User's Character Sheet:\n"
        f"```json\n{profile['character_sheet']}\n```\n\n"
        "Dynamic Attributes:\n"
        f"```json\n{profile['dynamic_attributes']}\n```\n\n"
        "Relevant Memories:\n"
        f"{memories_text}\n\n"
        f"{available_functions}\n\n"
        "When replying, if the user's message implies an action (like starting a game or creating a character), output a JSON object "
        "wrapped in `<|function_call|>` and `<|end_function_call|>` with the key 'name' for the function name and an 'args' object for parameters. "
        "Otherwise, simply output a plain text reply that is split into multiple segments (if long) using double newlines."
    )

    prompt = f"<|im_start|>system\n{system_instructions}\n<|im_end|>\n"
    for role, content in short_term:
        prompt += f"<|im_start|>{role}\n{content}\n<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"
    return prompt


async def dispatch_function_call(func_call: dict, message: discord.Message, user_id: str):
    """
    Based on the function call, run the corresponding function.
    """
    func_name = func_call.get("name")
    args = func_call.get("args", {})

    if func_name == "start_game":
        await start_game(user_id, message.channel, args)
    elif func_name == "create_character":
        await create_character(user_id, message.channel)
    elif func_name == "update_character":
        field = args.get("field")
        value = args.get("value")
        profile_manager.update_character_sheet(user_id, {field: value})
        await message.channel.send(f"Updated your {field} to {value}.")
    elif func_name == "execute_script":
        script_name = args.get("script_name")
        # Here you can implement local script execution
        await message.channel.send(f"Executed script: {script_name}.")
    elif func_name == "continue_adventure":
        await message.channel.send("Continuing the adventure...")
    else:
        await message.channel.send("I'm not sure how to handle that action.")

async def start_game(user_id: str, channel: discord.TextChannel, args: dict):
    # For instance, initialize game data for this user and others if provided
    mentions = args.get("mentions", [])
    await channel.send(f"Game is starting for <@{user_id}> and {', '.join(mentions)}! Let's get ready for an epic quest!")
    # Optionally, you might want to trigger character creation for users without a character
    profile = profile_manager.load_profile(user_id)
    if not profile["character_sheet"]["name"]:
        await channel.send(f"Hey <@{user_id}>, let's create your character. I'll guide you through it shortly.")

async def create_character(user_id: str, channel: discord.TextChannel):
    # A conversational character creation sequence handled by the LLM.
    # Here, we might send a prompt to the LLM asking questions.
    await channel.send(f"Hey <@{user_id}>, let's create your character! What is your character's name?")
    # In a full implementation, you could wait for the user response and then call the LLM again
    # to ask follow-up questions and ultimately update the character sheet.

# ----------------------------
# 5. Periodic Tasks (Inactivity, etc.)
# ----------------------------
async def handle_inactivity_check():
    now = datetime.now()
    for user_id, last_time in user_inactivity.items():
        if now - last_time > timedelta(minutes=INACTIVITY_THRESHOLD_MINUTES):
            user = await bot.fetch_user(int(user_id))
            if user:
                try:
                    msg = f"Hey <@{user_id}>, are you still with us? Let me know when you're ready to continue our adventure!"
                    await user.send(msg)
                    memory_manager.add_to_short_term(user_id, "assistant", msg)
                except Exception as e:
                    print(f"Error DMing user {user_id}: {e}")

@tasks.loop(minutes=2)
async def periodic_tasks():
    await handle_inactivity_check()

# ----------------------------
# 6. Bot Events & Message Handling
# ----------------------------
@bot.event
@bot.event
async def on_message(message):
    # Process commands (if any)
    await bot.process_commands(message)
    if message.author == bot.user or not message.content:
        return

    user_id = str(message.author.id)
    content = message.content.strip()
    user_inactivity[user_id] = datetime.now()
    memory_manager.add_to_short_term(user_id, "user", content)
    memory_manager.trim_and_summarize_if_needed(user_id, profile_manager)

    # Build the prompt (including function instructions) for the LLM.
    prompt = build_system_prompt(user_id)

    try:
        async with message.channel.typing():
            response = openai.Completion.create(
                model=MODEL_NAME,
                prompt=prompt,
                temperature=TEMPERATURE,
                max_tokens=300,
                top_p=TOP_P,
                stop=STOP_STRINGS
            )
        full_response = response.choices[0].text.strip()
        # Check if the LLM wants to call a function.
        func_call = extract_function_call(full_response)
        if func_call:
            await dispatch_function_call(func_call, message, user_id)
        else:
            # Process plain text reply:
            reply = remove_stage_directions(full_response)
            # Split into multiple segments on double newlines:
            segments = [seg.strip() for seg in reply.split("\n\n") if seg.strip()]
            for seg in segments:
                memory_manager.add_to_short_term(user_id, "assistant", seg)
                memory_manager.trim_and_summarize_if_needed(user_id, profile_manager)
                await message.channel.send(seg)
    except Exception as e:
        print(f"Error generating response: {e}")
        await message.channel.send("Oops, something went wrong. Please try again later.")

# ----------------------------
# 7. Bot Commands (Optional Fallbacks)
# ----------------------------
@bot.command(name="status")
async def status_command(ctx):
    user_id = str(ctx.author.id)
    profile = profile_manager.load_profile(user_id)
    char_sheet = profile["character_sheet"]
    dynamic = profile["dynamic_attributes"]
    ltm_count = len(profile.get("long_term_memories", []))
    await ctx.send(
        f"**Your Character**\nName: {char_sheet.get('name', 'Not set')}\n"
        f"Race: {char_sheet.get('race', 'Not set')}\n"
        f"Class: {char_sheet.get('class', 'Not set')}\n"
        f"Stats: {char_sheet.get('stats', {})}\n\n"
        f"**Dynamic Attributes:** {dynamic}\n"
        f"**Long-Term Memories:** {ltm_count} stored."
    )

# ----------------------------
# 8. Main Entry
# ----------------------------
@bot.event
async def on_ready():
    print(f"Bot is online! Logged in as {bot.user}")
    periodic_tasks.start()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
