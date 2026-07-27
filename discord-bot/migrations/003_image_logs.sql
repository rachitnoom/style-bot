-- Migration 003: AI image command log
-- Tracks every /style, /background, and /beauty invocation per user / guild.
-- Safe to re-run (IF NOT EXISTS guard).

CREATE TABLE IF NOT EXISTS image_logs (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    BIGINT      NOT NULL,
    guild_id   BIGINT      NOT NULL,
    command    TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS image_logs_user_guild_idx
    ON image_logs (user_id, guild_id);
