"""Unit tests for send_startup_alert() in bot.py.

Covered scenarios
-----------------
1. First start  — sentinel absent  → green embed, sentinel created.
2. Restart      — sentinel present → orange embed, sentinel updated.
3. ALERT_CHANNEL_ID missing        → silent skip, no Discord call.
4. ALERT_CHANNEL_ID invalid        → warning logged, no crash.
5. Channel not found (NotFound)    → warning logged, no crash.
6. No access to channel (Forbidden on fetch) → warning logged, no crash.
7. Missing send-message permission → warning logged, no crash.

All tests run without a live Discord token by mocking every external dep.
"""

import os
import pathlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch, call
import pytest

# ── Module loader ──────────────────────────────────────────────────────────────

_DISCORD_BOT_DIR = pathlib.Path(__file__).parent.parent  # discord-bot/


def _load_bot_module():
    """Import bot.py with all external deps mocked; return the module."""
    import importlib

    # Distinct exception classes so isinstance() checks in bot.py work.
    class _NotFound(Exception):
        pass

    class _Forbidden(Exception):
        pass

    class _Color:
        @staticmethod
        def green():
            return "green"

        @staticmethod
        def orange():
            return "orange"

    class _Embed:
        """Minimal discord.Embed stand-in that records the kwargs it received."""

        def __init__(self, **kwargs):
            self._data = kwargs
            self.fields = []
            self.footer = None

        def add_field(self, **kwargs):
            self.fields.append(kwargs)

        def set_footer(self, **kwargs):
            self.footer = kwargs

    mock_discord = MagicMock()
    mock_discord.Intents.default.return_value = MagicMock()
    mock_discord.NotFound = _NotFound
    mock_discord.Forbidden = _Forbidden
    mock_discord.Color = _Color
    mock_discord.Embed = _Embed

    mock_db = MagicMock()
    mock_db.init_pool = AsyncMock()
    mock_db.run_migrations = AsyncMock()
    mock_db.get_all_alert_channels = AsyncMock(return_value=[])

    cog_stubs = {
        cog: MagicMock()
        for cog in [
            "cogs", "cogs.moderation", "cogs.automod", "cogs.welcome",
            "cogs.customcommands", "cogs.reactionroles", "cogs.queue",
            "cogs.supportpanel", "cogs.settings", "cogs.presence", "cogs.alerts",
        ]
    }

    overrides = {
        "discord": mock_discord,
        "discord.ext": MagicMock(),
        "discord.ext.commands": MagicMock(),
        "db": mock_db,
        "dotenv": MagicMock(),
        **cog_stubs,
    }

    with patch.dict("sys.modules", overrides):
        sys.modules.pop("bot", None)
        sys.path.insert(0, str(_DISCORD_BOT_DIR))
        import bot as bot_module
        return bot_module, mock_discord


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_bot_mock(*, guilds=("guild1",), user_id=12345):
    m = MagicMock()
    m.guilds = list(guilds)
    m.user = MagicMock()
    m.user.id = user_id
    return m


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_first_start_sends_green_embed(tmp_path):
    """No sentinel → 'First start' embed (green) is sent and sentinel is created."""
    bot_module, mock_discord = _load_bot_module()

    sentinel = tmp_path / ".style_bot_started"
    bot_module._SENTINEL_FILE = sentinel

    channel = MagicMock()
    channel.send = AsyncMock()

    mock_bot = _make_bot_mock()
    mock_bot.get_channel.return_value = channel
    bot_module.bot = mock_bot

    with patch.dict(os.environ, {"ALERT_CHANNEL_ID": "111222333"}):
        await bot_module.send_startup_alert()

    channel.send.assert_awaited_once()
    embed_arg = channel.send.call_args.kwargs.get("embed") or channel.send.call_args.args[0]

    # Green color for first start.
    assert embed_arg._data.get("color") == "green"
    # Description mentions "First start".
    assert "First start" in embed_arg._data.get("description", "")
    # Sentinel must now exist.
    assert sentinel.exists()


