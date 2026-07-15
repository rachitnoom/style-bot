# Style-Bot

A general-purpose Discord server bot, similar in spirit to MEE6:

- **Moderation** — `/mod kick`, `/mod ban`, `/mod timeout`, `/mod warn`, `/mod warnings`, `/mod clear`
- **Leveling / XP** — members earn XP per message; `/level rank`, `/level leaderboard`, `/level setrole` (auto-assign a role at a given level)
- **Welcome / leave messages** — `/welcome channel`, `/welcome message` (supports `{mention}`, `{user}`, `{name}`, `{server}`, `{count}`)
- **Automod** — `/automod toggle` (banned words), `/automod anti_invite`, `/automod anti_mention_spam`
- **Custom commands** — `/customcommand add|remove|list`, triggered with a configurable prefix (default `!`)
- **Reaction roles** — `/reactionrole add` turns a reaction on any message into a role toggle
- **Logging** — `/settings logchannel` sends moderation/automod actions to a channel

Not included: music playback (requires voice/ffmpeg infrastructure and is legally risky due to YouTube ToS — most MEE6-style bots have dropped it too).

## Setup

1. Create an application + bot at https://discord.com/developers/applications
2. Under **Bot**, enable **Server Members Intent** and **Message Content Intent** (both are required — the bot will fail to start without them).
3. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes, and permissions: Manage Roles, Kick Members, Ban Members, Moderate Members, Manage Messages, Send Messages, Read Message History. Use the generated URL to invite the bot to your server.
4. Set the `DISCORD_BOT_TOKEN` secret (from the Bot page's "Reset Token" button) in this Replit project.
5. Start the bot workflow. Slash commands can take up to an hour to appear globally the first time (Discord's syncing), though they're usually instant per-server.

## Data

All settings, XP, warnings, custom commands, and reaction-role mappings are stored in the project's Postgres database (see `db.py`).
