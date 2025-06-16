# WereWolfBot

A Discord bot for playing the classic party game Werewolf (also known as Mafia), with a cute anime theme. This bot manages the entire game flow, from role assignment to night actions and voting, allowing players to focus on deduction and deception.

## Features

- **Full Game Automation:** The bot handles game creation, player management, role distribution, night/day cycles, and win condition checking.
- **Variety of Roles:** A wide range of special roles to make each game unique and exciting.
    - **Village Team:** Villager, Seer, Doctor, Witch, Hunter, Cupid, Bodyguard, Mayor, Veteran.
    - **Werewolf Team:** Werewolf, Alpha Wolf, Sorcerer.
    - **Neutral Roles:** Jester, Executioner, Arsonist.
- **Interactive Gameplay:** Uses Discord's latest features like slash commands and buttons for a smooth user experience.
- **DM-based Role Information:** Players receive their roles and night action prompts via direct messages to maintain secrecy.
- **Customizable Games:** The game creator can enable or disable specific roles for a customized game experience.
- **Persistent Games:** The bot uses Firebase Realtime Database to store game state, allowing games to survive bot restarts.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/WerewolfBot.git
    cd WerewolfBot
    ```

2.  **Install dependencies:**
    Make sure you have Python 3.8+ installed.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up Firebase:**
    - Create a new project on the [Firebase Console](https://console.firebase.google.com/).
    - Go to your project's settings, select the "Service accounts" tab, and generate a new private key. This will download a JSON file.
    - Rename the downloaded JSON file to `firebase-creds.json` and place it in the root directory of the project.
    - In the Firebase Console, go to "Realtime Database" and create a new database.
    - In the "Rules" tab of your Realtime Database, set the rules to allow read and write access. For development, you can set them to:
      ```json
      {
        "rules": {
          ".read": "true",
          ".write": "true"
        }
      }
      ```
      **Note:** These rules are not secure and should not be used in a production environment.

4.  **Configure environment variables:**
    Create a `.env` file in the root directory and add the following variables:
    ```
    DISCORD_BOT_TOKEN=your_discord_bot_token
    FIREBASE_DATABASE_URL=your_firebase_database_url
    ```
    - `DISCORD_BOT_TOKEN`: Your Discord bot's token. You can get this from the [Discord Developer Portal](https://discord.com/developers/applications).
    - `FIREBASE_DATABASE_URL`: The URL of your Firebase Realtime Database.

## Usage

The bot primarily uses slash commands under the `ww` group.

### Game Management

-   `/ww create`: Creates a new Werewolf game lobby in the current channel.
-   `/ww join`: Joins the game lobby in the current channel.
-   `/ww start`: Starts the game. Only the person who created the game can use this command.
-   `/ww end`: Ends the current game. Requires "Manage Channels" permission.

### Game Actions

-   `/ww vote`: Vote to lynch a player during the day.
-   `/ww reveal`: If you are the Mayor, use this to reveal your role. Your vote will count as two afterwards.

### Game Settings

-   `/ww settings`: Adjust the game settings before it starts. The game creator can enable/disable roles.

## How to Play

1.  A user with "Manage Channels" permission invites the bot to the server.
2.  In the channel where you want to play, someone starts a lobby with `/ww create`.
3.  Other players join the game using `/ww join`.
4.  The creator can adjust the roles available in the game with `/ww settings`.
5.  Once enough players have joined, the creator starts the game with `/ww start`.
6.  Players receive their roles via DM.
7.  The game proceeds in Night and Day phases.
8.  During the Night, players with night actions will receive prompts in their DMs.
9.  During the Day, players discuss and then vote to lynch someone using `/ww vote`.
10. The game ends when a win condition is met (e.g., all werewolves are eliminated, or werewolves equal or outnumber villagers).

## Contributing

Contributions are welcome! If you have any ideas, suggestions, or bug reports, please open an issue or create a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details. 