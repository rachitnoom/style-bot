"""Tests for the on_ready reconnect-suppression cooldown in cogs/alerts.py.

Scenarios covered
-----------------
1. First on_ready: embed is sent and _last_online_alert is recorded.
2. Rapid reconnect (within cooldown window): embed is suppressed and the
   suppression is logged at INFO level.
3. Reconnect after cooldown expires: embed is sent again.
4. ONLINE_ALERT_COOLDOWN_SECONDS default value is sensible (>= 30 s).
"""

import logging
import pathlib
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_DISCORD_BOT_DIR = pathlib.Path(__file__).parent.parent  # discord-bot/


def _load_alerts_module():
    """Import cogs/alerts.py with all external dependencies mocked.

    ``commands.Cog`` is replaced with a real Python class so that
    ``Alerts.__init__`` runs correctly and ``on_ready`` is an actual
    coroutine rather than a MagicMock attribute.
    """
    mock_discord = MagicMock()
    mock_discord.HTTPException = Exception  # so except clauses work

    mock_db = MagicMock()
    mock_db.get_all_alert_channels = AsyncMock(return_value=[])

    mock_utils = MagicMock()

    # A real base class so Alerts can inherit from it properly.
    class _FakeCog:
        """Minimal stand-in for discord.ext.commands.Cog."""

        def __init__(self, *args, **kwargs):
            pass  # don't call super(MagicMock)

        @staticmethod
        def listener():
            """Decorator that returns the original coroutine unchanged."""
            def _decorator(f):
                return f
            return _decorator

    mock_ext_commands = MagicMock()
    mock_ext_commands.Cog = _FakeCog

    # Wire discord.ext.commands onto the discord.ext mock so that
    # ``from discord.ext import commands`` in alerts.py picks up our stub.
    mock_ext = MagicMock()
    mock_ext.commands = mock_ext_commands

    overrides = {
        "discord": mock_discord,
        "discord.ext": mock_ext,
        "discord.ext.commands": mock_ext_commands,
        "db": mock_db,
        "utils": mock_utils,
    }

    with patch.dict("sys.modules", overrides):
        sys.modules.pop("cogs.alerts", None)
        sys.path.insert(0, str(_DISCORD_BOT_DIR))
        import cogs.alerts as alerts_module
        return alerts_module, mock_discord, mock_db


# ---------------------------------------------------------------------------
# Test 1 — first on_ready sends the embed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_on_ready_sends_embed():
    """The very first on_ready call sends the online embed and records the time."""
    alerts_module, mock_discord, mock_db = _load_alerts_module()

    mock_channel = MagicMock()
    mock_channel.send = AsyncMock()

    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = mock_channel

    mock_db.get_all_alert_channels = AsyncMock(
        return_value=[{"alert_channel_id": 123}]
    )

    cog = alerts_module.Alerts(mock_bot)
    assert cog._last_online_alert is None, "Timestamp should start as None"

    await cog.on_ready()

    mock_channel.send.assert_awaited_once()
    assert cog._last_online_alert is not None, (
        "_last_online_alert should be set after the first on_ready"
    )


# ---------------------------------------------------------------------------
# Test 2 — rapid reconnect within cooldown is suppressed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rapid_reconnect_suppresses_duplicate_embed(caplog):
    """A second on_ready within the cooldown window suppresses the embed.

    The suppression must be logged at INFO so operators can see it.
    """
    alerts_module, mock_discord, mock_db = _load_alerts_module()

    mock_channel = MagicMock()
    mock_channel.send = AsyncMock()

    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = mock_channel

    mock_db.get_all_alert_channels = AsyncMock(
        return_value=[{"alert_channel_id": 456}]
    )

    cog = alerts_module.Alerts(mock_bot)

    # Simulate: last alert sent just 5 seconds ago (well within cooldown).
    cog._last_online_alert = time.monotonic() - 5

    with caplog.at_level(logging.INFO, logger="cogs.alerts"):
        await cog.on_ready()

    # The embed must NOT have been sent.
    mock_channel.send.assert_not_called()

    # Suppression must be logged.
    assert "suppressing duplicate embed" in caplog.text.lower() or \
           "suppressing" in caplog.text.lower(), (
        f"Expected a suppression log entry, got:\n{caplog.text}"
    )


# ---------------------------------------------------------------------------
# Test 3 — reconnect after cooldown expires sends the embed again
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reconnect_after_cooldown_sends_embed():
    """An on_ready that fires after the cooldown has expired sends the embed."""
    alerts_module, mock_discord, mock_db = _load_alerts_module()

    mock_channel = MagicMock()
    mock_channel.send = AsyncMock()

    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = mock_channel

    mock_db.get_all_alert_channels = AsyncMock(
        return_value=[{"alert_channel_id": 789}]
    )

    cog = alerts_module.Alerts(mock_bot)

    # Simulate: last alert sent longer ago than the full cooldown.
    past = time.monotonic() - (alerts_module.ONLINE_ALERT_COOLDOWN_SECONDS + 1)
    cog._last_online_alert = past

    await cog.on_ready()

    mock_channel.send.assert_awaited_once()
    # Timestamp must be refreshed.
    assert cog._last_online_alert > past, (
        "_last_online_alert should be updated to the current time"
    )


# ---------------------------------------------------------------------------
# Test 4 — cooldown constant is sensible
# ---------------------------------------------------------------------------

def test_cooldown_constant_is_sensible():
    """ONLINE_ALERT_COOLDOWN_SECONDS should be at least 30 seconds."""
    alerts_module, _, _ = _load_alerts_module()
    assert alerts_module.ONLINE_ALERT_COOLDOWN_SECONDS >= 30, (
        f"Cooldown is too short ({alerts_module.ONLINE_ALERT_COOLDOWN_SECONDS} s); "
        "it should be at least 30 s to cover brief network blips."
    )


# ---------------------------------------------------------------------------
# Test 5 — send failures don't corrupt the cooldown timestamp
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_failure_still_records_timestamp():
    """Even if channel.send raises HTTPException the timestamp is still set.

    This prevents an infinite retry storm if a channel is persistently broken.
    """
    alerts_module, mock_discord, mock_db = _load_alerts_module()

    mock_channel = MagicMock()
    mock_channel.send = AsyncMock(side_effect=mock_discord.HTTPException)

    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = mock_channel

    mock_db.get_all_alert_channels = AsyncMock(
        return_value=[{"alert_channel_id": 111}]
    )

    cog = alerts_module.Alerts(mock_bot)
    assert cog._last_online_alert is None

    # Must not raise, and timestamp must be set.
    await cog.on_ready()

    assert cog._last_online_alert is not None, (
        "_last_online_alert must be set even when channel.send raises"
    )
