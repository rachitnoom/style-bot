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

---

## Offline Alerts via Uptime Monitor

The bot sends an **online** embed when it starts and an **offline** embed when it shuts down gracefully (SIGTERM).  
However, a crash or unresponsive process won't trigger the graceful shutdown path.  
To catch those cases, wire an external uptime monitor to the bot's `/health` endpoint and have it call a webhook on the **API Server** — a separate process that stays reachable even when the bot has crashed.

### How it works

```
External monitor  →  polls GET <bot-host>/health every N seconds
         │
         │  (non-200 or timeout detected)
         ▼
External monitor  →  POST <api-server-host>/api/alert/uptime
         │
         │  (API Server is a separate process — always up)
         ▼
API Server  →  Discord Incoming Webhook URL
         │
         ▼
Discord  →  🔴 offline embed appears in the alert channel
```

> **Why a separate process?**  
> Putting the webhook receiver inside the bot means it goes down with the bot.  
> The API Server (`artifacts/api-server`) runs independently on its own port and stays reachable during a bot crash or restart.

### Step 1 — Create a Discord Incoming Webhook

1. In Discord, open the **alert channel** → **Edit Channel** → **Integrations** → **Webhooks** → **New Webhook**.
2. Copy the **Webhook URL** — it looks like `https://discord.com/api/webhooks/<id>/<token>`.

### Step 2 — Set environment variables on the API Server

| Variable | Purpose |
|---|---|
| `DISCORD_ALERT_WEBHOOK_URL` | Discord Incoming Webhook URL from Step 1 |
| `UPTIME_WEBHOOK_SECRET` | *(Optional but recommended)* A shared secret to authenticate webhook calls |

### Step 3 — Configure UptimeRobot

1. Log in to [UptimeRobot](https://uptimerobot.com) and click **Add New Monitor**.
2. Choose **HTTP(s)** monitor type.
3. Set **URL** to the bot's health endpoint (the bot host, not the API server):
   ```
   https://<your-bot-railway-domain>/health
   ```
4. Set **Monitoring Interval** to **5 minutes** (free plan) or lower on paid plans.
5. Under **Alert Contacts**, click **Add Alert Contact → Webhook**:
   - **URL**: `https://<your-api-server-domain>/api/alert/uptime`  
     *(this is the API Server URL, not the bot URL)*
   - **POST Value (JSON)**:
     ```json
     {
       "monitor_name": "*monitorFriendlyName*",
       "monitor_url": "*monitorURL*",
       "alert_type": "*alertTypeFriendlyName*",
       "details": "*alertDetails*"
     }
     ```
     *(UptimeRobot replaces the `*placeholders*` automatically.)*
   - If you set `UPTIME_WEBHOOK_SECRET`, add a custom header:  
     `X-Webhook-Secret: <your-secret>`
6. Save both the alert contact and the monitor.

### Step 4 — Configure BetterUptime (alternative)

1. Log in to [BetterUptime](https://betteruptime.com) and create a monitor for:
   ```
   https://<your-bot-railway-domain>/health
   ```
2. In the monitor's **Integrations** tab, add a **Webhook** integration:
   - **URL**: `https://<your-api-server-domain>/api/alert/uptime`
   - **Method**: `POST`
   - **Payload**:
     ```json
     {
       "monitor_name": "{{ monitor.name }}",
       "monitor_url": "{{ monitor.url }}",
       "alert_type": "{{ event.cause }}",
       "details": "{{ event.description }}"
     }
     ```
   - Add header `X-Webhook-Secret: <your-secret>` if you set the env var.
3. Save the integration.

### Webhook endpoint reference

| Field | Value |
|---|---|
| Method | `POST` |
| Path | `/api/alert/uptime` (on the **API Server**, not the bot) |
| Content-Type | `application/json` |
| Auth header *(optional)* | `X-Webhook-Secret: <UPTIME_WEBHOOK_SECRET>` |

**Request body fields** (all optional):

| Key | Description |
|---|---|
| `alert_type` | `"down"` triggers a 🔴 offline embed; `"up"` / `"recovery"` triggers a 🟢 recovery embed |
| `monitor_name` | Friendly name shown in the embed |
| `monitor_url` | URL being monitored, shown in the embed |
| `details` | Additional context shown in the embed |

UptimeRobot's native keys (`alertType`, `alertTypeFriendlyName`, `monitorURL`, `monitorFriendlyName`, `alertDetails`) are also accepted directly.
