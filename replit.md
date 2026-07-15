# Style-Bot — Discord Server Bot

A general-purpose Discord server bot (in the spirit of MEE6) providing moderation, leveling/XP, welcome messages, automod, custom commands, and reaction roles. No music playback (intentionally excluded — see `discord-bot/README.md`).

## Run & Operate

- Workflow `Discord Bot` runs `cd discord-bot && python bot.py`
- Required secret: `DISCORD_BOT_TOKEN` — Discord bot token from the Developer Portal (Bot page, not OAuth2/Client Secret)
- Required: **Server Members Intent** and **Message Content Intent** must be enabled in the Discord Developer Portal (Bot page → Privileged Gateway Intents) or the bot fails to connect
- Uses the project's shared Postgres database (`DATABASE_URL`) via `asyncpg` — tables: `guild_settings`, `levels`, `level_roles`, `custom_commands`, `reaction_roles`, `warnings`
- See `discord-bot/README.md` for full setup (OAuth invite scopes/permissions, slash-command sync delay, etc.)

## Stack

- Python 3.12, py-cord (Discord API), asyncpg (Postgres), python-dotenv, Pillow, requests, aiohttp
- Standalone `discord-bot/` directory at the workspace root — NOT part of the pnpm workspace/artifacts system (this is a backend bot, not a web/mobile artifact)
- Shares the same Postgres database as the rest of the project

## Where things live

- `discord-bot/bot.py` — entry point, loads all cogs, starts the bot
- `discord-bot/db.py` — asyncpg pool + CRUD helpers for all tables
- `discord-bot/utils.py` — shared embed helpers, template rendering, XP curve, permission checks
- `discord-bot/cogs/` — one cog per feature area: `moderation.py`, `automod.py`, `leveling.py`, `welcome.py`, `customcommands.py`, `reactionroles.py`, `settings.py`

## Architecture decisions

- Python bot lives outside `artifacts/` since it doesn't fit the web/mobile/slides artifact model — it's a standalone backend process bound to a workflow, not a previewable artifact.
- Music playback was explicitly excluded (ffmpeg/voice complexity + YouTube ToS risk).
- Uses the project's existing shared Postgres instance rather than a separate DB service.

## Product

Server admins can: moderate members (kick/ban/timeout/warn/purge), run a leveling system with XP and level-based role rewards, send templated welcome/leave messages, auto-filter banned words/invite links/mention spam, define custom text commands with a configurable prefix, and set up reaction-role menus.

## User preferences

- Respond to this user in Thai.
- When requesting secrets (like bot tokens), always use the secure secret request form — never accept a secret value pasted directly into chat. If the user pastes one in chat anyway, treat it as leaked, do not use it, and ask them to reset/rotate it before providing it again through the form.

## Gotchas

- The bot will not start without `DISCORD_BOT_TOKEN` set, and will fail with `PrivilegedIntentsRequired` unless Server Members + Message Content intents are enabled in the Developer Portal — both are manual steps only the user can do.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details (applies to the `artifacts/` side of the project, not `discord-bot/`)
