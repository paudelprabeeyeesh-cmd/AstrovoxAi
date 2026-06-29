CREATE TABLE public.error_logs (
  id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  source text NOT NULL CHECK (source IN ('client','server')),
  level text NOT NULL DEFAULT 'error' CHECK (level IN ('error','warn','info')),
  message text NOT NULL,
  stack text,
  url text,
  route text,
  method text,
  status integer,
  duration_ms integer,
  user_id uuid,
  user_agent text,
  meta jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT ALL ON public.error_logs TO service_role;
ALTER TABLE public.error_logs ENABLE ROW LEVEL SECURITY;
CREATE INDEX error_logs_created_at_idx ON public.error_logs (created_at DESC);
CREATE INDEX error_logs_source_level_idx ON public.error_logs (source, level, created_at DESC);