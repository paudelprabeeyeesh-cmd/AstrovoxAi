-- Core AI Assistant Phase 1 tables

-- Conversation folders
CREATE TABLE IF NOT EXISTS public.conversation_folders (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL DEFAULT 'New Folder',
  color TEXT NOT NULL DEFAULT '#0ea5e9',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.conversation_folders TO authenticated;
GRANT ALL ON public.conversation_folders TO service_role;
ALTER TABLE public.conversation_folders ENABLE ROW LEVEL SECURITY;
CREATE POLICY "folder_own_all" ON public.conversation_folders FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE INDEX folders_user_created_idx ON public.conversation_folders (user_id, created_at DESC);

-- Extend conversations with folder, pin, share support
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS folder_id UUID REFERENCES public.conversation_folders(id) ON DELETE SET NULL;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS is_shared BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS shared_at TIMESTAMPTZ;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS shared_with UUID[];
CREATE INDEX conversations_folder_idx ON public.conversations (folder_id);
CREATE INDEX conversations_pinned_idx ON public.conversations (user_id, is_pinned, updated_at DESC);

-- File attachments for messages
CREATE TABLE IF NOT EXISTS public.message_attachments (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  message_id UUID NOT NULL REFERENCES public.messages(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  content_type TEXT NOT NULL,
  size INTEGER NOT NULL DEFAULT 0,
  url TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.message_attachments TO authenticated;
GRANT ALL ON public.message_attachments TO service_role;
ALTER TABLE public.message_attachments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "attach_own_all" ON public.message_attachments FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE INDEX attachments_message_idx ON public.message_attachments (message_id);

-- User settings (theme, language, etc.)
CREATE TABLE IF NOT EXISTS public.user_settings (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
  theme TEXT NOT NULL DEFAULT 'dark',
  language TEXT NOT NULL DEFAULT 'en',
  default_model TEXT,
  notifications_enabled BOOLEAN NOT NULL DEFAULT true,
  voice_enabled BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_settings TO authenticated;
GRANT ALL ON public.user_settings TO service_role;
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "settings_own_all" ON public.user_settings FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Chat exports
CREATE TABLE IF NOT EXISTS public.chat_exports (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE,
  format TEXT NOT NULL DEFAULT 'json',
  url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.chat_exports TO authenticated;
GRANT ALL ON public.chat_exports TO service_role;
ALTER TABLE public.chat_exports ENABLE ROW LEVEL SECURITY;
CREATE POLICY "export_own_all" ON public.chat_exports FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE INDEX exports_user_idx ON public.chat_exports (user_id, created_at DESC);

-- Shared conversation access logs
CREATE TABLE IF NOT EXISTS public.shared_conversation_access (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
  accessed_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  accessed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.shared_conversation_access TO authenticated;
GRANT ALL ON public.shared_conversation_access TO service_role;
ALTER TABLE public.shared_conversation_access ENABLE ROW LEVEL SECURITY;
CREATE POLICY "shared_access_own" ON public.shared_conversation_access FOR ALL TO authenticated USING (auth.uid() = accessed_by) WITH CHECK (auth.uid() = accessed_by);
CREATE INDEX shared_access_conv_idx ON public.shared_conversation_access (conversation_id);

-- Trigger for folders updated_at
CREATE OR REPLACE FUNCTION public.set_updated_at() RETURNS TRIGGER LANGUAGE plpgsql SET search_path = public AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$;
DROP TRIGGER IF EXISTS folders_set_updated_at ON public.conversation_folders;
CREATE TRIGGER folders_set_updated_at BEFORE UPDATE ON public.conversation_folders FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
DROP TRIGGER IF EXISTS settings_set_updated_at ON public.user_settings;
CREATE TRIGGER settings_set_updated_at BEFORE UPDATE ON public.user_settings FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
