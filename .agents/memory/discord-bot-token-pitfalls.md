---
name: Discord bot token pitfalls
description: Common failure modes when a user provides a Discord bot token, and how to spot invalid/leaked tokens quickly.
---

- A valid Discord bot token has 3 dot-separated segments (~59-72 chars total). If `os.environ['DISCORD_BOT_TOKEN']` has 0 dots and is ~32 chars, the user pasted the OAuth2 **Client Secret** instead of the Bot page's token — tell them to go to the Bot page (not OAuth2) and hit "Reset Token".
- `discord.errors.LoginFailure: Improper token has been passed` = malformed/wrong-value token (format issue). `PrivilegedIntentsRequired` = token is valid and login succeeded, but Server Members / Message Content intents aren't toggled on in the Developer Portal (Bot page → Privileged Gateway Intents) — a manual step only the user can do; no code fix possible.
- Users sometimes paste secret values directly into the chat message instead of the secure `requestSecrets` form, even after being asked to use the form. Treat any token/secret typed in chat as leaked: don't use it, ask the user to rotate/reset it via the provider's dashboard, and re-request through the secure form only.
