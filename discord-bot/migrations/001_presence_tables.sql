-- Migration 001: presence tracking tables
-- Run once against the target PostgreSQL database.
-- Safe to re-run (all statements use IF NOT EXISTS / DO … EXCEPTION).

-- 1. Enum for Discord member status values
DO $$ BEGIN
  CREATE TYPE presence_status AS ENUM ('online', 'idle', 'dnd', 'offline');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- 2. Append-only event log
CREATE TABLE IF NOT EXISTS presence_events (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  guild_id    BIGINT          NOT NULL,
  user_id     BIGINT          NOT NULL,
  username    TEXT            NOT NULL,
  status      presence_status NOT NULL,
  recorded_at TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS presence_events_guild_user_idx
  ON presence_events (guild_id, user_id);

CREATE INDEX IF NOT EXISTS presence_events_recorded_at_idx
  ON presence_events (recorded_at);

-- 3. Current-status snapshot (upserted on every event; one row per member per guild)
CREATE TABLE IF NOT EXISTS member_current_status (
  guild_id   BIGINT          NOT NULL,
  user_id    BIGINT          NOT NULL,
  username   TEXT            NOT NULL,
  status     presence_status NOT NULL,
  updated_at TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
  CONSTRAINT member_current_status_pk PRIMARY KEY (guild_id, user_id)
);
