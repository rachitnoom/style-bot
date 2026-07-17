"""Shared PostgreSQL connection pool and data-access helpers for Style-Bot."""

import logging
import os
import pathlib
from typing import Optional

import asyncpg

logger = logging.getLogger("style-bot.db")

_pool: Optional[asyncpg.Pool] = None

DEFAULT_WELCOME_MESSAGE = "Welcome {mention} to {server}! You are member #{count}."
DEFAULT_LEAVE_MESSAGE = "{user} has left {server}."


async def init_pool() -> asyncpg.Pool:
    """Create (or return the existing) connection pool. Call once at startup."""
    global _pool
    if _pool is None:
        database_url = os.environ["DATABASE_URL"]
        _pool = await asyncpg.create_pool(dsn=database_url, min_size=1, max_size=5)
    return _pool


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_pool() first.")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def run_migrations() -> None:
    """Apply all SQL files in the migrations/ directory in alphabetical order.

    Every migration file must be written to be idempotent (IF NOT EXISTS,
    DO … EXCEPTION, etc.) so this is safe to call on every startup.
    """
    migrations_dir = pathlib.Path(__file__).parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        logger.info("No migration files found — skipping.")
        return
    async with pool().acquire() as conn:
        for path in sql_files:
            logger.info("Applying migration: %s", path.name)
            await conn.execute(path.read_text())
            logger.info("Migration applied:  %s", path.name)
    logger.info("All migrations up to date.")


# ---------------------------------------------------------------------------
# guild_settings
# ---------------------------------------------------------------------------

async def get_guild_settings(guild_id: int) -> asyncpg.Record:
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM guild_settings WHERE guild_id = $1", guild_id
        )
        if row is None:
            row = await conn.fetchrow(
                """
                INSERT INTO guild_settings (guild_id) VALUES ($1)
                ON CONFLICT (guild_id) DO UPDATE SET guild_id = EXCLUDED.guild_id
                RETURNING *
                """,
                guild_id,
            )
        return row


async def update_guild_settings(guild_id: int, **fields) -> None:
    if not fields:
        return
    await get_guild_settings(guild_id)  # ensure a row exists
    set_clause = ", ".join(f"{key} = ${i + 2}" for i, key in enumerate(fields))
    values = list(fields.values())
    async with pool().acquire() as conn:
        await conn.execute(
            f"UPDATE guild_settings SET {set_clause} WHERE guild_id = $1",
            guild_id,
            *values,
        )


# ---------------------------------------------------------------------------
# custom_commands
# ---------------------------------------------------------------------------

async def add_custom_command(guild_id: int, name: str, response: str, created_by: int) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO custom_commands (guild_id, name, response, created_by)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, name) DO UPDATE SET response = EXCLUDED.response
            """,
            guild_id,
            name.lower(),
            response,
            created_by,
        )


async def remove_custom_command(guild_id: int, name: str) -> str:
    async with pool().acquire() as conn:
        result = await conn.execute(
            "DELETE FROM custom_commands WHERE guild_id = $1 AND name = $2",
            guild_id,
            name.lower(),
        )
        return result


async def get_custom_command(guild_id: int, name: str) -> Optional[asyncpg.Record]:
    async with pool().acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM custom_commands WHERE guild_id = $1 AND name = $2",
            guild_id,
            name.lower(),
        )


async def list_custom_commands(guild_id: int) -> list[asyncpg.Record]:
    async with pool().acquire() as conn:
        return await conn.fetch(
            "SELECT name FROM custom_commands WHERE guild_id = $1 ORDER BY name ASC",
            guild_id,
        )


# ---------------------------------------------------------------------------
# reaction_roles
# ---------------------------------------------------------------------------

async def add_reaction_role(message_id: int, guild_id: int, channel_id: int, emoji: str, role_id: int) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO reaction_roles (message_id, guild_id, channel_id, emoji, role_id)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (message_id, emoji) DO UPDATE SET role_id = EXCLUDED.role_id
            """,
            message_id,
            guild_id,
            channel_id,
            emoji,
            role_id,
        )


async def get_reaction_role(message_id: int, emoji: str) -> Optional[asyncpg.Record]:
    async with pool().acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM reaction_roles WHERE message_id = $1 AND emoji = $2",
            message_id,
            emoji,
        )


async def remove_reaction_roles_for_message(message_id: int) -> None:
    async with pool().acquire() as conn:
        await conn.execute("DELETE FROM reaction_roles WHERE message_id = $1", message_id)


# ---------------------------------------------------------------------------
# warnings
# ---------------------------------------------------------------------------

async def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
    async with pool().acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO warnings (guild_id, user_id, moderator_id, reason)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            guild_id,
            user_id,
            moderator_id,
            reason,
        )


async def get_warnings(guild_id: int, user_id: int) -> list[asyncpg.Record]:
    async with pool().acquire() as conn:
        return await conn.fetch(
            """
            SELECT * FROM warnings WHERE guild_id = $1 AND user_id = $2
            ORDER BY created_at DESC
            """,
            guild_id,
            user_id,
        )


async def clear_warnings(guild_id: int, user_id: int) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            "DELETE FROM warnings WHERE guild_id = $1 AND user_id = $2",
            guild_id,
            user_id,
        )


# ---------------------------------------------------------------------------
# queue_tickets
# ---------------------------------------------------------------------------

