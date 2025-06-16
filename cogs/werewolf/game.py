import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from .core import (
    GamePhase, Role, get_game_ref, get_game_data, distribute_roles,
    start_game_loop, ROLE_DESCRIPTIONS, ROLE_COLORS
)

class Game(commands.Cog):
    """Cog for creating and managing Werewolf games."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ww_group = app_commands.Group(name="ww", description="Werewolf game commands")

    @ww_group.command(name="create", description="🌸 Creates a new Werewolf game lobby.")
    async def create(self, interaction: discord.Interaction):
        """Creates a new Werewolf game lobby in the channel."""
        game_ref = get_game_ref(interaction.channel_id)
        if not game_ref:
            await interaction.response.send_message("The database is not connected, master! Please check the configuration.", ephemeral=True)
            return

        if get_game_data(interaction.channel_id):
            await interaction.response.send_message("A game is already in progress in this channel, baka!", ephemeral=True)
            return

        creator = interaction.user
        
        # Default roles for a new game. All special roles are enabled by default.
        default_roles = [role.value for role in Role]

        game_data = {
            "creator_id": creator.id,
            "players": {str(creator.id): {"name": creator.display_name, "mention": creator.mention}},
            "phase": GamePhase.WAITING.value,
            "channel_id": interaction.channel_id,
            "guild_id": interaction.guild_id,
            "settings": {
                "roles": default_roles
            }
        }
        game_ref.set(game_data)

        embed = discord.Embed(
            title="🌸 A New Werewolf Game is Starting! 🌸",
            description=f"The lovely {creator.mention} has started a game of Werewolf! Who will survive the night?!\n\nUse `/ww join` to join the adventure!",
            color=discord.Color.from_rgb(255, 182, 193) # Pink!
        )
        embed.set_thumbnail(url="https://i.imgur.com/8lT4fC5.png") # Cute anime wolf girl
        embed.add_field(name="Players (1)", value=f"✨ {creator.mention}")
        await interaction.response.send_message(embed=embed)


    @ww_group.command(name="join", description="🎀 Joins an existing Werewolf game lobby.")
    async def join(self, interaction: discord.Interaction):
        """Joins the Werewolf game lobby in the channel."""
        game_data = get_game_data(interaction.channel_id)
        game_ref = get_game_ref(interaction.channel_id)

        if not game_ref:
            await interaction.response.send_message("The database is not connected, master! Please check the configuration.", ephemeral=True)
            return

        if not game_data:
            await interaction.response.send_message("There's no game to join here, silly! Use `/ww create` to start one.", ephemeral=True)
            return

        if game_data["phase"] != GamePhase.WAITING.value:
            await interaction.response.send_message("The game has already started! Maybe next time, okay?", ephemeral=True)
            return

        players = game_data.get("players", {})
        if str(interaction.user.id) in players:
            await interaction.response.send_message("You're already in the game, you dork! ❤️", ephemeral=True)
            return

        players[str(interaction.user.id)] = {"name": interaction.user.display_name, "mention": interaction.user.mention}
        game_ref.child("players").set(players)

        player_list = "\n".join([f"✨ {p['mention']}" for p in players.values()])
        embed = discord.Embed(
            title="🎀 A New Challenger Appears! 🎀",
            description=f"{interaction.user.mention} has joined the game! The more the merrier!",
            color=discord.Color.from_rgb(173, 216, 230) # Light Blue
        )
        embed.add_field(name=f"Players ({len(players)})", value=player_list, inline=False)
        await interaction.response.send_message(embed=embed)
    
    @ww_group.command(name="start", description="💖 Starts the Werewolf game.")
    async def start(self, interaction: discord.Interaction):
        """Starts the game, assigns roles, and begins the first night."""
        game_ref = get_game_ref(interaction.channel_id)
        game_data = get_game_data(interaction.channel_id)

        if not game_data:
            await interaction.response.send_message("There's no game to start, sweetie!", ephemeral=True)
            return
        
        if game_data["creator_id"] != interaction.user.id:
            await interaction.response.send_message("Only the one who created the game can start it, okay?", ephemeral=True)
            return

        if game_data["phase"] != GamePhase.WAITING.value:
            await interaction.response.send_message("The game has already started!", ephemeral=True)
            return
        
        players = game_data.get("players", {})
        if len(players) < 4:
             await interaction.response.send_message(f"You can't play with only {len(players)} person! You need at least 4 players for a proper game!", ephemeral=True)
             return

        await interaction.response.send_message("The game is starting... I'm sending everyone their secret roles now! Don't peek, okay? 😉")
        
        await distribute_roles(game_ref, game_data, players)
        
        # We need to refetch the data after roles are distributed
        new_game_data = get_game_data(interaction.channel_id)
        player_roles = new_game_data.get("roles", {})
        player_states = new_game_data.get("player_states", {})
        
        for player_id_str, role_str in player_roles.items():
            player_id = int(player_id_str)
            member = interaction.guild.get_member(player_id)
            if not member: continue

            role_enum = Role(role_str)
            embed = discord.Embed(
                title=f"Your secret role is... {role_enum.value}! 🎭",
                description=f"Shhh... it's a secret!\n\n**Mission:**\n{ROLE_DESCRIPTIONS.get(role_enum)}",
                color=ROLE_COLORS.get(role_enum, discord.Color.default())
            )
            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                await interaction.followup.send(f"I couldn't DM {member.mention}, the poor thing! Please make sure your DMs are open so I can tell you your role!", ephemeral=True)
        
            # --- Inform Executioner of their Target ---
            if role_str == Role.EXECUTIONER.value:
                target_id = player_states.get(player_id_str, {}).get('target_id')
                if target_id and member:
                    target_name = new_game_data.get('players', {}).get(target_id, {}).get('name', 'Unknown')
                    try:
                        await member.send(f"🔪 Your secret target is **{target_name}**. Your mission is to convince the village to lynch them. Good luck.")
                    except discord.Forbidden:
                        pass # They were already warned about DMs being closed

        # Announce werewolves to each other
        werewolves = {pid: pdata for pid, pdata in players.items() if player_roles.get(pid) == Role.WEREWOLF.value}
        wolf_mentions = [p['mention'] for p in werewolves.values()]
        
        for wolf_id in werewolves.keys():
            other_wolves = [p['name'] for pid, p in werewolves.items() if pid != wolf_id]
            wolf_member = interaction.guild.get_member(int(wolf_id))
            if not wolf_member: continue

            if other_wolves:
                await wolf_member.send(f"Your fellow werewolves are: **{', '.join(other_wolves)}**. Work together to bring down the village!")
            else:
                await wolf_member.send("You are the lone wolf. Be careful out there!")

        # Start the game loop in the background
        asyncio.create_task(start_game_loop(self.bot, interaction.channel_id))


async def setup(bot: commands.Bot):
    await bot.add_cog(Game(bot))
