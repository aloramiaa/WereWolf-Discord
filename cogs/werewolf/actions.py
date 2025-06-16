import discord
from discord import app_commands
from discord.ext import commands
from .core import GamePhase, get_game_ref, get_game_data
from .views import VotingView

class Actions(commands.Cog):
    """Cog for player actions during the Werewolf game."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Commands for voting, checking roles, etc., will go here.
    # We will use interactive views and buttons for a stylish experience.

    ww_group = app_commands.Group(name="ww", description="Werewolf game commands")

    @ww_group.command(name="vote", description="🗳️ Vote to lynch a player during the day.")
    async def vote(self, interaction: discord.Interaction):
        """Allows a player to vote to lynch someone."""
        game_data = get_game_data(interaction.channel_id)
        game_ref = get_game_ref(interaction.channel_id)
        player_id = str(interaction.user.id)

        if not game_data:
            await interaction.response.send_message("There's no game happening right now, sweetie.", ephemeral=True)
            return

        if game_data.get("phase") != GamePhase.DAY.value:
            await interaction.response.send_message("You can only vote during the day! Patience, my dear.", ephemeral=True)
            return
            
        player_states = game_data.get("player_states", {})
        if not player_states.get(player_id, {}).get("is_alive"):
            await interaction.response.send_message("Ghosts can't vote, silly! You're dead. 👻", ephemeral=True)
            return
            
        all_players = game_data.get("players", {})
        alive_players_info = [
            {"id": pid, "name": pdata["name"]}
            for pid, pdata in all_players.items()
            if player_states.get(pid, {}).get("is_alive", False) and pid != player_id # Can't vote for yourself
        ]
        
        if not alive_players_info:
            await interaction.response.send_message("There's no one else to vote for!", ephemeral=True)
            return
            
        view = VotingView(game_ref, player_id, alive_players_info)
        await interaction.response.send_message("The time has come to cast your vote. Choose carefully...", view=view, ephemeral=True)

    @ww_group.command(name="reveal", description="👑 Reveal yourself as the Mayor (Mayor only).")
    async def reveal(self, interaction: discord.Interaction):
        """Allows the Mayor to reveal themselves, making their vote count as two."""
        game_data = get_game_data(interaction.channel_id)
        game_ref = get_game_ref(interaction.channel_id)
        player_id = str(interaction.user.id)
        player_state = game_data.get("player_states", {}).get(player_id)

        if not player_state or player_state.get("role") != "Mayor":
            await interaction.response.send_message("You are not the Mayor! This action is not for you, little one.", ephemeral=True)
            return

        if not player_state.get("is_alive"):
            await interaction.response.send_message("You can't reveal yourself when you're a ghost, silly! 👻", ephemeral=True)
            return

        if player_state.get("is_mayor_revealed"):
            await interaction.response.send_message("You have already revealed yourself as the Mayor!", ephemeral=True)
            return

        # Update the database
        game_ref.child('player_states').child(player_id).child('is_mayor_revealed').set(True)

        # Make a grand announcement
        embed = discord.Embed(
            title="👑 A Leader Steps Forward! 👑",
            description=f"Hear ye, hear ye! {interaction.user.mention} has revealed themselves as the **Mayor** of the village! Their vote will now count as **two** during the daily lynch.",
            color=ROLE_COLORS[Role.MAYOR]
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text="The political landscape has shifted...")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Actions(bot)) 