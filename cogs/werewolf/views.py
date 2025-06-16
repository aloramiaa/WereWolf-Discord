import discord

# This file will contain all the discord.ui.View classes for interactive components,
# like night action selection menus and voting buttons.

class ActionSelect(discord.ui.Select):
    """A stylish select menu for choosing a player to perform an action on."""
    def __init__(self, game_ref, acting_player_id, action_type: str, players: list, *args, **kwargs):
        self.game_ref = game_ref
        self.acting_player_id = acting_player_id
        self.action_type = action_type # e.g., 'werewolf_vote', 'seer_pick'
        
        options = [
            discord.SelectOption(label=player['name'], value=player['id'], description=f"Select {player['name']}")
            for player in players
        ]
        super().__init__(placeholder="Choose your target, my dear...", min_values=1, max_values=1, options=options, *args, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        # The user has made their choice
        chosen_player_id = self.values[0]
        
        # Store the action in firebase under a 'night_actions' key
        self.game_ref.child('night_actions').child(self.action_type).child(self.acting_player_id).set(chosen_player_id)
        
        # Give some cute feedback and disable the view
        await interaction.response.send_message(f"You have chosen your target... The spirits have heard your wish. ✨", ephemeral=True)
        self.view.stop()
        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(view=self.view)


class NightActionView(discord.ui.View):
    """A generic view that holds a night action select menu."""
    def __init__(self, game_ref, acting_player_id, action_type: str, players: list, *args, **kwargs):
        super().__init__(timeout=60.0, *args, **kwargs) # 60 second timeout for night actions
        self.add_item(ActionSelect(game_ref, acting_player_id, action_type, players))

    async def on_timeout(self):
        # Clean up the message after the timeout
        for item in self.children:
            item.disabled = True
        # You might want to get the original message and edit it.
        # This requires passing the message object to the view or fetching it. 

class VoteSelect(discord.ui.Select):
    """A select menu for choosing who to vote to lynch."""
    def __init__(self, game_ref, acting_player_id, players: list):
        self.game_ref = game_ref
        self.acting_player_id = acting_player_id
        
        options = [
            discord.SelectOption(label=player['name'], value=player['id'], description=f"Vote to lynch {player['name']}")
            for player in players
        ]
        super().__init__(placeholder="Choose who to vote for...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        chosen_player_id = self.values[0]
        
        # Store the vote in Firebase under a 'day_votes' key
        self.game_ref.child('day_votes').child(self.acting_player_id).set(chosen_player_id)
        
        await interaction.response.send_message(f"Your vote has been cast... The village is watching. 👀", ephemeral=True)
        self.view.stop()
        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(view=self.view)

class VotingView(discord.ui.View):
    """A view that holds the voting select menu."""
    def __init__(self, game_ref, acting_player_id, players: list):
        super().__init__(timeout=30.0) # 30 second timeout to vote
        self.add_item(VoteSelect(game_ref, acting_player_id, players))


class WitchActionView(discord.ui.View):
    """A highly interactive view for the Witch's night actions."""
    def __init__(self, game_ref, witch_id, potions: dict, werewolf_target: dict, all_players: list):
        super().__init__(timeout=30.0)
        self.game_ref = game_ref
        self.witch_id = witch_id
        self.werewolf_target = werewolf_target
        self.all_players = all_players
        
        # Add save button if potion is available and there's a target
        if potions.get("save") and self.werewolf_target:
            self.add_item(WitchSaveButton(target_name=self.werewolf_target['name']))
        
        # Add kill button if potion is available
        if potions.get("kill"):
            self.add_item(WitchKillButton())

    async def handle_kill_choice(self, interaction: discord.Interaction):
        """Called by the kill button to show the player selection."""
        # Clear existing buttons and add a dropdown to choose a kill target
        self.clear_items()
        self.add_item(ActionSelect(self.game_ref, self.witch_id, 'witch_kill', self.all_players))
        await interaction.response.edit_message(content="Such a wicked choice... Who will you kill?", view=self)


class WitchSaveButton(discord.ui.Button):
    def __init__(self, target_name: str):
        super().__init__(label=f"Use Save Potion on {target_name}", style=discord.ButtonStyle.green, custom_id="witch_save")

    async def callback(self, interaction: discord.Interaction):
        # Save the action to firebase
        self.view.game_ref.child('night_actions').child('witch_save').set(True)
        # Mark potion as used
        self.view.game_ref.child('game_state/witch_potions/save').set(False)
        
        await interaction.response.send_message("You've used your save potion. A life is spared... for now.", ephemeral=True)
        
        # Disable this button
        self.disabled = True
        await interaction.message.edit(view=self.view)

class WitchKillButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Use Kill Potion", style=discord.ButtonStyle.red, custom_id="witch_kill")

    async def callback(self, interaction: discord.Interaction):
        # The view will handle replacing this button with a dropdown
        await self.view.handle_kill_choice(interaction)


class CupidSelect(discord.ui.Select):
    """A select menu for Cupid to choose two lovers."""
    def __init__(self, game_ref, cupid_id, players: list):
        self.game_ref = game_ref
        self.cupid_id = cupid_id
        
        options = [
            discord.SelectOption(label=player['name'], value=player['id'], description=f"Select {player['name']} as a lover.")
            for player in players
        ]
        # Important: min_values and max_values are 2 for Cupid
        super().__init__(placeholder="Choose two players to link with love's arrow...", min_values=2, max_values=2, options=options)

    async def callback(self, interaction: discord.Interaction):
        lover1_id, lover2_id = self.values[0], self.values[1]
        
        # Store the lovers in a dedicated space in Firebase
        self.game_ref.child('lovers').set({lover1_id: lover2_id, lover2_id: lover1_id})
        
        await interaction.response.send_message(f"Your arrow has struck true! A new love story begins... or ends? 💘", ephemeral=True)
        self.view.stop()
        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(view=self.view)

class CupidSelectionView(discord.ui.View):
    """A view that holds Cupid's unique selection menu."""
    def __init__(self, game_ref, cupid_id, players: list):
        super().__init__(timeout=60.0) # Give Cupid a little more time
        self.add_item(CupidSelect(game_ref, cupid_id, players))


class ArsonistActionView(discord.ui.View):
    """A view for the Arsonist to choose to douse or ignite."""
    def __init__(self, game_ref, arsonist_id, players: list):
        super().__init__(timeout=60.0)
        self.game_ref = game_ref
        
        # Add the ignite button
        self.add_item(ArsonistIgniteButton())

        # Add the douse dropdown, excluding self
        douse_options = [p for p in players if p['id'] != arsonist_id]
        self.add_item(ActionSelect(game_ref, arsonist_id, 'arsonist_douse', douse_options))


class ArsonistIgniteButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🔥 IGNITE ALL DOUSED TARGETS 🔥", style=discord.ButtonStyle.danger, custom_id="arsonist_ignite")

    async def callback(self, interaction: discord.Interaction):
        # The Arsonist has chosen to ignite.
        self.view.game_ref.child('night_actions').child('arsonist_ignite').set(True)
        
        await interaction.response.send_message("The world will burn... Your choice has been sealed.", ephemeral=True)
        self.view.stop()
        for item in self.view.children:
            item.disabled = True
        await interaction.message.edit(view=self.view)


class VeteranAlertView(discord.ui.View):
    """A view for the Veteran to choose to go on alert."""
    def __init__(self, game_ref, veteran_id: str):
        super().__init__(timeout=60.0)
        self.game_ref = game_ref
        self.veteran_id = veteran_id

    @discord.ui.button(label="Go on Alert", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def go_on_alert(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Callback for the veteran alert button."""
        # Record that the veteran is on alert for the night
        self.game_ref.child('night_actions').child('veteran_alert').set(self.veteran_id)
        # Mark the alert as used
        self.game_ref.child('game_state').child('veteran_alerts_used').set(True)

        await interaction.response.send_message("You have barricaded your house for the night. You will shoot anyone who visits.", ephemeral=True)
        self.view.stop()
        button.disabled = True
        await interaction.message.edit(view=self.view)


# --- Settings Views ---

class RoleSelect(discord.ui.Select):
    """A multi-select dropdown for enabling/disabling roles."""
    def __init__(self, game_ref, all_possible_roles, enabled_roles):
        self.game_ref = game_ref
        
        options = []
        for role in all_possible_roles:
            # Villager and Werewolf are mandatory, so they are not included here
            if role in [Role.VILLAGER, Role.WEREWOLF]:
                continue
            options.append(
                discord.SelectOption(
                    label=role.value,
                    value=role.value,
                    description=f"Enable or disable the {role.value} role.",
                    default=role.value in enabled_roles
                )
            )

        super().__init__(
            placeholder="Select the special roles for this game...",
            min_values=0,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # The user has confirmed their selection. Update the database.
        # We always include Villager and Werewolf.
        enabled_roles = self.values
        enabled_roles.extend([Role.VILLAGER.value, Role.WEREWOLF.value])
        
        self.game_ref.child('settings').child('roles').set(enabled_roles)
        
        await interaction.response.send_message("The prophecy has been written! I have updated the roles for this game. ✨", ephemeral=True)
        
        # We need to refresh the main settings view
        # This part will be handled by the button that opens this view.

class RoleSettingsView(discord.ui.View):
    """A view for managing role settings."""
    def __init__(self, game_ref, all_possible_roles, enabled_roles):
        super().__init__(timeout=180.0)
        self.add_item(RoleSelect(game_ref, all_possible_roles, enabled_roles))


class SettingsView(discord.ui.View):
    """The main view for game settings, shown with the /ww settings command."""
    def __init__(self, game_ref, game_data):
        super().__init__(timeout=180.0)
        self.game_ref = game_ref
        self.game_data = game_data

    @discord.ui.button(label="Configure Roles", style=discord.ButtonStyle.primary, emoji="🎭")
    async def configure_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Opens the role selection view."""
        all_roles = [role for role in Role]
        enabled_roles = self.game_data.get('settings', {}).get('roles', [])
        
        view = RoleSettingsView(self.game_ref, all_roles, enabled_roles)
        await interaction.response.send_message("Choose the roles you wish to include in this game, master.", view=view, ephemeral=True)