@pytest.mark.asyncio
async def test_restart_sends_orange_embed(tmp_path):
    """Sentinel present → 'Restart' embed (orange) is sent and sentinel is updated."""
    bot_module, mock_discord = _load_bot_module()

    sentinel = tmp_path / ".style_bot_started"
    sentinel.write_text("2026-01-01T00:00:00+00:00")  # pre-existing sentinel
    bot_module._SENTINEL_FILE = sentinel

    channel = MagicMock()
    channel.send = AsyncMock()

    mock_bot = _make_bot_mock()
    mock_bot.get_channel.return_value = channel
    bot_module.bot = mock_bot

    with patch.dict(os.environ, {"ALERT_CHANNEL_ID": "111222333"}):
        await bot_module.send_startup_alert()

    channel.send.assert_awaited_once()
    embed_arg = channel.send.call_args.kwargs.get("embed") or channel.send.call_args.args[0]

    # Orange color for restart.
    assert embed_arg._data.get("color") == "orange"
    # Description mentions "Restart".
    assert "Restart" in embed_arg._data.get("description", "")
    # Sentinel is still there (updated).
    assert sentinel.exists()


@pytest.mark.asyncio
async def test_missing_alert_channel_id_skips_silently(tmp_path):
    """No ALERT_CHANNEL_ID set → function returns without touching Discord."""
    bot_module, mock_discord = _load_bot_module()
    bot_module._SENTINEL_FILE = tmp_path / ".style_bot_started"

    mock_bot = _make_bot_mock()
    bot_module.bot = mock_bot

    env = {k: v for k, v in os.environ.items() if k != "ALERT_CHANNEL_ID"}
    with patch.dict(os.environ, env, clear=True):
        await bot_module.send_startup_alert()

    mock_bot.get_channel.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_alert_channel_id_logs_warning_no_crash(tmp_path):
    """Non-integer ALERT_CHANNEL_ID → warning logged, no exception raised."""
    bot_module, mock_discord = _load_bot_module()
    bot_module._SENTINEL_FILE = tmp_path / ".style_bot_started"

    mock_bot = _make_bot_mock()
    bot_module.bot = mock_bot

    with patch.dict(os.environ, {"ALERT_CHANNEL_ID": "not-a-number"}):
        # Must not raise.
        await bot_module.send_startup_alert()

    mock_bot.get_channel.assert_not_called()


@pytest.mark.asyncio
async def test_channel_not_found_logs_warning_no_crash(tmp_path):
    """discord.NotFound on fetch_channel → warning logged, no exception raised."""
    bot_module, mock_discord = _load_bot_module()
    bot_module._SENTINEL_FILE = tmp_path / ".style_bot_started"

    # get_channel returns None, fetch_channel raises NotFound.
    mock_bot = _make_bot_mock()
    mock_bot.get_channel.return_value = None
    mock_bot.fetch_channel = AsyncMock(side_effect=mock_discord.NotFound)
    bot_module.bot = mock_bot

    with patch.dict(os.environ, {"ALERT_CHANNEL_ID": "999888777"}):
        await bot_module.send_startup_alert()

    # send was never called.
    mock_bot.fetch_channel.assert_awaited_once_with(999888777)


@pytest.mark.asyncio
async def test_forbidden_fetch_logs_warning_no_crash(tmp_path):
    """discord.Forbidden on fetch_channel → warning logged, no exception raised."""
    bot_module, mock_discord = _load_bot_module()
    bot_module._SENTINEL_FILE = tmp_path / ".style_bot_started"

    mock_bot = _make_bot_mock()
    mock_bot.get_channel.return_value = None
    mock_bot.fetch_channel = AsyncMock(side_effect=mock_discord.Forbidden)
    bot_module.bot = mock_bot

    with patch.dict(os.environ, {"ALERT_CHANNEL_ID": "999888777"}):
        await bot_module.send_startup_alert()

    mock_bot.fetch_channel.assert_awaited_once_with(999888777)


@pytest.mark.asyncio
async def test_missing_send_permission_logs_warning_no_crash(tmp_path):
    """discord.Forbidden on channel.send → warning logged, no exception raised."""
    bot_module, mock_discord = _load_bot_module()
    bot_module._SENTINEL_FILE = tmp_path / ".style_bot_started"

    channel = MagicMock()
    channel.send = AsyncMock(side_effect=mock_discord.Forbidden)

    mock_bot = _make_bot_mock()
    mock_bot.get_channel.return_value = channel
    bot_module.bot = mock_bot

    with patch.dict(os.environ, {"ALERT_CHANNEL_ID": "111222333"}):
        await bot_module.send_startup_alert()

    channel.send.assert_awaited_once()
