"""Shared PostgreSQL connection pool and data-access helpers for Style-Bot."""

import os
from typing import Optional

import asyncpg

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
# levels
# ---------------------------------------------------------------------------

async def get_level_row(guild_id: int, user_id: int) -> asyncpg.Record:
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM levels WHERE guild_id = $1 AND user_id = $2",
            guild_id,
            user_id,
        )
        if row is None:
            row = await conn.fetchrow(
                """
                INSERT INTO levels (guild_id, user_id) VALUES ($1, $2)
                ON CONFLICT (guild_id, user_id) DO UPDATE SET guild_id = EXCLUDED.guild_id
                RETURNING *
                """,
                guild_id,
                user_id,
            )
        return row


async def add_xp(guild_id: int, user_id: int, amount: int, level: int, when) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            """
            UPDATE levels
            SET xp = xp + $3, level = $4, last_message_at = $5
            WHERE guild_id = $1 AND user_id = $2
            """,
            guild_id,
            user_id,
            amount,
            level,
            when,
        )


async def get_leaderboard(guild_id: int, limit: int = 10) -> list[asyncpg.Record]:
    async with pool().acquire() as conn:
        return await conn.fetch(
            """
            SELECT user_id, xp, level FROM levels
            WHERE guild_id = $1
            ORDER BY xp DESC
            LIMIT $2
            """,
            guild_id,
            limit,
        )


async def get_rank(guild_id: int, user_id: int) -> int:
    async with pool().acquire() as conn:
        rank = await conn.fetchval(
            """
            SELECT COUNT(*) + 1 FROM levels
            WHERE guild_id = $1 AND xp > (
                SELECT xp FROM levels WHERE guild_id = $1 AND user_id = $2
            )
            """,
            guild_id,
            user_id,
        )
        return rank


async def set_level_role(guild_id: int, level: int, role_id: int) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO level_roles (guild_id, level, role_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, level) DO UPDATE SET role_id = EXCLUDED.role_id
            """,
            guild_id,
            level,
            role_id,
        )


async def remove_level_role(guild_id: int, level: int) -> None:
    async with pool().acquire() as conn:
        await conn.execute(
            "DELETE FROM level_roles WHERE guild_id = $1 AND level = $2",
            guild_id,
            level,
        )


async def get_level_roles(guild_id: int) -> list[asyncpg.Record]:
    async with pool().acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM level_roles WHERE guild_id = $1 ORDER BY level ASC",
            guild_id,
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
