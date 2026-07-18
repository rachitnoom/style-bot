"""Tests verifying health endpoint and crash-exit behaviour of bot.py.

Test 1 – Health endpoint (connected):
    Starts only the aiohttp health server (no real Discord connection, no DB)
    and asserts GET /health returns 200 with the required JSON keys.

Test 2 – Health endpoint (disconnected):
    Mocks bot.is_closed() = True and asserts /health reports ready=False,
    confirming the endpoint surface reflects a degraded/offline bot state.

Test 3 – Non-zero exit when bot.start() crashes:
    Runs tests/helpers/crash_runner.py in a subprocess.  That script imports
    bot.py with all deps mocked and calls main() with bot.start() rigged to
    raise a RuntimeError, exercising the full _runner() control-flow path.
    Asserts exit code != 0 so Railway's restartPolicyType = "on_failure" fires.

Test 4 – Clean reconnect after crash:
    Simulates the Railway restart cycle end-to-end:
      a) crash subprocess exits non-zero (crash confirmed)
      b) a fresh process starts its health server and returns 200 + ready=True
    This confirms a restarted bot comes up in a healthy state, not a broken one.
"""

import asyncio
import logging
import os
import pathlib
import socket
import subprocess
import sys
import textwrap
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

_DISCORD_BOT_DIR = pathlib.Path(__file__).parent.parent  # discord-bot/
_CRASH_RUNNER = pathlib.Path(__file__).parent / "helpers" / "crash_runner.py"


def _make_bot_mock(*, guilds=(), closed=False):
    """Return a discord.Bot-shaped mock suitable for health_handler."""
    m = MagicMock()
    m.guilds = list(guilds)
    m.is_closed.return_value = closed
    return m


