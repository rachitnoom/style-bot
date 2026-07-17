"""Subprocess helper — run directly by test_bot_resilience.py.

Imports discord-bot/bot.py with all external dependencies mocked, then calls
``bot.main()`` with ``bot.start()`` rigged to raise a RuntimeError, simulating
an unhandled crash in the Discord connection loop.

Expected result: the process exits with a non-zero code, which is what
Railway's ``restartPolicyType = "on_failure"`` requires to trigger a restart.
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# ── Ensure discord-bot/ is importable regardless of cwd ──────────────────────
_bot_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if _bot_dir not in sys.path:
    sys.path.insert(0, _bot_dir)

# ── Provide a fake token so main() doesn't abort early ───────────────────────
os.environ["DISCORD_BOT_TOKEN"] = "fake.token.for.testing"

# ── Mock discord ──────────────────────────────────────────────────────────────
_mock_discord = MagicMock()
_mock_discord.Intents.default.return_value = MagicMock()
_mock_discord.Color.green.return_value = MagicMock()
_mock_discord.Color.orange.return_value = MagicMock()
_mock_discord.NotFound = Exception
_mock_discord.Forbidden = Exception

_mock_bot_obj = MagicMock()
_mock_bot_obj.guilds = []
_mock_bot_obj.is_closed.return_value = False
_mock_bot_obj.load_extension = MagicMock()
_mock_bot_obj.get_channel.return_value = None
# bot.start() raises — this is the simulated crash
_mock_bot_obj.start = AsyncMock(side_effect=RuntimeError("Simulated Discord connection crash"))
# async-context-manager protocol: __aexit__ must return falsy so the
# exception is NOT suppressed and propagates out of `async with bot:`.
_mock_bot_obj.__aenter__ = AsyncMock(return_value=_mock_bot_obj)
_mock_bot_obj.__aexit__ = AsyncMock(return_value=False)
_mock_discord.Bot.return_value = _mock_bot_obj

# ── Mock db ───────────────────────────────────────────────────────────────────
_mock_db = MagicMock()
_mock_db.init_pool = AsyncMock()
_mock_db.run_migrations = AsyncMock()
_mock_db.get_all_alert_channels = AsyncMock(return_value=[])

# ── Stub cog modules before bot.py loads them ─────────────────────────────────
for _cog in [
    "cogs",
    "cogs.moderation",
    "cogs.automod",
    "cogs.welcome",
    "cogs.customcommands",
    "cogs.reactionroles",
    "cogs.queue",
    "cogs.supportpanel",
    "cogs.settings",
    "cogs.presence",
    "cogs.alerts",
]:
    sys.modules[_cog] = MagicMock()

sys.modules["discord"] = _mock_discord
sys.modules["db"] = _mock_db
sys.modules["dotenv"] = MagicMock()

# ── Import bot and override the module-level bot instance ────────────────────
import bot as bot_module  # noqa: E402  (imports after sys.modules patches)

bot_module.bot = _mock_bot_obj

# Run main() — bot.start() raises, the exception propagates through
# asyncio.run(_runner()), and Python exits with code 1.
bot_module.main()
