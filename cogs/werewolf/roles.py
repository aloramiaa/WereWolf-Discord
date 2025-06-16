import discord
from .core import Role, get_game_ref
from .views import (
    NightActionView, WitchActionView, CupidSelectionView, ArsonistActionView,
    VeteranAlertView
)
from collections import Counter
import random

async def send_early_night_prompts(bot: commands.Bot, game_data: dict):
    """Sends DMs with interactive views to players with non-witch night roles."""
    game_ref = get_game_ref(game_data['channel_id'])
    player_states = game_data.get('player_states', {})
    all_players = game_data.get('players', {})
    
    alive_players_info = [
        {"id": pid, "name": pdata["name"]}
        for pid, pdata in all_players.items()
        if player_states.get(pid, {}).get("is_alive", False)
    ]
    
    werewolves = []
    night_num = game_data.get("game_state", {}).get("night_number", 0)

    for player_id, state in player_states.items():
        if not state.get('is_alive'):
            continue
        
        member = bot.get_guild(game_data['guild_id']).get_member(int(player_id))
        if not member:
            continue

        role = Role(state['role'])
        
        if role == Role.WITCH:
            continue

        if role == Role.CUPID and night_num == 1:
            view = CupidSelectionView(game_ref, player_id, alive_players_info)
            await member.send("Choose two players to strike with your arrow of love, Cupid. Their fates will be forever intertwined.", view=view)
            continue

        if role == Role.ARSONIST:
            view = ArsonistActionView(game_ref, player_id, alive_players_info)
            await member.send("It's time to play with fire, my dear. Will you douse a new target in gasoline, or ignite the world?", view=view)
            continue

        # --- Veteran Action ---
        if role == Role.VETERAN and not game_data.get("game_state", {}).get("veteran_alerts_used", True):
            view = VeteranAlertView(game_ref, player_id)
            await member.send("The night is unsettling. You can choose to go on alert, but you only have one chance.", view=view)
            continue

        # --- Sorcerer Action ---
        if role == Role.SORCERER:
            view = NightActionView(game_ref, player_id, 'sorcerer_pick', alive_players_info)
            await member.send("The werewolves trust in your dark magic. Who do you suspect is the Seer?", view=view)
            continue

        # --- Werewolf Action ---
        if role == Role.WEREWOLF:
            werewolves.append({"id": player_id, "member": member})
            
        elif role == Role.SEER:
            view = NightActionView(game_ref, player_id, 'seer_pick', alive_players_info)
            await member.send("Seer, who do you want to peek at tonight? Choose wisely...", view=view)

        elif role == Role.DOCTOR:
            view = NightActionView(game_ref, player_id, 'doctor_save', alive_players_info)
            await member.send("Doctor, who will you protect with your life-saving medicine tonight?", view=view)
            
        elif role == Role.BODYGUARD:
            view = NightActionView(game_ref, player_id, 'bodyguard_protect', alive_players_info)
            await member.send("Bodyguard, whose life is more important than yours tonight?", view=view)
    
    if werewolves:
        potential_victims = [p for p in alive_players_info if p["id"] not in [w["id"] for w in werewolves]]
        for wolf in werewolves:
            view = NightActionView(game_ref, wolf["id"], 'werewolf_vote', potential_victims)
            await wolf["member"].send("My dear wolf, who shall we feast on tonight? 🐺", view=view)


async def prompt_witch(bot: commands.Bot, game_data: dict):
    """Calculates werewolf target and sends the special prompt to the Witch."""
    witch_id = None
    player_states = game_data.get('player_states', {})
    for pid, state in player_states.items():
        if state.get('is_alive') and state.get('role') == Role.WITCH.value:
            witch_id = pid
            break
            
    if not witch_id:
        return

    game_ref = get_game_ref(game_data['channel_id'])
    potions = game_data.get('game_state', {}).get('witch_potions', {})
    
    if not potions.get('kill') and not potions.get('save'):
        return

    werewolf_target_id = None
    werewolf_target_info = None
    wolf_votes = game_data.get('night_actions', {}).get('werewolf_vote', {})
    if wolf_votes:
        vote_counts = Counter(wolf_votes.values())
        max_votes = vote_counts.most_common(1)[0][1]
        tied_targets = [p_id for p_id, count in vote_counts.items() if count == max_votes]
        werewolf_target_id = random.choice(tied_targets)
        target_player_data = game_data.get('players', {}).get(werewolf_target_id)
        if target_player_data:
            werewolf_target_info = {'id': werewolf_target_id, 'name': target_player_data['name']}

    witch_member = bot.get_guild(game_data['guild_id']).get_member(int(witch_id))
    if not witch_member: return

    prompt_text = "The spirits whisper to you from your hut, Witch..."
    if werewolf_target_info:
        prompt_text += f"\nThey are planning to attack **{werewolf_target_info['name']}** tonight."
    else:
        prompt_text += f"\nThe werewolves were indecisive tonight, and no one was targeted."

    all_players = game_data.get('players', {})
    alive_players_info = [
        {"id": pid, "name": pdata["name"]}
        for pid, pdata in all_players.items()
        if player_states.get(pid, {}).get("is_alive", False)
    ]

    view = WitchActionView(game_ref, witch_id, potions, werewolf_target_info, alive_players_info)
    await witch_member.send(prompt_text, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Roles(bot)) 