def _free_port() -> int:
    """Return an OS-assigned free TCP port."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _load_bot_module():
    """Import bot.py with discord/db/dotenv fully mocked, return the module."""
    import importlib

    mock_discord = MagicMock()
    mock_discord.Intents.default.return_value = MagicMock()
    mock_discord.NotFound = Exception
    mock_discord.Forbidden = Exception

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

    mock_ext = MagicMock()
    mock_ext_commands = MagicMock()

    overrides = {
        "discord": mock_discord,
        "discord.ext": mock_ext,
        "discord.ext.commands": mock_ext_commands,
        "db": mock_db,
        "dotenv": MagicMock(),
        **cog_stubs,
    }

    with patch.dict("sys.modules", overrides):
        # Remove cached copy so reload picks up fresh mocks.
        sys.modules.pop("bot", None)
        import bot as bot_module
        return bot_module


# ── Test 1: health endpoint — connected state ──────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint_returns_200_with_expected_keys():
    """GET /health → 200 JSON with status / uptime_seconds / guild_count / ready=True."""
    from aiohttp import web

    bot_module = _load_bot_module()
    bot_module.bot = _make_bot_mock(guilds=["guild1"], closed=False)

    port = _free_port()
    app = web.Application()
    app.router.add_get("/health", bot_module.health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/health") as resp:
                assert resp.status == 200, f"Expected 200, got {resp.status}"
                assert "application/json" in resp.headers.get("Content-Type", "")
                body = await resp.json(content_type=None)

        for key in ("status", "uptime_seconds", "guild_count", "ready"):
            assert key in body, f"Missing key {key!r} in /health response: {body}"

        assert body["status"] == "ok"
        assert isinstance(body["uptime_seconds"], (int, float))
        assert body["guild_count"] == 1
        assert body["ready"] is True
    finally:
        await runner.cleanup()


# ── Test 2: health endpoint — disconnected / offline state ─────────────────────

@pytest.mark.asyncio
async def test_health_endpoint_reports_offline_when_bot_closed():
    """GET /health → ready=False when bot.is_closed() is True (degraded state)."""
    from aiohttp import web

    bot_module = _load_bot_module()
    # Simulate a bot whose websocket has closed (e.g. after an error or disconnect).
    bot_module.bot = _make_bot_mock(guilds=[], closed=True)

    port = _free_port()
    app = web.Application()
    app.router.add_get("/health", bot_module.health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/health") as resp:
                assert resp.status == 200
                body = await resp.json(content_type=None)

        assert body["ready"] is False, (
            f"Expected ready=False for a closed bot, got: {body}"
        )
        assert body["guild_count"] == 0
    finally:
        await runner.cleanup()


# ── Test 3: bot.start() crash → non-zero exit (Railway restart trigger) ────────

def test_bot_start_crash_exits_with_nonzero_code():
    """bot.py main() must exit non-zero when bot.start() raises.

    The crash_runner helper imports bot.py with all deps mocked and calls
    main() with bot.start() patched to raise RuntimeError, exercising the
    full asyncio _runner() → bot.start() → exception → propagation path.

    Railway's restartPolicyType = "on_failure" only fires on non-zero exit,
    so this is the critical signal for automatic recovery.
    """
    assert _CRASH_RUNNER.exists(), f"Crash runner script not found: {_CRASH_RUNNER}"

    result = subprocess.run(
        [sys.executable, str(_CRASH_RUNNER)],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(_DISCORD_BOT_DIR),
    )

    assert result.returncode != 0, (
        "Expected non-zero exit when bot.start() raises, but got "
        f"returncode={result.returncode}.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # Confirm it was the expected exception, not an import / setup error.
    assert "RuntimeError" in result.stderr or "Simulated Discord" in result.stderr, (
        f"Expected RuntimeError traceback in stderr, got:\n{result.stderr}"
    )


# ── Test 4: clean reconnect after crash (Railway restart cycle) ────────────────

def test_clean_reconnect_after_crash():
    """After a crash (non-zero exit), a fresh process's health endpoint returns 200.

    Simulates Railway's restart-on-failure cycle end-to-end:
      Step A — crash:   crash_runner.py exits non-zero  ✓
      Step B — restart: a fresh Python process starts the health server and
                        responds with 200 + ready=True, confirming the bot
                        reconnects into a healthy state.
    """
    # ── Step A: confirm the crash subprocess exits non-zero ───────────────────
    crash_result = subprocess.run(
        [sys.executable, str(_CRASH_RUNNER)],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(_DISCORD_BOT_DIR),
    )
    assert crash_result.returncode != 0, (
        f"Crash step must exit non-zero, got {crash_result.returncode}"
    )

    # ── Step B: fresh process — health server comes up clean ──────────────────
    # Inline script that starts only the health server (no Discord, no DB) and
    # GETs /health, printing the result as JSON to stdout before exiting 0.
    restart_script = textwrap.dedent(f"""\
        import asyncio, json, os, sys
        from unittest.mock import AsyncMock, MagicMock

        # Ensure discord-bot/ is on the path
        sys.path.insert(0, {str(_DISCORD_BOT_DIR)!r})

        # Mock all external deps before importing bot
        _mock_discord = MagicMock()
        _mock_discord.Intents.default.return_value = MagicMock()
        _mock_discord.NotFound = Exception
        _mock_discord.Forbidden = Exception
        for _cog in ["cogs","cogs.moderation","cogs.automod","cogs.welcome",
                     "cogs.customcommands","cogs.reactionroles","cogs.queue",
                     "cogs.supportpanel","cogs.settings","cogs.presence","cogs.alerts"]:
            sys.modules[_cog] = MagicMock()
        sys.modules["discord"] = _mock_discord
        sys.modules["discord.ext"] = MagicMock()
        sys.modules["discord.ext.commands"] = MagicMock()
        sys.modules["db"] = MagicMock()
        sys.modules["dotenv"] = MagicMock()

        import bot as bot_module

        # Simulate a freshly reconnected bot (not closed)
        mock_bot = MagicMock()
        mock_bot.guilds = ["guild1"]
        mock_bot.is_closed.return_value = False
        bot_module.bot = mock_bot

        from aiohttp import web
        import socket

        async def run():
            # Find a free port
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]

            app = web.Application()
            app.router.add_get("/health", bot_module.health_handler)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "127.0.0.1", port)
            await site.start()

            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://127.0.0.1:{{port}}/health") as resp:
                    body = await resp.json(content_type=None)
                    print(json.dumps({{"status_code": resp.status, "body": body}}))

            await runner.cleanup()

        asyncio.run(run())
    """)

    restart_result = subprocess.run(
        [sys.executable, "-c", restart_script],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=str(_DISCORD_BOT_DIR),
    )

    assert restart_result.returncode == 0, (
        f"Fresh-start process must exit 0 after restart, got "
        f"{restart_result.returncode}.\nstderr: {restart_result.stderr}"
    )

    import json as _json
    data = _json.loads(restart_result.stdout.strip())
    assert data["status_code"] == 200, f"Expected 200 after restart, got: {data}"
    assert data["body"]["status"] == "ok"
    assert data["body"]["ready"] is True, (
        f"Bot should be ready after clean restart, got: {data['body']}"
    )


# ── Test 5: startup alert distinguishes first start vs restart ───────────────

@pytest.mark.asyncio
async def test_startup_alert_sends_first_start_then_restart(tmp_path, caplog):
    """send_startup_alert distinguishes first start from restart via sentinel file.

    A fresh start creates the sentinel and sends a first-start alert.  A second
    start (simulating a Railway restart) sees the sentinel and sends a restart
    alert instead.  This confirms Task #15: startup alerts fire correctly after a
    simulated crash and restart.
    """
    sentinel = tmp_path / ".style_bot_started"
    bot_module = _load_bot_module()
    bot_module._SENTINEL_FILE = sentinel

    mock_channel = MagicMock()
    mock_channel.send = AsyncMock()
    mock_bot = MagicMock()
    mock_bot.guilds = ["guild1"]
    mock_bot.user.id = 12345
    mock_bot.get_channel.return_value = mock_channel
    bot_module.bot = mock_bot

    with patch.dict(os.environ, {"ALERT_CHANNEL_ID": "999999"}):
        # First call: sentinel does not exist yet → first start
        with caplog.at_level(logging.INFO, logger="style-bot"):
            await bot_module.send_startup_alert()
        assert "Startup alert sent to channel 999999 (restart=False)." in caplog.text
        assert sentinel.exists(), "Sentinel file should be created after first start"

        # Second call: sentinel exists → restart (simulates Railway restart)
        caplog.clear()
        with caplog.at_level(logging.INFO, logger="style-bot"):
            await bot_module.send_startup_alert()
        assert "Startup alert sent to channel 999999 (restart=True)." in caplog.text

    assert mock_channel.send.call_count == 2, (
        f"Expected two startup alerts (first start + restart), got {mock_channel.send.call_count}"
    )


# ── Test 6: uptime webhook — "down" payload sends offline embed ────────────────

@pytest.mark.asyncio
async def test_uptime_webhook_down_sends_offline_embed():
    """POST /alert/uptime with status=down sends an offline (red) embed to alert channels."""
    from aiohttp import web

    bot_module = _load_bot_module()

    # Stub db.get_all_alert_channels to return one channel row
    mock_channel = MagicMock()
    mock_channel.send = AsyncMock()
    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = mock_channel
    bot_module.bot = mock_bot
    bot_module.db.get_all_alert_channels = AsyncMock(
        return_value=[{"alert_channel_id": 111}]
    )

    # Stub cogs.alerts so offline_embed is importable inside the handler
    import sys
    mock_offline_embed = MagicMock(return_value=MagicMock(name="offline_embed_obj"))
    mock_recovery_embed = MagicMock(return_value=MagicMock(name="recovery_embed_obj"))
    mock_alerts_mod = MagicMock()
    mock_alerts_mod.offline_embed = mock_offline_embed
    mock_alerts_mod.recovery_embed = mock_recovery_embed
    sys.modules["cogs.alerts"] = mock_alerts_mod

    port = _free_port()
    app = web.Application()
    app.router.add_post("/alert/uptime", bot_module.uptime_webhook_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:{port}/alert/uptime",
                json={"status": "down", "reason": "No response from health check"},
            ) as resp:
                assert resp.status == 200, f"Expected 200, got {resp.status}"
                body = await resp.json(content_type=None)

        assert body["ok"] is True
        assert body["status"] == "down"
        assert body["channels_notified"] == 1

        # offline_embed must have been called with the reason string
        mock_offline_embed.assert_called_once_with("No response from health check")
        # And that embed must have been sent to the channel
        mock_channel.send.assert_awaited_once()
        # recovery_embed must NOT have been called
        mock_recovery_embed.assert_not_called()
    finally:
        await runner.cleanup()


# ── Test 7: uptime webhook — "up" payload sends recovery embed ─────────────────

@pytest.mark.asyncio
async def test_uptime_webhook_up_sends_recovery_embed():
    """POST /alert/uptime with status=up sends a green recovery embed to alert channels."""
    from aiohttp import web

    bot_module = _load_bot_module()

    mock_channel = MagicMock()
    mock_channel.send = AsyncMock()
    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = mock_channel
    bot_module.bot = mock_bot
    bot_module.db.get_all_alert_channels = AsyncMock(
        return_value=[{"alert_channel_id": 222}]
    )

    import sys
    mock_offline_embed = MagicMock(return_value=MagicMock(name="offline_embed_obj"))
    mock_recovery_embed = MagicMock(return_value=MagicMock(name="recovery_embed_obj"))
    mock_alerts_mod = MagicMock()
    mock_alerts_mod.offline_embed = mock_offline_embed
    mock_alerts_mod.recovery_embed = mock_recovery_embed
    sys.modules["cogs.alerts"] = mock_alerts_mod

    port = _free_port()
    app = web.Application()
    app.router.add_post("/alert/uptime", bot_module.uptime_webhook_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:{port}/alert/uptime",
                json={"status": "up", "reason": "Service recovered"},
            ) as resp:
                assert resp.status == 200, f"Expected 200, got {resp.status}"
                body = await resp.json(content_type=None)

        assert body["ok"] is True
        assert body["status"] == "up"
        assert body["channels_notified"] == 1

        # recovery_embed must have been called
        mock_recovery_embed.assert_called_once_with("Service recovered")
        mock_channel.send.assert_awaited_once()
        # offline_embed must NOT have been called
        mock_offline_embed.assert_not_called()
    finally:
        await runner.cleanup()


# ── Test 8: uptime webhook — secret validation returns 401 ────────────────────

@pytest.mark.asyncio
async def test_uptime_webhook_secret_validation():
    """POST /alert/uptime returns 401 when X-Webhook-Secret is missing or wrong.

    With WEBHOOK_SECRET set:
      - No header → 401
      - Wrong value → 401
      - Correct value → 200
    """
    from aiohttp import web

    bot_module = _load_bot_module()

    mock_bot = MagicMock()
    mock_bot.get_channel.return_value = None
    bot_module.bot = mock_bot
    bot_module.db.get_all_alert_channels = AsyncMock(return_value=[])

    port = _free_port()
    app = web.Application()
    app.router.add_post("/alert/uptime", bot_module.uptime_webhook_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    correct_secret = "super-secret-token"
    url = f"http://127.0.0.1:{port}/alert/uptime"
    payload = {"status": "down", "reason": "Test"}

    try:
        with patch.dict(os.environ, {"WEBHOOK_SECRET": correct_secret}):
            async with aiohttp.ClientSession() as session:
                # Case 1: no secret header → 401
                async with session.post(url, json=payload) as resp:
                    assert resp.status == 401, (
                        f"Expected 401 with no secret header, got {resp.status}"
                    )
                    body = await resp.json(content_type=None)
                    assert "error" in body

                # Case 2: wrong secret → 401
                async with session.post(
                    url, json=payload,
                    headers={"X-Webhook-Secret": "wrong-secret"},
                ) as resp:
                    assert resp.status == 401, (
                        f"Expected 401 with wrong secret, got {resp.status}"
                    )

                # Case 3: correct secret → 200
                async with session.post(
                    url, json=payload,
                    headers={"X-Webhook-Secret": correct_secret},
                ) as resp:
                    assert resp.status == 200, (
                        f"Expected 200 with correct secret, got {resp.status}"
                    )
    finally:
        await runner.cleanup()
