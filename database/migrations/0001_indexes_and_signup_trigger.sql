-- ============================================================
-- Migration 0001: Performance indexes + signup trigger
-- ============================================================
-- This migration is additive and idempotent. It is safe to run
-- against an existing Supabase database created from
-- database/schemas/supabase_setup.sql. It does NOT drop or modify
-- any existing data.
--
-- NOTE: This SQL has been syntax-reviewed but NOT executed against a
-- live database in this environment (no Supabase credentials available).
-- ============================================================

-- ------------------------------------------------------------
-- 1. Performance indexes
-- ------------------------------------------------------------
-- The frontend and backend filter conversations by user_id and
-- order by updated_at, and load messages by conversation_id ordered
-- by created_at. Without these indexes those queries do full scans.

CREATE INDEX IF NOT EXISTS idx_conversations_user_id
    ON public.conversations (user_id);

CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
    ON public.conversations (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
    ON public.messages (conversation_id, created_at);

CREATE INDEX IF NOT EXISTS idx_messages_user_id
    ON public.messages (user_id);

CREATE INDEX IF NOT EXISTS idx_ai_memory_user_importance
    ON public.ai_memory (user_id, importance DESC, created_at DESC);

-- ------------------------------------------------------------
-- 2. Auto-create profile + settings on signup
-- ------------------------------------------------------------
-- supabase_setup.sql defines handle_new_user() but leaves the trigger
-- commented out, so new auth users never get a profiles/user_settings
-- row. This wires the trigger up idempotently.

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, username, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.raw_user_meta_data->>'username',
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  )
  ON CONFLICT (id) DO NOTHING;

  INSERT INTO public.user_settings (user_id)
  VALUES (NEW.id)
  ON CONFLICT (user_id) DO NOTHING;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
