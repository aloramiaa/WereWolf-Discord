import discord
from discord import app_commands
from discord.ext import commands
from .core import get_game_ref, get_game_data, GamePhase
from .views import SettingsView

class Admin(commands.Cog):
    """Cog for administrative Werewolf commands."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    ww_group = app_commands.Group(name="ww", description="Werewolf game commands")

    @ww_group.command(name="settings", description="⚙️ Adjust the settings for the current game.")
    async def settings(self, interaction: discord.Interaction):
        """Allows the game creator to change settings before the game starts."""
        game_data = get_game_data(interaction.channel_id)
        game_ref = get_game_ref(interaction.channel_id)

        if not game_data:
            await interaction.response.send_message("There's no game to configure, silly!", ephemeral=True)
            return
            
        if game_data["creator_id"] != interaction.user.id:
            await interaction.response.send_message("Only the person who created the game can change the settings!", ephemeral=True)
            return
            
        if game_data["phase"] != GamePhase.WAITING.value:
            await interaction.response.send_message("You can't change settings after the game has started!", ephemeral=True)
            return

        # Create a beautiful embed to show current settings
        enabled_roles = game_data.get('settings', {}).get('roles', [])
        
        embed = discord.Embed(
            title="✨ Game Settings ✨",
            description="Here are the current settings for your game. Use the buttons below to make changes, master!",
            color=discord.Color.from_rgb(255, 209, 220) # A nice pastel pink
        )
        embed.add_field(
            name="🎭 Enabled Roles",
            value=" ".join([f"`{role}`" for role in enabled_roles]),
            inline=False
        )
        # TODO: Add fields for timers, etc. in the future

        view = SettingsView(game_ref, game_data)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @ww_group.command(name="end", description="💔 Ends the current Werewolf game.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def end(self, interaction: discord.Interaction):
        """Ends the game in the channel (moderator only)."""
        game_ref = get_game_ref(interaction.channel_id)
        if not get_game_data(interaction.channel_id):
            await interaction.response.send_message("There's no game to end here.", ephemeral=True)
            return

        game_ref.delete()
        embed = discord.Embed(
            title="💔 Game Over 💔",
            description="The game has been ended by a moderator. Thank you for playing!",
            color=discord.Color.dark_grey()
        )
        await interaction.response.send_message(embed=embed)

    @end.error
    async def end_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("H-Hey! You can't do that! You need the `Manage Channels` permission to end a game.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Something went wrong... I'm so sorry! Please tell my master! {error}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot)) 