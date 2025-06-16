import discord
from enum import Enum
from firebase_config import get_db
import random
import asyncio
from .roles import send_night_action_prompts, send_early_night_prompts, prompt_witch
from collections import Counter

class GamePhase(Enum):
    WAITING = "WAITING"
    NIGHT = "NIGHT"
    DAY = "DAY"
    VOTING = "VOTING"
    ENDED = "ENDED"

class Role(Enum):
    WEREWOLF = "Werewolf"
    VILLAGER = "Villager"
    SEER = "Seer"
    DOCTOR = "Doctor"
    WITCH = "Witch"
    HUNTER = "Hunter"
    CUPID = "Cupid"
    BODYGUARD = "Bodyguard"
    JESTER = "Jester"
    EXECUTIONER = "Executioner"
    ARSONIST = "Arsonist"
    MAYOR = "Mayor"
    VETERAN = "Veteran"
    ALPHA_WOLF = "Alpha Wolf"
    SORCERER = "Sorcerer"

# --- Role Information ---
ROLE_DESCRIPTIONS = {
    Role.WEREWOLF: "Each night, you and your fellow werewolves choose one person to kill. Don't get caught, little wolf~",
    Role.VILLAGER: "You are a simple, pure-hearted villager. Your goal is to find and lynch all the werewolves. Good luck!",
    Role.SEER: "Each night, you can choose one person to learn their true role. Use your insight to guide the village!",
    Role.DOCTOR: "Each night, you can choose one person to save from a werewolf attack. Will you save the right person?",
    Role.WITCH: "You have two powerful potions: one to kill a player, and one to save a player. You can only use each once per game.",
    Role.HUNTER: "If you are killed, you get to take one person down with you. A final, beautiful act of revenge!",
    Role.CUPID: "On the first night, you choose two players to fall in love. If one dies, the other dies of a broken heart. How romantic!",
    Role.BODYGUARD: "Each night, you may choose one person to protect. If they are attacked, you will die in their place. So heroic!",
    Role.JESTER: "You are a lonely fool whose only goal is to get yourself lynched by the village. Trick them into voting against you to win!",
    Role.EXECUTIONER: "You have one goal: get your target lynched at all costs. If you succeed, you win the game. Your target will be revealed to you at the start of the game.",
    Role.ARSONIST: "Each night, you can choose to douse someone in gasoline. At any point, instead of dousing, you can choose to ignite all players you have doused. Win when you are the last one standing.",
    Role.MAYOR: "You are a respected member of the village. Once per game, you can reveal yourself as the Mayor. When you do, your vote during the day counts as two.",
    Role.VETERAN: "You are a paranoid war hero. Once per game, you can go on 'alert' for the night. While on alert, you are immune to attack, and anyone who visits you will be shot.",
    Role.ALPHA_WOLF: "You are the leader of the pack. If you are lynched by the village, you get to convert the last person who voted for you into a new werewolf.",
    Role.SORCERER: "You are a human on the side of the werewolves. Each night, you can check if a player is the Seer.",
}

ROLE_COLORS = {
    Role.WEREWOLF: discord.Color.from_rgb(255, 87, 87), # Red
    Role.VILLAGER: discord.Color.from_rgb(137, 207, 240), # Blue
    Role.SEER: discord.Color.from_rgb(171, 71, 188), # Purple
    Role.DOCTOR: discord.Color.from_rgb(129, 212, 250), # Light Blue
    Role.WITCH: discord.Color.from_rgb(88, 24, 99), # Dark Purple
    Role.HUNTER: discord.Color.from_rgb(139, 69, 19), # Brown
    Role.CUPID: discord.Color.from_rgb(255, 182, 193), # Pink
    Role.BODYGUARD: discord.Color.from_rgb(112, 128, 144), # Slate Gray
    Role.JESTER: discord.Color.from_rgb(255, 165, 0), # Orange
    Role.EXECUTIONER: discord.Color.from_rgb(48, 48, 48), # Dark Grey
    Role.ARSONIST: discord.Color.from_rgb(230, 81, 0), # Burnt Orange
    Role.MAYOR: discord.Color.from_rgb(255, 215, 0), # Gold
    Role.VETERAN: discord.Color.from_rgb(0, 51, 102), # Navy Blue
    Role.ALPHA_WOLF: discord.Color.from_rgb(153, 0, 0), # Dark Red
    Role.SORCERER: discord.Color.from_rgb(118, 42, 131), # Dark Magenta
}

