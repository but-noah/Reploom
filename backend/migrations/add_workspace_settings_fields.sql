-- Migration: Add tone_level (int) and style_json fields to workspace_settings
-- This updates existing workspace_settings to use integer tone_level (1-5) and adds style_json

-- Note: SQLModel will automatically create the table with the new schema
-- This migration is for reference and manual updates if needed

-- Example: Update existing records to use integer tone_level
-- UPDATE workspace_settings SET tone_level = 1 WHERE tone_level = 'formal';
-- UPDATE workspace_settings SET tone_level = 3 WHERE tone_level = 'friendly';
-- UPDATE workspace_settings SET tone_level = 5 WHERE tone_level = 'casual';

-- For SQLModel, the table will be recreated with correct schema on next startup
-- Existing data migration can be handled by the seed script

-- Verify the schema
-- \d workspace_settings
