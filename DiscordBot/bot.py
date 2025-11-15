import os
import discord
from discord import app_commands
from dotenv import load_dotenv
from openai import OpenAI
import requests
import aiohttp
import asyncio

# ─── CONFIG ───────────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=r"C:\Users\Thoma\OneDrive\Documents\DiscordBot\.env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 👇 Replace these with your actual values
APPLICATION_ID = "1438293505536692366"   # GV Staff Bot V2 App ID

# MULTIPLE GUILD SUPPORT
GUILD_IDS = [
    "1434247018343043219",   # Server 1
     "1438622173911842969",  # Add more here
]

# ─── OPENAI CLIENT ────────────────────────────────────────────────────────────
client_ai = OpenAI(api_key=OPENAI_API_KEY)

# ─── DISCORD CLIENT SETUP ─────────────────────────────────────────────────────
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ─── LOAD RULES FILE ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are GV Staff Bot — a professional rules assistant.
Answer only from the rules below; if not specified, say 'Not specified. Please ask a moderator.'"""

def load_rules():
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "No rules file found."

RULES_TEXT = load_rules()

def ask_openai(question: str) -> str:
    ctx = f"SERVER RULES:\n{RULES_TEXT}\n\nQUESTION: {question}"
    r = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": ctx},
        ],
        temperature=0.2,
        max_tokens=500,
    )
    return r.choices[0].message.content.strip()

# ─── SLASH COMMANDS ───────────────────────────────────────────────────────────
@tree.command(name="pingv2", description="Replies with Pong! Used to test sync.")
async def pingv2(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong from GV Staff Bot V2!")

@tree.command(name="rulesv2", description="Ask about the server rules (GV Staff Bot V2).")
@app_commands.describe(question="What do you want to know?")
async def rulesv2(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)
    try:
        answer = ask_openai(question)
        if len(answer) > 1900:
            answer = answer[:1900] + "..."
        await interaction.followup.send(answer)
    except Exception as e:
        await interaction.followup.send("Something went wrong.")
        print("Error:", e)

# ─── REGISTER COMMANDS VIA REST API ───────────────────────────────────────────
async def push_commands():
    commands = [
        {"name": "pingv2", "description": "Replies with Pong! Used to test sync.", "type": 1},
        {
            "name": "rulesv2",
            "description": "Ask about the server rules (GV Staff Bot V2).",
            "options": [
                {
                    "name": "question",
                    "description": "What do you want to know?",
                    "type": 3,
                    "required": True,
                }
            ],
        },
    ]

    headers = {"Authorization": f"Bot {DISCORD_TOKEN}", "Content-Type": "application/json"}

    print("📡 Sending commands to all guilds...")

    for gid in GUILD_IDS:
        url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/guilds/{gid}/commands"

        print(f"\n🔹 Updating guild: {gid}")

        # Push commands
        for cmd in commands:
            r = requests.post(url, headers=headers, json=cmd)
            print(f"   → {cmd['name']} ({r.status_code})")

        # Verify by fetching them back
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as r:
                data = await r.json()
                print(f"   ✓ {len(data)} commands registered:")
                for c in data:
                    print("      -", c["name"])

# ─── MAIN READY EVENT ─────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print("Commands in tree:", [c.name for c in tree.get_commands()])
    await push_commands()
    print("✅ Try /pingv2 or /rulesv2 in Discord after refreshing (Ctrl+R).")

# ─── RUN ──────────────────────────────────────────────────────────────────────
bot.run(DISCORD_TOKEN)
