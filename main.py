# main.py

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

# For local LM or OpenAI usage
openai.api_key = "None"  # Not used if local
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

# We also track inactivity times per user
user_inactivity = {}  # user_id -> datetime of last message
INACTIVITY_THRESHOLD_MINUTES = 15

# ----------------------------
# 4. Utility / Outline
# ----------------------------

def format_prompt(user_id: str) -> str:
    """
    Construct a ChatML style prompt for Lachesis (the DM).
    We'll gather:
      - short-term conversation
      - relevant memories (RAG)
      - user’s character sheet
      - system instructions
    """
    # Prepare system content
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    short_term = memory_manager.get_short_term_history(user_id)
    
    # Last user message to do naive retrieval
    user_text = ""
    for role, txt in reversed(short_term):
        if role == "user":
            user_text = txt
            break
    
    # RAG from user's memories
    relevant_memories = memory_manager.get_relevant_memories(user_id, user_text, profile_manager, top_k=3)
    relevant_text = "\n".join([f"- {m}" for m in relevant_memories])

    # Get user's profile
    profile = profile_manager.load_profile(user_id)
    char_sheet = profile["character_sheet"]
    dynamic = profile["dynamic_attributes"]

    # Create a summary of the user's character for the system prompt
    char_info = (
        f"Character Name: {char_sheet.get('name', '')}\n"
        f"Race: {char_sheet.get('race', '')}\n"
        f"Class: {char_sheet.get('class', '')}\n"
        f"Stats: {char_sheet.get('stats', {})}\n"
    )

    # Lachesis's role + style instructions
    system_instructions = (
        f"You are Lachesis, a Dungeon Master with a slightly playful, friendly personality. "
        f"You keep track of the story arcs, player characters, and rules. "
        f"Speak to the user in a warm, engaging tone, with creative storytelling flair. "
        f"Date/Time: {current_time}.\n\n"
        "If the user requests character creation, walk them through questions about their name, race, class, stats.\n"
        "If multiple users are present, coordinate their character sheets.\n"
        "Keep track of arcs, storylines, and relevant details in your memory system. "
        "Answer in a style that includes some creative detail and mild humor, but remain concise.\n\n"
        f"Relevant past info:\n{relevant_text}\n\n"
        f"User's Character Sheet:\n{char_info}\n"
        f"Dynamic attributes: {dynamic}\n"
    )

    # Build the ChatML style prompt
    prompt = f"<|im_start|>system\n{system_instructions}\n<|im_end|>\n"
    for role, content in short_term:
        prompt += f"<|im_start|>{role}\n{content}\n<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"

    return prompt

async def handle_inactivity_check():
    """
    Periodically check each user's inactivity.
    If they've been inactive, maybe DM them or do something creative.
    """
    now = datetime.now()
    for user_id, last_time in user_inactivity.items():
        delta = now - last_time
        if delta > timedelta(minutes=INACTIVITY_THRESHOLD_MINUTES):
            # Example: DM them a nudge
            user = await bot.fetch_user(int(user_id))
            if user:
                try:
                    nudge_msg = f"Hey <@{user_id}>, you still around? We can continue whenever you're ready!"
                    await user.send(nudge_msg)
                    # And we can store that in the short-term memory for context
                    memory_manager.add_to_short_term(user_id, "assistant", nudge_msg)
                except Exception as e:
                    print(f"Error DMing user {user_id}: {e}")

@tasks.loop(minutes=2)
async def periodic_tasks():
    """
    This will run every 2 minutes in the background.
    Handle inactivity checks, random events, etc.
    """
    await handle_inactivity_check()

# ----------------------------
# 5. Bot Commands
# ----------------------------

@bot.command(name="status")
async def status_command(ctx):
    """
    Check your own status (like short summary of your character).
    """
    user_id = str(ctx.author.id)
    profile = profile_manager.load_profile(user_id)
    char_sheet = profile["character_sheet"]
    dynamic = profile["dynamic_attributes"]
    ltm_count = len(profile["long_term_memories"])

    msg = (
        f"**Your Character**\n"
        f"Name: {char_sheet.get('name', '')}\n"
        f"Race: {char_sheet.get('race', '')}\n"
        f"Class: {char_sheet.get('class', '')}\n"
        f"Stats: {char_sheet.get('stats', {})}\n\n"
        f"**Dynamic Attributes:** {dynamic}\n"
        f"**Long-Term Memories:** {ltm_count} stored.\n"
    )
    await ctx.send(msg)

