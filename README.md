# Croco bot

A little game inside a Discord bot I made:

You need to explain the shown word to other people in chat
without saying the word itself or any similar words.

[Click to invite Drafts Croco to your own server](https://discord.com/oauth2/authorize?client_id=1220419189593084044)

> [!WARNING]
> This bot may not always be online. Depends on my mood and lunar energy affecting my server's workability.


## Installation

- Clone the repo
- Put your bot token inside a `.env` file as `BOT_TOKEN`
- Put your Discord User ID in the admin list in the `config.py` file
- Launch main.py, should work flawlessly

> [!WARNING]
> You need to have Message Content Intent enabled in your
> Discord Dev bot page.

> [!NOTE]
> Use `c!sync` to sync the slash command tree (only available to bot admins)


## How to play

Use `/start` or `c!start` to begin a game in chat.

The one who entered the command needs to explain a word shown to him in chat.
If the word is hard to explain, you may skip this word at no penalty.

The one who guesses the word gets some XP in reward. The explainer also gets the same amount of XP (and moonrocks if the word is long enough). The amount of XP given corresponds to the amount of symbols in the word.

Other players can vote on the explanation. For each like the explainer gets 1 XP. Dislikes is just a number on the other hand and doesn't take away anything, except for the number in the stats.


## Todo-list

- [x] Basic balance and stats
- [x] Server leaderboard of guesses
- [x] Transferring moonrocks
- [x] Ability to skip your turn
- [x] Text/slash commands for skipping the turn or changing the word 
- [ ] Shop with XP boosts
- [ ] ~~Global leaderboard of XP~~ hella cheaters out there
- [ ] Server settings (e.g. changing word list language)


## Use your own word list

To use your own word list in the bot:

- Place your word list in the `lang/` directory
  - The list must have words separated by newlines
- Go to `data.json` and add your own language
  - Specify a name, an emoji and a filename of your word list
- Relaunch the bot

> You can also change the default word list in the `data.json` file.