QUEUE_MIN = 1
QUEUE_MAX = 100


async def get_user_ticket(guild_id: int, user_id: int) -> Optional[asyncpg.Record]:
    async with pool().acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM queue_tickets WHERE guild_id = $1 AND user_id = $2",
            guild_id,
            user_id,
        )


async def claim_next_ticket(guild_id: int, user_id: int, display_name: str) -> Optional[int]:
    """Assign the smallest free number in [QUEUE_MIN, QUEUE_MAX] to this user.

    Returns the assigned number, or None if the queue is full.
    Returns the user's existing number without creating a duplicate if they already hold one.
    """
    async with pool().acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow(
                "SELECT number FROM queue_tickets WHERE guild_id = $1 AND user_id = $2",
                guild_id,
                user_id,
            )
            if existing:
                return existing["number"]

            taken = {
                r["number"]
                for r in await conn.fetch(
                    "SELECT number FROM queue_tickets WHERE guild_id = $1", guild_id
                )
            }
            number = next((n for n in range(QUEUE_MIN, QUEUE_MAX + 1) if n not in taken), None)
            if number is None:
                return None

            await conn.execute(
                """
                INSERT INTO queue_tickets (guild_id, number, user_id, display_name)
                VALUES ($1, $2, $3, $4)
                """,
                guild_id,
                number,
                user_id,
                display_name,
            )
            return number


async def complete_ticket(guild_id: int, user_id: int) -> Optional[int]:
    """Remove the caller's ticket. Returns the freed number, or None if they had none."""
    async with pool().acquire() as conn:
        return await conn.fetchval(
            "DELETE FROM queue_tickets WHERE guild_id = $1 AND user_id = $2 RETURNING number",
            guild_id,
            user_id,
        )


async def list_active_tickets(guild_id: int) -> list[asyncpg.Record]:
    async with pool().acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM queue_tickets WHERE guild_id = $1 ORDER BY number ASC",
            guild_id,
        )


async def clear_all_tickets(guild_id: int) -> None:
    async with pool().acquire() as conn:
        await conn.execute("DELETE FROM queue_tickets WHERE guild_id = $1", guild_id)


# ---------------------------------------------------------------------------
# presence_events / member_current_status
# ---------------------------------------------------------------------------

VALID_STATUSES = {"online", "idle", "dnd", "offline"}


async def record_presence_event(
    guild_id: int, user_id: int, username: str, status: str
) -> None:
    """Insert a presence event and upsert the current-status snapshot."""
    if status not in VALID_STATUSES:
        status = "offline"
    async with pool().acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                """
                INSERT INTO presence_events (guild_id, user_id, username, status)
                VALUES ($1, $2, $3, $4::presence_status)
                """,
                guild_id,
                user_id,
                username,
                status,
            )
            await conn.execute(
                """
                INSERT INTO member_current_status (guild_id, user_id, username, status, updated_at)
                VALUES ($1, $2, $3, $4::presence_status, NOW())
                ON CONFLICT (guild_id, user_id)
                DO UPDATE SET username = EXCLUDED.username,
                              status = EXCLUDED.status,
                              updated_at = EXCLUDED.updated_at
                """,
                guild_id,
                user_id,
                username,
                status,
            )


async def get_presence_events(
    guild_id: int,
    user_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[asyncpg.Record]:
    """Return presence events for a guild, optionally filtered by user."""
    async with pool().acquire() as conn:
        if user_id is not None:
            return await conn.fetch(
                """
                SELECT * FROM presence_events
                WHERE guild_id = $1 AND user_id = $2
                ORDER BY recorded_at DESC
                LIMIT $3 OFFSET $4
                """,
                guild_id,
                user_id,
                limit,
                offset,
            )
        return await conn.fetch(
            """
            SELECT * FROM presence_events
            WHERE guild_id = $1
            ORDER BY recorded_at DESC
            LIMIT $2 OFFSET $3
            """,
            guild_id,
            limit,
            offset,
        )


async def get_member_current_statuses(guild_id: int) -> list[asyncpg.Record]:
    """Return the latest status snapshot for every member in a guild."""
    async with pool().acquire() as conn:
        return await conn.fetch(
            """
            SELECT * FROM member_current_status
            WHERE guild_id = $1
            ORDER BY username ASC
            """,
            guild_id,
        )


# ---------------------------------------------------------------------------
# support_panel_settings
# ---------------------------------------------------------------------------

async def get_support_panel_settings(guild_id: int) -> asyncpg.Record:
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM support_panel_settings WHERE guild_id = $1", guild_id
        )
        if row is None:
            row = await conn.fetchrow(
                """
                INSERT INTO support_panel_settings (guild_id) VALUES ($1)
                ON CONFLICT (guild_id) DO UPDATE SET guild_id = EXCLUDED.guild_id
                RETURNING *
                """,
                guild_id,
            )
        return row


async def update_support_panel_settings(guild_id: int, **fields) -> None:
    if not fields:
        return
    await get_support_panel_settings(guild_id)  # ensure a row exists
    set_clause = ", ".join(f"{key} = ${i + 2}" for i, key in enumerate(fields))
    values = list(fields.values())
    async with pool().acquire() as conn:
        await conn.execute(
            f"UPDATE support_panel_settings SET {set_clause} WHERE guild_id = $1",
            guild_id,
            *values,
        )