@bot.command(name="start_game")
async def start_game(ctx, *args):
    """
    Example command to start a new game with multiple participants.
    Usage: !start_game @User1 @User2
    """
    # Get all mention IDs except the bot
    participants = [m for m in ctx.message.mentions if m != bot.user]
    if not participants:
        await ctx.send("No participants mentioned! Usage: `!start_game @User1 @User2`")
        return

    # Initialize each participant's profile
    for p in participants:
        user_id = str(p.id)
        profile = profile_manager.load_profile(user_id)
        # If they have no name, let's prompt them to fill out their sheet
        if not profile["character_sheet"]["name"]:
            await ctx.send(f"Hey <@{user_id}>, let's create your character sheet! Type `!create_character` to begin.")
        else:
            await ctx.send(f"Looks like <@{user_id}> already has a character: {profile['character_sheet']['name']}")
    await ctx.send("Game has started! Everyone has been initialized. Feel free to ask me about the storyline now.")

@bot.command(name="create_character")
async def create_character(ctx):
    """
    This command triggers a conversation to fill out the user’s character sheet.
    We'll ask them a series of questions. We'll do this interactively.
    """
    user_id = str(ctx.author.id)
    channel = ctx.channel

    profile = profile_manager.load_profile(user_id)
    char_sheet = profile["character_sheet"]

    def check(m):
        # Only accept replies from the same user in the same channel
        return m.author == ctx.author and m.channel == channel

    # Ask for character name
    if not char_sheet.get("name"):
        await ctx.send("What is your character's name?")
        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
            char_sheet["name"] = msg.content.strip()
            profile_manager.update_character_sheet(user_id, {"name": char_sheet["name"]})
            await ctx.send(f"Great! Your character is now named **{char_sheet['name']}**.")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Type `!create_character` again to continue.")
            return
    
    # Ask for race
    if not char_sheet.get("race"):
        await ctx.send("What race is your character? e.g. Elf, Human, Dwarf, etc.")
        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
            char_sheet["race"] = msg.content.strip()
            profile_manager.update_character_sheet(user_id, {"race": char_sheet["race"]})
            await ctx.send(f"Your character's race is now **{char_sheet['race']}**.")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond.")
            return

    # Ask for class
    if not char_sheet.get("class"):
        await ctx.send("What class is your character? e.g. Warrior, Rogue, Wizard, etc.")
        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
            char_sheet["class"] = msg.content.strip()
            profile_manager.update_character_sheet(user_id, {"class": char_sheet["class"]})
            await ctx.send(f"Your character's class is now **{char_sheet['class']}**.")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond.")
            return

    # Ask for stats (STR, DEX, etc.) – for brevity, just do 1 or 2
    if not char_sheet.get("stats"):
        await ctx.send("Let's assign some basic stats. e.g. STR=10, DEX=12, etc. Type them in format: STR=10, DEX=12")
        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
            input_str = msg.content.strip()
            # Very naive parse: "STR=10, DEX=12" -> dict
            stats = {}
            for part in input_str.split(","):
                kv = part.strip().split("=")
                if len(kv) == 2:
                    key = kv[0].strip().upper()
                    val = kv[1].strip()
                    stats[key] = val
            char_sheet["stats"] = stats
            profile_manager.update_character_sheet(user_id, {"stats": stats})
            await ctx.send(f"Stats have been set: {stats}")
        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond.")
            return

    await ctx.send("Character creation complete! Type `!status` to check your data anytime.")

# ----------------------------
# 6. The On-Message Event
# ----------------------------
@bot.event
async def on_message(message):
    # Process commands first
    await bot.process_commands(message)
    if message.author == bot.user:
        return
    if not message.content:
        return

    user_id = str(message.author.id)
    content = message.content.strip()
    
    # Update last activity time
    user_inactivity[user_id] = datetime.now()

    # Add user message to short-term memory
    memory_manager.add_to_short_term(user_id, "user", content)
    memory_manager.trim_and_summarize_if_needed(user_id, profile_manager)

    # If the message mentions the bot or is in a direct channel, respond
    # e.g., check if the bot is mentioned
    if bot.user in message.mentions or isinstance(message.channel, discord.DMChannel):
        try:
            # Build the prompt
            prompt = format_prompt(user_id)
            # Call the model
            async with message.channel.typing():
                response = openai.Completion.create(
                    model=MODEL_NAME,
                    prompt=prompt,
                    temperature=TEMPERATURE,
                    max_tokens=300,
                    top_p=TOP_P,
                    stop=STOP_STRINGS
                )
            
            bot_reply = response.choices[0].text.strip()
            bot_reply = remove_stage_directions(bot_reply)
            bot_reply = force_lowercase_minimal(bot_reply)

            # Add to memory
            memory_manager.add_to_short_term(user_id, "assistant", bot_reply)
            memory_manager.trim_and_summarize_if_needed(user_id, profile_manager)

            await message.channel.send(bot_reply)

        except Exception as e:
            print(f"Error generating response: {e}")
            await message.channel.send("Oops, something went wrong. Please try again later.")

@bot.event
async def on_ready():
    print(f"Bot is online! Logged in as {bot.user}")
    periodic_tasks.start()  # Now the loop is running
# ----------------------------
# 7. Main Entry
# ----------------------------
if __name__ == "__main__":
    # periodic_tasks.start()  # start background tasks
    bot.run(DISCORD_TOKEN)