# This file will hold our core game logic, data models, and database interactions.
# It's not a cog, but a helper module for the other cogs.

def get_game_ref(channel_id: int):
    """Gets the Firebase reference for a game in a specific channel."""
    db = get_db()
    if not db:
        return None
    return db.child('games').child(str(channel_id))

def get_game_data(channel_id: int):
    """Retrieves the game data from Firebase."""
    game_ref = get_game_ref(channel_id)
    if not game_ref:
        return None
    return game_ref.get()

def check_game_host(user_id, game_ref):
    game_data = game_ref.get()
    return game_data and game_data.get('creator_id') == user_id

# --- Core Game Logic ---
async def distribute_roles(game_ref, game_data: dict, players: dict):
    """Assigns roles to players based on game settings and stores them in Firebase."""
    player_ids = list(players.keys())
    random.shuffle(player_ids)
    num_players = len(player_ids)

    # This is the key change: read roles from settings!
    enabled_roles_str = game_data.get("settings", {}).get("roles", [r.value for r in Role])
    enabled_roles = [Role(rs) for rs in enabled_roles_str]

    # Dynamically select special roles from the enabled list
    special_roles = [r for r in enabled_roles if r not in [Role.VILLAGER, Role.WEREWOLF]]
    random.shuffle(special_roles)
    
    # Simple werewolf count for now, can be a setting later
    num_werewolves = max(1, num_players // 4)
    
    roles_to_assign = []

    # Assign Sorcerer first if enabled
    if Role.SORCERER in enabled_roles:
        roles_to_assign.append(Role.SORCERER)
        # Ensure there's at least one werewolf for the Sorcerer to side with
        if num_werewolves == 0:
            num_werewolves = 1
    
    roles_to_assign.extend([Role.WEREWOLF] * num_werewolves)
    
    # Designate one werewolf as the Alpha Wolf if there's more than one
    if num_werewolves > 1 and Role.ALPHA_WOLF in enabled_roles:
        roles_to_assign[0] = Role.ALPHA_WOLF

    # Fill with special roles, up to the number of available slots
    slots_for_specials = num_players - len(roles_to_assign)
    
    for i in range(min(len(special_roles), slots_for_specials)):        
        roles_to_assign.append(special_roles.pop())
    
    # Fill the rest with Villagers
    roles_to_assign += [Role.VILLAGER] * (num_players - len(roles_to_assign))
    random.shuffle(roles_to_assign)

    player_roles = {player_id: role.value for player_id, role in zip(player_ids, roles_to_assign)}
    
    # Set initial player state
    player_states = {}
    for p_id in player_ids:
        player_states[p_id] = {
            "role": player_roles[p_id],
            "is_alive": True,
            "is_protected": False,
            "is_healed_by_witch": False,
            "lover_id": None,
            "is_doused": False,
            "is_mayor_revealed": False,
            "veteran_alerts": 1, # Starting alerts
            "is_on_alert": False,
        }
    
    # Assign Executioner's target
    executioner_id = None
    for p_id, role_str in player_roles.items():
        if role_str == Role.EXECUTIONER.value:
            executioner_id = p_id
            break
    
    if executioner_id:
        potential_targets = [
            p_id for p_id, role_str in player_roles.items() 
            if role_str != Role.EXECUTIONER.value and role_str != Role.WEREWOLF.value
        ]
        if potential_targets:
            target_id = random.choice(potential_targets)
            player_states[executioner_id]['target_id'] = target_id

    game_ref.child("roles").set(player_roles)
    game_ref.child("player_states").set(player_states)
    game_ref.child("game_state").set({
        "night_number": 0,
        "phase": GamePhase.NIGHT.value,
        "witch_potions": { "kill": True, "save": True },
        "veteran_alerts_used": False, # To track if the single alert is used
    })


async def start_game_loop(bot: commands.Bot, channel_id: int):
    """The main game loop that transitions between night and day."""
    await asyncio.sleep(5) # Give a moment for DMs to be sent
    
    # --- Handle First Night Lover DMs ---
    game_data = get_game_data(channel_id)
    if game_data.get("game_state", {}).get("night_number") == 1:
        await asyncio.sleep(60) # Wait for cupid to choose
        game_data = get_game_data(channel_id)
        await dm_lovers(bot, game_data)

    while True:
        game_ref = get_game_ref(channel_id)
        game_data = game_ref.get()
        if not game_data or game_data.get("phase") == GamePhase.ENDED.value:
            break
        
        # --- NIGHT PHASE ---
        await start_night_phase(bot, channel_id, game_data)
        await asyncio.sleep(30) # 30 seconds for initial actions

        # --- WITCH PHASE ---
        game_data = get_game_data(channel_id) # Refetch data to get wolf votes
        if not game_data: break
        await prompt_witch(bot, game_data) # A new function to prompt the witch
        await asyncio.sleep(30) # 30 seconds for the witch to act

        # --- DAY PHASE ---
        game_data = get_game_data(channel_id) # Refetch data for all actions
        if not game_data: break
        await start_day_phase(bot, channel_id, game_data)
        
        # We check win condition after day announcement because of Hunter/Lover deaths
        # This is tricky, a better way might be to re-check win condition inside start_day_phase after deaths.
        new_game_data = get_game_data(channel_id)
        if not new_game_data: break
        if await check_win_condition(bot, channel_id, new_game_data):
            break

        # --- VOTING PHASE ---
        day_discussion_duration = 120 # 2 minutes for discussion
        channel = bot.get_channel(channel_id)
        await channel.send(f"You have {day_discussion_duration} seconds to discuss and cast your votes using `/ww vote`!")
        await asyncio.sleep(day_discussion_duration)

        # Refetch data to get all the new day_votes
        game_data = get_game_data(channel_id)
        if not game_data: break

        lynch_story, lynched_id = await process_lynch_votes(game_data)
        
        # --- JESTER/EXECUTIONER WIN CONDITION CHECK ---
        if lynched_id:
            # Check for Jester Win
            lynched_role = game_data.get("player_states", {}).get(lynched_id, {}).get("role")
            if lynched_role == Role.JESTER.value:
                jester_name = game_data.get("players", {}).get(lynched_id, {}).get("name", "The Jester")
                jester_win_embed = discord.Embed(
                    title="😂 The Jester Wins! 😂",
                    description=f"The village has been played for fools! You have lynched **{jester_name}**, the Jester, which was their goal all along! The Jester wins the game, laughing all the way from the grave.",
                    color=ROLE_COLORS[Role.JESTER]
                )
                jester_win_embed.set_image(url="https://i.imgur.com/gB41pPE.gif") # Jester gif
                jester_win_embed.set_footer(text="The game is over!")
                await channel.send(embed=jester_win_embed)
                get_game_ref(channel_id).delete()
                break # End the game loop

            # Check for Executioner Win
            player_states = game_data.get("player_states", {})
            for pid, state in player_states.items():
                if state.get("role") == Role.EXECUTIONER.value and state.get("target_id") == lynched_id:
                    exe_name = game_data.get("players", {}).get(pid, {}).get("name", "The Executioner")
                    target_name = game_data.get("players", {}).get(lynched_id, {}).get("name", "their target")
                    exe_win_embed = discord.Embed(
                        title="🔪 The Executioner Wins! 🔪",
                        description=f"The village has been manipulated! **{exe_name}** has successfully convinced you to lynch their target, **{target_name}**. The Executioner's personal vendetta is complete, and they win the game!",
                        color=ROLE_COLORS[Role.EXECUTIONER]
                    )
                    exe_win_embed.set_image(url="https://i.imgur.com/kSdv2a2.gif") # Executioner gif
                    exe_win_embed.set_footer(text="The game is over!")
                    await channel.send(embed=exe_win_embed)
                    get_game_ref(channel_id).delete()
                    return # Use return to exit the function and thus the loop

        # --- ALPHA WOLF CONVERSION CHECK ---
        if lynched_id:
            lynched_role = game_data.get("player_states", {}).get(lynched_id, {}).get("role")
            if lynched_role == Role.ALPHA_WOLF.value:
                day_votes = game_data.get("day_votes", {})
                # Find the last person who voted for the Alpha Wolf
                last_voter_id = None
                for voter, target in reversed(list(day_votes.items())):
                    if target == lynched_id:
                        last_voter_id = voter
                        break
                
                if last_voter_id:
                    # Convert the voter
                    game_ref = get_game_ref(channel_id)
                    game_ref.child('player_states').child(last_voter_id).child('role').set(Role.WEREWOLF.value)
                    
                    voter_name = game_data.get('players', {}).get(last_voter_id, {}).get('name', 'Someone')
                    lynch_embed.description += f"\nAs the Alpha Wolf is dragged away, they let out a final, terrifying howl. **{voter_name}** feels a dark change within them... they have become a Werewolf!"

                    # DM the newly converted player
                    new_wolf_member = bot.get_guild(game_data['guild_id']).get_member(int(last_voter_id))
                    if new_wolf_member:
                        try:
                            await new_wolf_member.send("🐺 The Alpha Wolf's curse has fallen upon you. You are now a Werewolf! Serve the pack.")
                        except discord.Forbidden:
                            pass

        lynch_embed = discord.Embed(title="⚖️ The Verdict is In! ⚖️", description=lynch_story, color=discord.Color.from_rgb(128, 128, 128))

        if lynched_id:
            # Refetch data to get the new role if conversion happened
            game_data = get_game_data(channel_id)
            if not game_data: break
            
            dead_ids, lover_story = await process_death(game_ref, lynched_id, game_data)
            if lover_story:
                lynch_embed.description += lover_story
        
        await channel.send(embed=lynch_embed)

        if lynched_id:
            # Refetch data after the death
            new_game_data = get_game_data(channel_id)
            if not new_game_data: break
            if await check_win_condition(bot, channel_id, new_game_data):
                break
        
        # --- Clear votes for next day ---
        get_game_ref(channel_id).child('day_votes').delete()

        if game_data.get("phase") == GamePhase.ENDED.value:
            break


async def start_night_phase(bot: commands.Bot, channel_id: int, game_data: dict):
    """Initiates the night phase and sends action prompts to roles."""
    channel = bot.get_channel(channel_id)
    game_ref = get_game_ref(channel_id)

    # Clear out actions from the previous night
    game_ref.child("night_actions").delete()

    night_num = game_data.get("game_state", {}).get("night_number", 0) + 1
    game_ref.child("game_state/night_number").set(night_num)

    embed = discord.Embed(
        title=f"🌙 Night {night_num} has fallen... 🌙",
        description="The moon is high in the sky. If you have a night action, I've sent you a DM. Sweet dreams... or nightmares?",
        color=discord.Color.dark_blue()
    )
    embed.set_image(url="https://i.imgur.com/vHj3mGz.gif")
    await channel.send(embed=embed)

    # This will now only send prompts for non-witch roles
    await send_early_night_prompts(bot, game_data)


async def start_day_phase(bot: commands.Bot, channel_id: int, game_data: dict):
    """Initiates the day phase, processes night actions, and announces events."""
    channel = bot.get_channel(channel_id)
    game_ref = get_game_ref(channel_id)
    night_num = game_data.get("game_state", {}).get("night_number", 0)
    
    # This is the new key part: processing the actions!
    story, deaths = await process_night_actions(bot, game_data)

    # Update the database for any players who died
    if deaths:
        for death in deaths:
            game_ref.child('player_states').child(death['id']).child('is_alive').set(False)

    embed = discord.Embed(
        title=f"☀️ Day {night_num} begins! ☀️",
        description=f"{story}\n\nIt's time to discuss! Who do you suspect? Use `/ww vote` when you're ready to cast a vote to lynch someone.",
        color=discord.Color.orange()
    )
    embed.set_image(url="https://i.imgur.com/w9emP2g.gif")
    
    # Add a list of who is still alive
    player_states = game_data.get("player_states", {})
    all_players = game_data.get("players", {})
    alive_player_mentions = [
        all_players[pid]['mention'] for pid, state in player_states.items() 
        if state['is_alive'] and pid not in [d['id'] for d in deaths]
    ]
    
    if alive_player_mentions:
        embed.add_field(name="Remaining Players", value="\n".join(alive_player_mentions), inline=False)
    else:
        embed.add_field(name="Remaining Players", value="No one is left...", inline=False)

    await channel.send(embed=embed)


async def check_win_condition(bot: commands.Bot, channel_id: int, game_data: dict) -> bool:
    """Checks if a win condition has been met and ends the game if so."""
    player_states = game_data.get("player_states", {})
    all_players_info = game_data.get("players", {})
    
    alive_werewolves = []
    alive_villagers = [] # Includes all non-werewolf roles
    alive_players = []

    for pid, state in player_states.items():
        if state.get("is_alive"):
            alive_players.append(pid)
            role_val = state.get("role")
            # Alpha Wolf is part of the werewolf faction
            if role_val in [Role.WEREWOLF.value, Role.ALPHA_WOLF.value, Role.SORCERER.value]:
                alive_werewolves.append(pid)
            else:
                alive_villagers.append(pid)

    winner = None
    win_description = ""
    win_color = discord.Color.gold()
    lovers = game_data.get("lovers", {})
    
    # --- Lovers Win Condition ---
    if len(alive_players) == 2 and alive_players[0] in lovers and lovers[alive_players[0]] == alive_players[1]:
        winner = "💘 The Lovers"
        win_description = "Against all odds, the two lovers are the last ones standing. A tragic but beautiful victory!"
        win_color = discord.Color.from_rgb(255, 182, 193) # Pink!
    # --- Arsonist Win Condition ---
    elif len(alive_players) == 1 and player_states[alive_players[0]]["role"] == Role.ARSONIST.value:
        winner = "🔥 The Arsonist"
        win_description = "The village is reduced to ash. The Arsonist stands alone, watching the world burn. A solitary, fiery victory."
        win_color = ROLE_COLORS[Role.ARSONIST]
    elif len(alive_werewolves) == 0:
        winner = "💖 The Village"
        win_description = "All werewolves have been eliminated! The village is safe once more, thanks to your efforts!"
        win_color = discord.Color.from_rgb(137, 207, 240) # Villager Blue
    elif len(alive_werewolves) >= len(alive_villagers):
        winner = "🐺 The Werewolves"
        win_description = "The werewolves have taken over the village! Darkness falls, and the howling begins..."
        win_color = discord.Color.from_rgb(255, 87, 87) # Werewolf Red
    
    if winner:
        channel = bot.get_channel(channel_id)
        embed = discord.Embed(
            title=f"🎉 Game Over! {winner} Won! 🎉",
            description=win_description,
            color=win_color
        )
        
        # Reveal all roles at the end
        roles_reveal_text = ""
        for pid, pdata in all_players_info.items():
            role = player_states.get(pid, {}).get("role", "Unknown")
            status = "💀" if not player_states.get(pid, {}).get("is_alive") else "😊"
            roles_reveal_text += f"{status} {pdata['mention']} was a **{role}**\n"
        
        embed.add_field(name="Final Roles", value=roles_reveal_text, inline=False)
        embed.set_footer(text="Thank you for playing, my dear! I hope you had fun!")
        
        await channel.send(embed=embed)
        
        # Clean up the game from the database
        get_game_ref(channel_id).delete()
        return True

    return False


async def _dm_seer_vision(bot: commands.Bot, seer_id: str, target_name: str, target_role: str, game_data: dict):
    """Sends a private message to the Seer with the result of their vision."""
    seer_member = bot.get_guild(game_data['guild_id']).get_member(int(seer_id))
    if not seer_member: return
    
    embed = discord.Embed(
        title="🌙 Your Midnight Vision 🌙",
        description=f"You focused your mystical energy on **{target_name}**...\nThe spirits whisper that their true role is **{target_role}**!",
        color=ROLE_COLORS[Role.SEER]
    )
    await seer_member.send(embed=embed)


async def _dm_sorcerer_vision(bot: commands.Bot, sorcerer_id: str, target_name: str, is_seer: bool, game_data: dict):
    """Sends a private message to the Sorcerer with the result of their scrying."""
    sorcerer_member = bot.get_guild(game_data['guild_id']).get_member(int(sorcerer_id))
    if not sorcerer_member: return
    
    if is_seer:
        description = f"You gaze into your crystal ball at **{target_name}**... Yes! The mystical energies confirm they are the **Seer**!"
    else:
        description = f"You scry upon **{target_name}**, but see nothing of interest. They are not the Seer."

    embed = discord.Embed(
        title="🔮 Your Dark Scrying 🔮",
        description=description,
        color=ROLE_COLORS[Role.SORCERER]
    )
    await sorcerer_member.send(embed=embed)


async def dm_lovers(bot: commands.Bot, game_data: dict):
    """Sends a DM to the two lovers to inform them of their bond."""
    lovers = game_data.get("lovers")
    if not lovers: return
    
    lover1_id, lover2_id = list(lovers.keys())
    
    p1_name = game_data["players"][lover1_id]["name"]
    p2_name = game_data["players"][lover2_id]["name"]

    p1_member = bot.get_guild(game_data['guild_id']).get_member(int(lover1_id))
    p2_member = bot.get_guild(game_data['guild_id']).get_member(int(lover2_id))

    embed = discord.Embed(title="💘 You have been struck by Cupid's Arrow! 💘", color=discord.Color.from_rgb(255, 182, 193))
    
    if p1_member:
        embed.description=f"You are secretly in love with **{p2_name}**. Your destiny is now linked to theirs. If one of you dies, the other will die of a broken heart. Your new goal is to be the last two standing."
        await p1_member.send(embed=embed)
    if p2_member:
        embed.description=f"You are secretly in love with **{p1_name}**. Your destiny is now linked to theirs. If one of you dies, the other will die of a broken heart. Your new goal is to be the last two standing."
        await p2_member.send(embed=embed)


async def process_death(game_ref, player_id: str, game_data: dict):
    """
    Processes a single player death, updates DB, and checks for lover chain-reactions.
    Returns a list of all players who died (original + lover) and a potential story part for the lover's death.
    """
    game_ref.child('player_states').child(player_id).child('is_alive').set(False)
    
    all_deaths = [player_id]
    lover_death_story = ""

    lovers = game_data.get("lovers", {})
    if player_id in lovers:
        lover_id = lovers[player_id]
        lover_state = game_data.get("player_states", {}).get(lover_id, {})
        if lover_state.get("is_alive"):
            game_ref.child('player_states').child(lover_id).child('is_alive').set(False)
            all_deaths.append(lover_id)
            lover_name = game_data["players"][lover_id]["name"]
            lover_death_story = f"\nUpon seeing their beloved's fate, **{lover_name}** also died of a broken heart! 💔"

    return all_deaths, lover_death_story


async def process_night_actions(bot: commands.Bot, game_data: dict):
    """Processes all actions from the night and returns a story and list of dead players."""
    game_ref = get_game_ref(game_data['channel_id'])
    night_actions = game_data.get('night_actions', {})
    player_states = game_data.get('player_states', {})
    players_info = game_data.get('players', {})

    werewolf_target_id = None
    doctor_save_id = None
    bodyguard_protector_id = None
    bodyguard_protected_id = None
    witch_saved = False
    witch_kill_id = None
    deaths = []
    story_parts = []
    visits = {} # Target_id -> [visitor_id_1, visitor_id_2]

    # --- Step 1: Compile all visits and immediate actions ---
    # We need to know who is visiting who before resolving anything.
    
    # Werewolf visit
    wolf_votes = night_actions.get('werewolf_vote', {})
    if wolf_votes:
        vote_counts = Counter(wolf_votes.values())
        max_votes = vote_counts.most_common(1)[0][1]
        tied_targets = [p_id for p_id, count in vote_counts.items() if count == max_votes]
        werewolf_target_id = random.choice(tied_targets)
        # All wolves are considered visitors to their target
        visits.setdefault(werewolf_target_id, []).extend(list(wolf_votes.keys()))

    # Doctor visit
    doctor_actions = night_actions.get('doctor_save', {})
    if doctor_actions:
        doctor_id = list(doctor_actions.keys())[0]
        doctor_save_id = list(doctor_actions.values())[0]
        visits.setdefault(doctor_save_id, []).append(doctor_id)

    # Bodyguard visit
    bodyguard_actions = night_actions.get('bodyguard_protect', {})
    if bodyguard_actions:
        bodyguard_protector_id = list(bodyguard_actions.keys())[0]
        bodyguard_protected_id = list(bodyguard_actions.values())[0]
        visits.setdefault(bodyguard_protected_id, []).append(bodyguard_protector_id)
        
    # Seer visit
    seer_picks = night_actions.get('seer_pick', {})
    for seer_id, target_id in seer_picks.items():
        visits.setdefault(target_id, []).append(seer_id)

    # Witch kill is also a visit
    witch_kill_action = night_actions.get('witch_kill')
    if witch_kill_action:
        witch_id = list(witch_kill_action.keys())[0]
        witch_kill_id = list(witch_kill_action.values())[0]
        visits.setdefault(witch_kill_id, []).append(witch_id)

    # Check for witch save
    if night_actions.get('witch_save') and werewolf_target_id:
        witch_saved = True


    # --- Step 2: Check for Veteran on Alert ---
    # This is high priority. If veteran shoots you, you're dead.
    alerting_vet_id = night_actions.get('veteran_alert')
    if alerting_vet_id:
        story_parts.append(f"**A paranoid Veteran, {players_info[alerting_vet_id]['name']}, was on alert tonight!**")
        visitors = visits.get(alerting_vet_id, [])
        if not visitors:
            story_parts.append("They nervously watched the door all night, but no one came.")
        else:
            for visitor_id in visitors:
                if visitor_id not in deaths:
                    story_parts.append(f"**{players_info[visitor_id]['name']}** was shot by the Veteran!")
                    newly_dead, lover_story = await process_death(game_ref, visitor_id, game_data)
                    deaths.extend(newly_dead)
                    if lover_story: story_parts.append(lover_story)
        
        # If a werewolf visited the vet, their main attack is cancelled
        if werewolf_target_id == alerting_vet_id:
            werewolf_target_id = None # Attack is nullified


    # --- Step 3: Resolve all other actions ---
    # Werewolf attack resolution
    if werewolf_target_id:
        target_name = players_info[werewolf_target_id]['name']
        if witch_saved:
            story_parts.append(f"The werewolves targeted **{target_name}**, but a powerful witch brewed a potion of life, saving them from the brink!")
        elif werewolf_target_id == doctor_save_id:
            story_parts.append(f"A terrible howl was heard near **{target_name}**'s house, but a skilled doctor intervened, miraculously saving them!")
        elif werewolf_target_id == bodyguard_protected_id:
            protector_name = players_info[bodyguard_protector_id]['name']
            story_parts.append(f"The werewolves descended upon **{target_name}**, but a brave bodyguard, **{protector_name}**, sacrificed themselves to save them! A true hero has fallen.")
            newly_dead, lover_story = await process_death(game_ref, bodyguard_protector_id, game_data)
            deaths.extend(newly_dead)
            if lover_story: story_parts.append(lover_story)
        else:
            story_parts.append(f"A blood-curdling scream pierced the night. The village awakens to find that **{target_name}** has been tragically killed by werewolves.")
            newly_dead, lover_story = await process_death(game_ref, werewolf_target_id, game_data)
            deaths.extend(newly_dead)
            if lover_story: story_parts.append(lover_story)

    # 5. Resolve Witch's kill potion
    if witch_kill_id and witch_kill_id not in deaths:
        killed_name = players_info[witch_kill_id]['name']
        # Mark potion as used
        game_ref.child('game_state/witch_potions/kill').set(False)
        if witch_kill_id == doctor_save_id:
            story_parts.append(f"The witch threw a deadly potion at **{killed_name}**, but the doctor was one step ahead, providing a miraculous antidote just in time!")
        else:
            story_parts.append(f"In the dead of night, the witch brewed a deadly concoction, and poor **{killed_name}** was found lifeless at dawn.")
            newly_dead, lover_story = await process_death(game_ref, witch_kill_id, game_data)
            deaths.extend(newly_dead)
            if lover_story: story_parts.append(lover_story)

    # 6. Douse targets
    arsonist_douse_action = night_actions.get('arsonist_douse')
    if arsonist_douse_action:
        doused_id = list(arsonist_douse_action.values())[0]
        game_ref.child('player_states').child(doused_id).child('is_doused').set(True)

    # 7. Ignite! This happens last and is the grand finale.
    if night_actions.get('arsonist_ignite'):
        doused_players = []
        player_states = get_game_data(channel_id).get('player_states', {}) # Refetch to include newly doused
        for pid, state in player_states.items():
            if state.get('is_doused') and state.get('is_alive') and pid not in deaths:
                doused_players.append(pid)
        
        if doused_players:
            story_parts.append("\n**A brilliant inferno engulfs the village! The Arsonist has revealed their fiery plot!**")
            for pid in doused_players:
                story_parts.append(f"**{players_info[pid]['name']}** was consumed by the flames!")
                newly_dead, lover_story = await process_death(game_ref, pid, game_data)
                deaths.extend(newly_dead)
                if lover_story: story_parts.append(lover_story)

    # 8. Process Seer visions (and send DMs)
    seer_picks = night_actions.get('seer_pick', {})
    for seer_id, target_id in seer_picks.items():
        # A dead seer gets no vision
        if seer_id in deaths: continue
        target_state = player_states.get(target_id, {})
        target_role = target_state.get('role', 'Unknown')
        target_name = players_info.get(target_id, {}).get('name', 'An unknown player')
        asyncio.create_task(_dm_seer_vision(bot, seer_id, target_name, target_role, game_data))

    # 9. Process Sorcerer scrying
    sorcerer_picks = night_actions.get('sorcerer_pick', {})
    for sorcerer_id, target_id in sorcerer_picks.items():
        if sorcerer_id in deaths: continue
        target_role = player_states.get(target_id, {}).get('role')
        is_seer = (target_role == Role.SEER.value)
        target_name = players_info.get(target_id, {}).get('name', 'An unknown player')
        asyncio.create_task(_dm_sorcerer_vision(bot, sorcerer_id, target_name, is_seer, game_data))

    # 10. Finalize story
    story = "\n".join(story_parts) if story_parts else "A new day dawns on the village... and to everyone's surprise, the night was peacefully quiet. No one died!"
        
    return story, deaths

async def process_lynch_votes(game_data: dict):
    """Tallies day votes and determines who is lynched."""
    day_votes = game_data.get('day_votes', {})
    players_info = game_data.get('players', {})
    player_states = game_data.get('player_states', {})
    
    if not day_votes:
        return "The day ends quietly. The village couldn't decide on a verdict, and no one is lynched.", None

    # Use a list to handle Mayor's double vote
    vote_list = []
    for voter_id, target_id in day_votes.items():
        vote_list.append(target_id)
        # If the voter is a revealed Mayor, add their vote again
        if player_states.get(voter_id, {}).get('is_mayor_revealed'):
            vote_list.append(target_id)

    vote_counts = Counter(vote_list)
    if not vote_counts: # handle case where vote_list might be empty
        return "Despite the discussion, no votes were cast. The day ends in a tense silence.", None

    max_votes = vote_counts.most_common(1)[0][1]
    
    # Check for a tie
    tied_targets = [p_id for p_id, count in vote_counts.items() if count == max_votes]
    
    if len(tied_targets) > 1:
        tied_names = [players_info[p_id]['name'] for p_id in tied_targets]
        return f"The vote is a tie between **{', '.join(tied_names)}**! The village is in chaos, and no one is lynched today.", None
    
    lynched_id = tied_targets[0]
    lynched_name = players_info[lynched_id]['name']
    
    story = f"The villagers have spoken! With a heavy heart, they lead **{lynched_name}** to the gallows. They have been lynched."
    return story, lynched_id