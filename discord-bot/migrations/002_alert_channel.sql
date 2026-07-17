-- Add alert_channel_id to guild_settings so each guild can configure
-- where the bot sends online / offline notifications.
-- Safe to run repeatedly (IF NOT EXISTS guard via DO block).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'guild_settings' AND column_name = 'alert_channel_id'
    ) THEN
        ALTER TABLE guild_settings ADD COLUMN alert_channel_id BIGINT;
    END IF;
END;
$$;
