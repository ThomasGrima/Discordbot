import os, aiohttp, asyncio
from dotenv import load_dotenv

load_dotenv(r"C:\Users\Thoma\OneDrive\Documents\DiscordBot\.env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
APPLICATION_ID = "1438293505536692366"  # your V2 app id
GUILD_ID = "1113585879710179451"

async def main():
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(
            f"https://discord.com/api/v10/applications/{APPLICATION_ID}/guilds/{GUILD_ID}/commands"
        ) as r:
            data = await r.json()
            print(f"🏠 Guild commands ({len(data)}):")
            for c in data:
                print(" -", c["name"])
        async with session.get(
            f"https://discord.com/api/v10/applications/{APPLICATION_ID}/commands"
        ) as r:
            global_cmds = await r.json()
            print(f"🌍 Global commands ({len(global_cmds)}):")
            for c in global_cmds:
                print(" -", c["name"])

asyncio.run(main())
