import discord
from discord.ext import commands
from discord import app_commands
from firebase_admin import db

from .core import Role, get_game_ref_for_channel, check_game_host

class RoleToggle(discord.ui.Button):
    """A button to toggle a specific role on or off for the game."""
    def __init__(self, role: Role, enabled: bool = False):
        self.role = role
        # Set the style based on whether the role is enabled
        super().__init__(
            label=role.value,
            style=discord.ButtonStyle.green if enabled else discord.ButtonStyle.grey,
            custom_id=f"toggle_{role.name}"
        )

    async def callback(self, interaction: discord.Interaction):
        # Defer to prevent "interaction failed" on longer operations
        await interaction.response.defer(ephemeral=True)

        game_ref = get_game_ref_for_channel(interaction.channel_id)
        if game_ref is None:
            await interaction.followup.send("No game is running in this channel.", ephemeral=True)
            return
        
        if not await check_game_host(interaction.user.id, game_ref):
             await interaction.followup.send("Only the game host can change settings.", ephemeral=True)
             return

        enabled_roles_ref = game_ref.child('settings/enabled_roles')
        current_roles = enabled_roles_ref.get() or []

        role_name = self.role.value
        
        # Toggle the role and button style
        if role_name in current_roles:
            current_roles.remove(role_name)
            self.style = discord.ButtonStyle.grey
        else:
            current_roles.append(role_name)
            self.style = discord.ButtonStyle.green
            
        enabled_roles_ref.set(current_roles)

        # Update the original message to show the new button styles
        await interaction.message.edit(view=self.view)
        await interaction.followup.send(f"Role '{role_name}' has been {'enabled' if self.style == discord.ButtonStyle.green else 'disabled'}.", ephemeral=True)


class SettingsView(discord.ui.View):
    def __init__(self, game_ref: db.Reference, enabled_roles: list):
        super().__init__(timeout=180)
        
        # Define all possible special roles
        all_special_roles = [
            Role.JESTER, Role.EXECUTIONER, Role.ARSONIST, Role.MAYOR, 
            Role.VETERAN, Role.ALPHA_WOLF, Role.SORCERER
        ]

        # Create a toggle button for each role
        for role in all_special_roles:
            is_enabled = role.value in enabled_roles
            self.add_item(RoleToggle(role, enabled=is_enabled))


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ww-settings", description="Change the roles for the next Werewolf game.")
    @app_commands.guild_only()
    async def ww_settings(self, interaction: discord.Interaction):
        game_ref = get_game_ref_for_channel(interaction.channel_id)
        if game_ref is None:
            return await interaction.response.send_message("There is no game running in this channel to configure.", ephemeral=True)

        if not await check_game_host(interaction.user.id, game_ref):
            return await interaction.response.send_message("Only the game host can change the settings.", ephemeral=True)
            
        game_state = game_ref.child('state/phase').get()
        if game_state != 'lobby':
            return await interaction.response.send_message("Settings can only be changed while the game is in the lobby.", ephemeral=True)

        enabled_roles = game_ref.child('settings/enabled_roles').get() or []
        
        embed = discord.Embed(
            title="🐺 Werewolf Game Settings 🔮",
            description="Click the buttons below to toggle special roles for this game. Green means the role is enabled, grey means disabled.",
            color=discord.Color.purple()
        )
        view = SettingsView(game_ref, enabled_roles)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))