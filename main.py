import discord
from discord.ext import commands
import os
import asyncio
import firebase_config # This will initialize firebase

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print(f'Anime-style commands at your service, master!')

@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')

# Owner-only command to sync slash commands to Discord
@bot.command()
@commands.is_owner()
async def sync(ctx: commands.Context):
    """Syncs slash commands to the current guild or globally."""
    await ctx.send("Syncing slash commands... Senpai, please wait a moment! ✨")
    # To sync to a specific guild, use:
    # bot.tree.copy_global_to(guild=ctx.guild)
    # synced = await bot.tree.sync(guild=ctx.guild)
    
    # Sync globally
    synced = await bot.tree.sync()

    await ctx.send(f"Phew! I've synced {len(synced)} commands. They're all ready for you!")

async def load_cogs():
    """Loads all cogs from the cogs directory and its subdirectories."""
    for root, dirs, files in os.walk('./cogs'):
        for filename in files:
            if filename.endswith('.py') and not filename.startswith('__init__'):
                # Construct the extension path like: cogs.werewolf.game
                path = os.path.join(root, filename)
                # make it a python module path
                extension_path = path.replace(os.path.sep, '.')[:-3]
                print(f"Attempting to load extension: {extension_path}")
                try:
                    await bot.load_extension(extension_path)
                    print(f'Loaded extension: {extension_path}')
                except Exception as e:
                    print(f'Failed to load extension {extension_path}: {e}')

async def main():
    async with bot:
        await load_cogs()
        token = os.environ.get('DISCORD_BOT_TOKEN')
        if not token or token == 'YOUR_BOT_TOKEN':
            print('ERROR: DISCORD_BOT_TOKEN environment variable not set!')
            return
        await bot.start(token)

if __name__ == "__main__":
    # Ensure you have a .env file with DISCORD_BOT_TOKEN='your_token'
    # or replace 'YOUR_BOT_TOKEN' directly
    asyncio.run(main()) 