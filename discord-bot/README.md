# Style-Bot

A general-purpose Discord server bot:

- **Moderation** — `/mod kick`, `/mod ban`, `/mod timeout`, `/mod warn`, `/mod warnings`, `/mod clear`
- **Welcome / leave messages** — `/welcome channel`, `/welcome message` (supports `{mention}`, `{user}`, `{name}`, `{server}`, `{count}`)
- **Automod** — `/automod toggle` (banned words), `/automod anti_invite`, `/automod anti_mention_spam`
- **Custom commands** — `/customcommand add|remove|list`, triggered with a configurable prefix (default `!`)
- **Reaction roles** — `/reactionrole add` turns a reaction on any message into a role toggle
- **Queue** — `/queue panel`, `/queue setdisplay`, `/queue reset`
- **Support panel** — `/supportpanel panel` posts a 2-button help panel (call admin / request help)
- **Logging** — `/settings logchannel` sends moderation/automod actions to a channel
- **Presence tracking** — records member online/offline status to the database

## Local / Replit Setup

1. Create an application + bot at https://discord.com/developers/applications
2. Under **Bot**, enable **Server Members Intent**, **Message Content Intent**, and **Presence Intent** (all three are required).
3. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes, and permissions: Manage Roles, Kick Members, Ban Members, Moderate Members, Manage Messages, Send Messages, Read Message History. Use the generated URL to invite the bot to your server.
4. Set the `DISCORD_BOT_TOKEN` secret in this Replit project.
5. Start the **Discord Bot** workflow. Slash commands can take up to an hour to appear globally the first time.

## Data

All settings, warnings, custom commands, and reaction-role mappings are stored in the project's PostgreSQL database (see `db.py`).

---

## Deploying to Railway (always-on 24/7)

Railway keeps the bot running continuously, even when the Replit workspace is closed.

### Step 1 — Create a Railway project

1. Go to [railway.app](https://railway.app) and sign in.
2. Click **New Project → Deploy from GitHub repo** and select this repository.
3. Railway will detect the project automatically via Nixpacks.

### Step 2 — Set the Root Directory

In your Railway service settings, set **Root Directory** to `discord-bot`.
This tells Railway to install `requirements.txt` and run `bot.py` from the right folder.

### Step 3 — Set environment variables

In the Railway service's **Variables** tab, add the following:

| Variable | Where to get it |
|---|---|
| `DISCORD_BOT_TOKEN` | Discord Developer Portal → your app → **Bot** → Reset Token |
| `DATABASE_URL` | Your PostgreSQL connection string (e.g. from Replit DB, Supabase, Neon, or Railway's own Postgres plugin) |
| `SESSION_SECRET` | Any long random string (only needed if you run the API server alongside the bot) |

> **Tip:** Railway offers a free managed PostgreSQL plugin — click **New → Database → PostgreSQL** inside your project and Railway will inject `DATABASE_URL` automatically.

### Step 4 — Run database migrations

If this is the first deploy, you need to apply the schema.
The SQL migration files are in `discord-bot/migrations/`. Run them once against your production database (e.g. via `psql $DATABASE_URL -f migrations/001_presence_tables.sql`).

### Step 5 — Deploy

Railway deploys automatically on every push to your connected branch.
Check the **Logs** tab to confirm the bot logs `Logged in as ...` within a few seconds of deploy.

### Required Discord intents (reminder)

Make sure all three privileged intents are enabled in the Discord Developer Portal under **Bot → Privileged Gateway Intents**:

- ✅ Server Members Intent
- ✅ Message Content Intent
- ✅ Presence Intent
